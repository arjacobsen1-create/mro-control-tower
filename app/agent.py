#!/usr/bin/env python3
"""
Stage 3 — MRO Control Tower assessment agent (Claude, tool use).

Workflow per (event, part): detect -> assess -> recommend -> human decides.
The agent must call check_availability for every quantity/status, ground its
recommendation in search_knowledge results, and finish with ONE JSON object
matching the assessment schema. Every run is logged to monitoring/runs.jsonl.

Usage:
  ANTHROPIC_API_KEY=... python3 app/agent.py E001 P001     # one demand line
  ANTHROPIC_API_KEY=... python3 app/agent.py E001          # all lines of an event
Env: MRO_MODEL (default claude-haiku-4-5 — cheap dev model; spot-check on a
     larger model only when needed).
Reference date: 2026-11-02, pinned (ingest/config.py). The dataset is a
snapshot as of that date; event dates are compared against it by the rule
engine, not against the wall clock.
"""
import json, os, sys, urllib.request
from datetime import datetime, timezone

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingest"))
from config import REFERENCE_DATE  # noqa: E402
from tools import TOOL_SCHEMAS, TOOL_SCHEMAS_V2, run_tool  # noqa: E402
import availability  # noqa: E402

API_URL = "https://api.anthropic.com/v1/messages"
MODEL = os.environ.get("MRO_MODEL", "claude-haiku-4-5")
LOG_PATH = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
                        "monitoring", "runs.jsonl")
STATUSES = {"OK", "COVERED_BY_PO", "COVERED_BY_TRANSFER", "COVERED_BY_ALTERNATE",
            "SHORT_UNCOVERED", "INSUFFICIENT_DATA"}

SYSTEM = """You are the assessment agent for a fictional MRO (maintenance, repair and overhaul) supply chain control tower. The data is synthetic, current as of 2026-11-02.

Your job for one (event, part) demand line: assess parts coverage and recommend the planner's next action. A human planner makes the final decision; you recommend, you never act.

Rules you must follow:
1. Call check_availability before stating ANY quantity or status. Never compute or guess stock figures yourself; use only its returned evidence.
2. Ground recommendations in search_knowledge results and cite the note_ids you used. If search returns nothing relevant, say no documented rule covers it instead of inventing one.
3. If status is INSUFFICIENT_DATA, recommend escalation for a physical count - never an estimate.
4. If status is SHORT_UNCOVERED and the part's criticality is AOG, set escalation_required to true. If SHORT_UNCOVERED, also state the earliest inbound date from the PO detail (or that none exists).
5. Dates: check_availability returns a lead_time_check computed in code. Use only those dates. If order_by_already_passed is true, state plainly that the order-by date has already passed and give the earliest_arrival_if_ordered_now as the consequence - never present a past date as a future deadline, and never compute dates yourself.
6. Day-counts: any number of days you state (days late, days early, days of gap) MUST come from the tool output - the days_vs_event_start / days_vs_event_end fields in po_detail, or the earliest_arrival_days_vs_event_start / earliest_arrival_days_vs_event_end fields in lead_time_check. Positive means the delivery lands that many days AFTER that event date; negative means before it. If the difference you need is not among those provided numbers, leave the number out entirely rather than computing or estimating it yourself.
7. Finish with exactly one JSON object, no prose after it, matching:
{"event_id": str, "part_id": str, "status": one of OK|COVERED_BY_PO|COVERED_BY_TRANSFER|COVERED_BY_ALTERNATE|SHORT_UNCOVERED|INSUFFICIENT_DATA, "shortage_qty": int, "coverage_summary": str (one sentence, citing the evidence numbers), "recommendation": str (the planner's next action), "escalation_required": bool, "notes_cited": [note_id strings]}"""


def call_api(key, messages, system=SYSTEM, tools=TOOL_SCHEMAS):
    payload = {"model": MODEL, "max_tokens": 1600, "system": system,
               "tools": tools, "messages": messages}
    if key:  # direct path, key supplied via environment (e.g. her own laptop)
        body = json.dumps(payload).encode()
        req = urllib.request.Request(API_URL, data=body, method="POST", headers={
            "x-api-key": key, "anthropic-version": "2023-06-01", "content-type": "application/json"})
        with urllib.request.urlopen(req, timeout=120) as r:
            return json.loads(r.read())
    # connector path: key lives in the custom.anthropic connection (Secure
    # Vault) and is injected by the connector helper - never handled here.
    sys.path.insert(0, os.path.expanduser("~/workspace/custom-connectors/custom.anthropic/bin"))
    from anthropic_api import post_messages
    return post_messages(payload)


def extract_json(text):
    text = text.strip()
    if text.startswith("```"):
        text = text.split("```")[1].lstrip("json").strip()
    start = text.find("{")
    return json.loads(text[start:text.rfind("}") + 1])


def validate(a, event_id, part_id):
    assert a["event_id"] == event_id and a["part_id"] == part_id, "id mismatch"
    assert a["status"] in STATUSES, f"bad status {a['status']}"
    assert isinstance(a["shortage_qty"], int) and a["shortage_qty"] >= 0
    assert isinstance(a["escalation_required"], bool)
    return a


# Stage 6 fix 2 — citation stability. A recommendation for one of these
# statuses is policy-driven by construction (transfer procedure, alternate
# approval, count-and-escalate on missing data), so it must cite the
# knowledge note(s) behind it on EVERY run, not most runs. SHORT_UNCOVERED
# joins the list when the run escalates (AOG escalation policy).
POLICY_CITATION_STATUSES = {"COVERED_BY_TRANSFER", "COVERED_BY_ALTERNATE",
                            "INSUFFICIENT_DATA"}


def _needs_citation(a):
    if a.get("notes_cited"):
        return False
    return (a["status"] in POLICY_CITATION_STATUSES
            or (a["status"] == "SHORT_UNCOVERED" and a.get("escalation_required")))


def assess(key, event_id, part_id):
    messages = [{"role": "user", "content":
                 f"Assess coverage for event {event_id}, part {part_id}. "
                 "Use your tools, then return the JSON assessment."}]
    usage = {"input_tokens": 0, "output_tokens": 0}
    a = _run_loop(key, messages, usage, event_id, part_id)
    if _needs_citation(a):
        # One retry, with the gap named explicitly. The retried result is
        # accepted as-is (still schema-validated inside _run_loop).
        usage["citation_retry"] = 1
        messages.append({"role": "user", "content":
                         "Your assessment's recommendation relies on a policy-driven "
                         "action, but notes_cited is empty. Call search_knowledge for "
                         "the policy or procedure behind this recommendation "
                         "(escalation, inter-site transfer, approved alternate use, "
                         "or the missing-record / physical-count procedure), then "
                         "return the corrected JSON assessment with notes_cited "
                         "listing the supporting note_id(s). Keep the status and "
                         "shortage_qty exactly as check_availability computed them."})
        a = _run_loop(key, messages, usage, event_id, part_id)
    return a, usage


def _run_loop(key, messages, usage, event_id, part_id, system=SYSTEM,
              tools=TOOL_SCHEMAS, validator=None, max_iter=12):
    validator = validator or validate
    for _ in range(max_iter):
        resp = call_api(key, messages, system=system, tools=tools)
        u = resp.get("usage", {})
        usage["input_tokens"] += u.get("input_tokens", 0)
        usage["output_tokens"] += u.get("output_tokens", 0)
        messages.append({"role": "assistant", "content": resp["content"]})
        tool_uses = [b for b in resp["content"] if b.get("type") == "tool_use"]
        if not tool_uses:
            text = "".join(b.get("text", "") for b in resp["content"] if b.get("type") == "text")
            return validator(extract_json(text), event_id, part_id)
        results = [{"type": "tool_result", "tool_use_id": b["id"],
                    "content": json.dumps(run_tool(b["name"], b["input"]))} for b in tool_uses]
        messages.append({"role": "user", "content": results})
    raise RuntimeError("agent exceeded tool-call limit")


# ---------------------------------------------------------------- V2 agent
# Stage V2-4: the V2 assessment path, beside the V1 path above (which is
# unchanged). Same discipline — every number from a tool, recommendations
# grounded in knowledge notes — extended with the four V2 tools and the
# V2 output fields: allocated view, slippage tier, watchlist tier, the
# §5.6 procurement action, the §4.6 notification path, recovery
# feasibility, and ONE recommended decision value from the fixed §7
# gate model. The three decision dimensions (procurement readiness,
# material coverage risk, customer impact) stay in separate fields.

V2_DECISIONS = {"acknowledged", "approve_monitor_po", "approve_transfer",
                "approve_alternate", "escalate_expedite", "escalate_defer",
                "escalate_investigate", "notify_customer_at_risk",
                "place_order", "acknowledge_lapse", "sent_back"}
V2_RECOVERY_PATHS = {"expedite / chase PO", "exchange / rotable",
                     "transfer under allocation", "re-sequence the check", "defer"}
V2_VERIFICATIONS = ["affected event", "material shortfall",
                    "recovery options", "proposed communication"]

SYSTEM_V2 = """You are the assessment agent for a fictional MRO (maintenance, repair and overhaul) supply chain control tower. The data is synthetic, current as of 2026-11-02.

Your job for one (event, part) demand line: assess parts coverage in BOTH views (single-line and cross-event allocated), flag the V2 exception types, and recommend the planner's next action. A human planner makes the final decision; you recommend, you never act, and you never send anything to a customer - a notification is only ever a prepared draft for human approval.

Rules you must follow:
1. Call check_availability AND check_allocated_availability before stating ANY quantity or status. status and shortage_qty come from check_availability; allocated_status, allocated_shortage_qty and contention come from check_allocated_availability. Never compute or guess figures yourself.
2. Call check_slippage_risk, check_watchlist and get_horizon for the same line, and copy slippage_tier, watchlist_tier, procurement_action, the notification eligibility/checkpoint and the recovery feasibility EXACTLY from their outputs. Never derive a tier, band or date yourself.
3. Ground recommendations in search_knowledge results and cite the note_ids you used. Almost every V2 line involves a policy-driven action (transfer, alternate use, escalation, procurement, notification, or a missing record), so call search_knowledge during your assessment - before finishing - whenever any of those is in play, and cite the supporting note_ids in your JSON. If search returns nothing relevant, say no documented rule covers it instead of inventing one.
4. recommended_decision: choose exactly ONE value, using the ALLOCATED status for the coverage decision when it differs from the single-line status, in this precedence order:
   - if the line is SHORT_UNCOVERED in either view: "escalate_expedite" when get_horizon reports a feasible recovery lever, otherwise "escalate_defer";
   - else if INSUFFICIENT_DATA in either view: "escalate_investigate";
   - else if slippage_tier is SLIPPAGE_HIGH: "escalate_expedite";
   - else if watchlist_tier is ORDER_BY_CLOSING and procurement_action is RAISED: "place_order";
   - else if slippage_tier is SLIPPAGE_WATCH: "approve_monitor_po";
   - else by allocated status: OK -> "acknowledged", COVERED_BY_PO -> "approve_monitor_po", COVERED_BY_TRANSFER -> "approve_transfer", COVERED_BY_ALTERNATE -> "approve_alternate".
5. customer_notification: set action to "PREPARE_DRAFT" exactly when get_horizon's notification.eligible is true, copying its checkpoint_date; otherwise "NONE" with checkpoint_date null. When PREPARE_DRAFT, verifications_outstanding must list exactly ["affected event", "material shortfall", "recovery options", "proposed communication"] - the four checks the HUMAN approver must complete before release; they are never yours to complete. When NONE, verifications_outstanding is [].
6. recovery_path: for a line that is SLIPPAGE_HIGH or SHORT_UNCOVERED in either view, name the recovery path you recommend - one of "expedite / chase PO", "exchange / rotable", "transfer under allocation", "re-sequence the check", "defer" - using only levers get_horizon's recovery output shows as feasible; if none is feasible the path is "defer". For all other lines, null.
7. feasible_recovery_exists: if the line is short in either view, copy get_horizon's recovery.feasible exactly (true or false). If the line is NOT short in either view, output true: get_horizon returns null for recovery.feasible there because there is no shortage to recover from — never copy that null into this field, which must always be a JSON boolean.
8. If no feasible recovery exists for a short line, say so plainly in the recommendation: state that no feasible recovery exists and recommend only escalation (defer) and the prepared notification. Never invent a recovery lever, and never soften a shortage into monitoring.
9. If procurement_action is RAISED, your recommendation must present the order decision and quote its documented need (get_horizon's procurement.documented_need) as a PROCUREMENT decision - never describe that action as a shortage, and never let the line's OK coverage verdict suppress it.
10. escalation_required: true if your recommended_decision is an escalation, or the line is SHORT_UNCOVERED in either view and the part's criticality is AOG; otherwise false.
11. Dates and day-counts: use only dates and day numbers the tools returned (lead_time_check, po_detail, horizon outputs). Positive day differences mean AFTER the event date. Never compute dates or day-counts yourself; if a number was not returned, leave it out.
12. Finish with exactly one JSON object, no prose after it, matching:
{"event_id": str, "part_id": str, "status": one of OK|COVERED_BY_PO|COVERED_BY_TRANSFER|COVERED_BY_ALTERNATE|SHORT_UNCOVERED|INSUFFICIENT_DATA, "shortage_qty": int, "allocated_status": same vocabulary, "allocated_shortage_qty": int, "contention": one of CONTENDED_SHORT|CONTENDED_COVERED|UNCONTENDED, "slippage_tier": one of SLIPPAGE_HIGH|SLIPPAGE_WATCH|NONE, "watchlist_tier": one of ORDER_BY_CLOSING|NO_ORDERING_FALLBACK|NONE, "procurement_action": one of RAISED|NONE, "procurement_need": str or null, "customer_notification": {"action": one of PREPARE_DRAFT|NONE, "checkpoint_date": str or null, "verifications_outstanding": [str]}, "recovery_path": str or null, "feasible_recovery_exists": bool, "recommended_decision": one of acknowledged|approve_monitor_po|approve_transfer|approve_alternate|escalate_expedite|escalate_defer|escalate_investigate|notify_customer_at_risk|place_order|acknowledge_lapse|sent_back, "coverage_summary": str (one sentence, citing the evidence numbers), "recommendation": str (the planner's next action), "escalation_required": bool, "notes_cited": [note_id strings]}"""


def validate_v2(a, event_id, part_id):
    assert a["event_id"] == event_id and a["part_id"] == part_id, "id mismatch"
    assert a["status"] in STATUSES, f"bad status {a['status']}"
    assert a["allocated_status"] in STATUSES, f"bad allocated status {a['allocated_status']}"
    assert isinstance(a["shortage_qty"], int) and a["shortage_qty"] >= 0, "shortage_qty must be an int >= 0"
    assert isinstance(a["allocated_shortage_qty"], int) and a["allocated_shortage_qty"] >= 0, "allocated_shortage_qty must be an int >= 0"
    assert a["contention"] in {"CONTENDED_SHORT", "CONTENDED_COVERED", "UNCONTENDED"}, f"bad contention {a['contention']}"
    assert a["slippage_tier"] in {"SLIPPAGE_HIGH", "SLIPPAGE_WATCH", "NONE"}, f"bad slippage_tier {a['slippage_tier']}"
    assert a["watchlist_tier"] in {"ORDER_BY_CLOSING", "NO_ORDERING_FALLBACK", "NONE"}, f"bad watchlist_tier {a['watchlist_tier']}"
    assert a["procurement_action"] in {"RAISED", "NONE"}, f"bad procurement_action {a['procurement_action']}"
    cn = a["customer_notification"]
    assert cn["action"] in {"PREPARE_DRAFT", "NONE"}, f"bad notification action {cn['action']}"
    assert isinstance(cn["verifications_outstanding"], list), "verifications_outstanding must be a list"
    assert a["recovery_path"] is None or a["recovery_path"] in V2_RECOVERY_PATHS, f"bad recovery_path {a['recovery_path']}"
    assert isinstance(a["feasible_recovery_exists"], bool), "feasible_recovery_exists must be a JSON boolean: copy get_horizon's recovery.feasible for a short line; output true when the line is not short (the tool's null there means no shortage, and must not be copied)"
    assert a["recommended_decision"] in V2_DECISIONS, f"bad recommended_decision {a['recommended_decision']}"
    assert isinstance(a["escalation_required"], bool), "escalation_required must be a boolean"
    return a


def _needs_citation_v2(a):
    if a.get("notes_cited"):
        return False
    return (a["status"] in POLICY_CITATION_STATUSES
            or a["allocated_status"] in POLICY_CITATION_STATUSES
            or a["contention"] == "CONTENDED_SHORT"
            or a["slippage_tier"] == "SLIPPAGE_HIGH"
            or a["watchlist_tier"] == "ORDER_BY_CLOSING"
            or a["customer_notification"]["action"] == "PREPARE_DRAFT"
            or (a["allocated_status"] == "SHORT_UNCOVERED" and a.get("escalation_required")))


def assess_v2(key, event_id, part_id):
    usage = {"input_tokens": 0, "output_tokens": 0}
    base = (f"Assess coverage for event {event_id}, part {part_id}. "
            "Use your tools, then return the JSON assessment.")
    try:
        messages = [{"role": "user", "content": base}]
        a = _run_loop(key, messages, usage, event_id, part_id, system=SYSTEM_V2,
                      tools=TOOL_SCHEMAS_V2, validator=validate_v2, max_iter=16)
    except AssertionError as ex:
        # Validation retry (V2 only; the Stage 6 citation-retry pattern
        # applied to schema failures): the model's flag values are
        # copies of tool outputs, so a type slip (e.g. a null or string
        # where a boolean belongs) is correctable when named. This is
        # the failure that cost R01 and X02a in the V2-5 evaluation —
        # see the evaluation report addendum. Retried once, and flagged
        # in the usage record when it fires.
        usage["validation_retry"] = 1
        messages = [{"role": "user", "content": base +
                     f" A previous attempt failed output validation: {ex}. "
                     "Copy every flag value from the tool outputs exactly, "
                     "with the exact JSON types specified (booleans as "
                     "true/false, never null or strings)."}]
        a = _run_loop(key, messages, usage, event_id, part_id, system=SYSTEM_V2,
                      tools=TOOL_SCHEMAS_V2, validator=validate_v2, max_iter=16)
    if _needs_citation_v2(a):
        usage["citation_retry"] = 1
        messages.append({"role": "user", "content":
                         "Your assessment's recommendation relies on a policy-driven "
                         "action, but notes_cited is empty. Call search_knowledge for "
                         "the policy or procedure behind this recommendation "
                         "(escalation, inter-site transfer, approved alternate use, "
                         "missing-record / physical-count procedure, or procurement) "
                         "then return the corrected JSON assessment with notes_cited "
                         "listing the supporting note_id(s). Keep every computed "
                         "field exactly as the tools returned it."})
        a = _run_loop(key, messages, usage, event_id, part_id, system=SYSTEM_V2,
                      tools=TOOL_SCHEMAS_V2, validator=validate_v2, max_iter=16)
    return a, usage


def main():
    key = os.environ.get("ANTHROPIC_API_KEY")  # optional: connector is the default route
    event_id = sys.argv[1]
    if len(sys.argv) > 2:
        lines = [(event_id, sys.argv[2])]
    else:
        lines = [(event_id, d["part_id"]) for d in availability.get_demand(event_id)]
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    for eid, pid in lines:
        a, usage = assess(key, eid, pid)
        rec = {"run_at": datetime.now(timezone.utc).isoformat(), "reference_date": REFERENCE_DATE,
               "model": MODEL, "usage": usage, "assessment": a}
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(rec) + "\n")
        print(json.dumps(a, indent=2))


if __name__ == "__main__":
    main()
