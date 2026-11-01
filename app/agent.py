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
from tools import TOOL_SCHEMAS, run_tool  # noqa: E402
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


def call_api(key, messages):
    payload = {"model": MODEL, "max_tokens": 1600, "system": SYSTEM,
               "tools": TOOL_SCHEMAS, "messages": messages}
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


def _run_loop(key, messages, usage, event_id, part_id):
    for _ in range(12):
        resp = call_api(key, messages)
        u = resp.get("usage", {})
        usage["input_tokens"] += u.get("input_tokens", 0)
        usage["output_tokens"] += u.get("output_tokens", 0)
        messages.append({"role": "assistant", "content": resp["content"]})
        tool_uses = [b for b in resp["content"] if b.get("type") == "tool_use"]
        if not tool_uses:
            text = "".join(b.get("text", "") for b in resp["content"] if b.get("type") == "text")
            return validate(extract_json(text), event_id, part_id)
        results = [{"type": "tool_result", "tool_use_id": b["id"],
                    "content": json.dumps(run_tool(b["name"], b["input"]))} for b in tool_uses]
        messages.append({"role": "user", "content": results})
    raise RuntimeError("agent exceeded tool-call limit")


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
