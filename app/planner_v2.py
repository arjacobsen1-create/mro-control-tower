#!/usr/bin/env python3
"""
Stage V2-6 — planner screen V2 (local server). Read-only against the
project data; the ONLY thing it writes is the planner's own V2
decision file. Serves the page in app/planner_v2_page.py and
validates every decision server-side against the §7 gate model,
exactly as the V1 gate fix did for its model — the server builds the
canonical decision record itself from the validated fields (the
client never supplies the label, the flags snapshot, the checkpoint
or the documented need; those are injected from the data file).

§7 model (docs/v2-spec.md): precedence shortage rows -> SLIPPAGE_HIGH
-> Tier A -> status row, allocated view governing. Notification and
procurement are separate fields of the record. Every decision on a
HIGH line (SLIPPAGE_HIGH or CONTENDED_SHORT) must record a recovery
path. A notification recorded as released requires the four §4.6
verifications. A procurement decision requires the line's documented
§5.6 need, which the record names. Nothing is sent, ordered or
placed by the system — decisions are records of a human's decision.

How to run:
    python3 app/planner_v2.py            # then open http://127.0.0.1:8766
    python3 app/planner_v2.py 9001       # custom port

Data in:   evals/planner_data_v2.json (its OWN file; the V1 planner
                                      and its data are untouched)
Data out:  monitoring/planner_decisions_v2.json (local only)
"""
import json, os, sys
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from planner_v2_page import PAGE_TEMPLATE  # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_PATH = os.path.join(ROOT, "evals", "planner_data_v2.json")
DECISIONS_PATH = os.path.join(ROOT, "monitoring", "planner_decisions_v2.json")

STATUS_ACTIONS = {
    "OK": ["acknowledged"],
    "COVERED_BY_PO": ["approve_monitor_po"],
    "COVERED_BY_TRANSFER": ["approve_transfer"],
    "COVERED_BY_ALTERNATE": ["approve_alternate"],
    "SHORT_UNCOVERED": ["escalate_expedite", "escalate_defer"],
    "INSUFFICIENT_DATA": ["escalate_investigate"],
}
DECISION_LABELS = {
    "acknowledged": "Acknowledge — no action",
    "approve_monitor_po": "Approve — monitor PO",
    "approve_transfer": "Approve transfer",
    "approve_alternate": "Approve alternate use",
    "escalate_expedite": "Escalate — expedite / emergency source",
    "escalate_defer": "Escalate — defer event",
    "escalate_investigate": "Escalate — investigate / physical count",
    "sent_back": "Send back for review",
    "notify_customer_at_risk": "Notify customer — at risk",
    "place_order": "Decide: place the order",
    "acknowledge_lapse": "Acknowledge — let the window lapse",
}
RECOVERY_PATHS = ["expedite / chase PO", "exchange / rotable",
                  "transfer under allocation", "re-sequence the check", "defer"]
VERIFICATIONS = ["affected_event", "material_shortfall",
                 "recovery_options", "proposed_communication"]


def load_data():
    with open(DATA_PATH) as f:
        return json.load(f)


def load_decisions():
    if os.path.exists(DECISIONS_PATH):
        with open(DECISIONS_PATH) as f:
            return json.load(f)
    return {}


def find_line(data, event_id, part_id):
    for e in data["events"]:
        if e["event_id"] == event_id:
            for l in e["lines"]:
                if l["part_id"] == part_id:
                    return l
    return None


def is_short(l):
    return "SHORT_UNCOVERED" in (l["allocated_status"], l["status"])


def is_insuff(l):
    return "INSUFFICIENT_DATA" in (l["allocated_status"], l["status"])


def is_high(l):
    return l["slippage_tier"] == "SLIPPAGE_HIGH" or l["contention"] == "CONTENDED_SHORT"


def tier_a_governs(l):
    return (not is_short(l) and not is_insuff(l)
            and l["slippage_tier"] != "SLIPPAGE_HIGH"
            and l["watchlist_tier"] == "ORDER_BY_CLOSING")


def allowed_primary(l):
    """§7 precedence: shortage -> SLIPPAGE_HIGH -> Tier A -> status row."""
    if is_short(l):
        base = ["escalate_expedite", "escalate_defer", "notify_customer_at_risk"]
    elif is_insuff(l):
        base = ["escalate_investigate"]
    elif l["slippage_tier"] == "SLIPPAGE_HIGH":
        base = ["escalate_expedite", "notify_customer_at_risk"]
    elif tier_a_governs(l):
        base = ["place_order", "acknowledge_lapse"]
    else:
        base = list(STATUS_ACTIONS.get(l["allocated_status"], []))
        if l["slippage_tier"] == "SLIPPAGE_WATCH":
            base.append("escalate_expedite")
    return set(base) | {"sent_back"}


def notify_allowed(l):
    return is_short(l) or l["slippage_tier"] == "SLIPPAGE_HIGH"


def validate_and_build(data, req):
    """Validate a decision payload against §7 and build the canonical
    record. Returns (record, None) or (None, error_message)."""
    line = find_line(data, req.get("event_id"), req.get("part_id"))
    if line is None or not line.get("assessed"):
        return None, "not an assessed line"
    decision = req.get("decision")
    if decision not in allowed_primary(line):
        return None, ("decision must be one of "
                      + ", ".join(sorted(allowed_primary(line))) + ", or null (undo)")
    recovery = req.get("recovery_path")
    if is_high(line) and not recovery:
        return None, "a decision on a HIGH line must record a recovery path (§7, Amendment A)"
    if recovery is not None and recovery not in RECOVERY_PATHS:
        return None, "recovery_path must be one of: " + ", ".join(RECOVERY_PATHS)
    notification = req.get("notification")
    if notification is not None:
        if not notify_allowed(line):
            return None, "customer notification is not offered for this line's state (§4.6/§7)"
        if notification.get("action") != "notify_customer_at_risk":
            return None, "notification action must be notify_customer_at_risk"
        verifs = notification.get("verifications") or {}
        if notification.get("released") and not all(verifs.get(v) for v in VERIFICATIONS):
            return None, ("a notification recorded as released requires all four "
                          "pre-release verifications (§4.6)")
        notification = {"action": "notify_customer_at_risk",
                        "released": bool(notification.get("released")),
                        "checkpoint_date": line["notification"].get("checkpoint_date"),
                        "verifications": {v: bool(verifs.get(v)) for v in VERIFICATIONS}}
    procurement = req.get("procurement_decision")
    if procurement is not None:
        if procurement not in ("place_order", "acknowledge_lapse"):
            return None, "procurement_decision must be place_order or acknowledge_lapse"
        if line["procurement_action"] != "RAISED" or not line.get("procurement_need"):
            return None, ("a procurement decision requires the line's documented "
                          "procurement need (§5.6)")
    record = {"event_id": req["event_id"], "part_id": req["part_id"],
              "decision": decision,
              "label": DECISION_LABELS.get(decision, decision),
              "decided_at": datetime.now(timezone.utc).isoformat(),
              "flags": {"status": line["status"],
                        "allocated_status": line["allocated_status"],
                        "contention": line["contention"],
                        "slippage_tier": line["slippage_tier"],
                        "watchlist_tier": line["watchlist_tier"]},
              "recovery_path": recovery,
              "notification": notification,
              "procurement_decision": procurement,
              "procurement_need": line.get("procurement_need") if procurement else None}
    if line["contention"] == "CONTENDED_COVERED":
        record["allocation_basis"] = ("decided against the allocated view; "
                                      "pool ledger in planner data")
    return record, None


def clear_decision(event_id, part_id):
    decisions = load_decisions()
    decisions.pop(f"{event_id}/{part_id}", None)
    os.makedirs(os.path.dirname(DECISIONS_PATH), exist_ok=True)
    with open(DECISIONS_PATH, "w") as f:
        json.dump(decisions, f, indent=2)
    return decisions


PAGE = PAGE_TEMPLATE.replace("__MODE__", "server").replace("__DATA__", "null")


class Handler(BaseHTTPRequestHandler):
    def log_message(self, *a):
        pass

    def _json(self, obj, code=200):
        body = json.dumps(obj).encode()
        self.send_response(code)
        self.send_header("content-type", "application/json")
        self.send_header("content-length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/api/state":
            self._json({"data": load_data(), "decisions": load_decisions()})
        elif self.path in ("/", "/index.html"):
            body = PAGE.encode()
            self.send_response(200)
            self.send_header("content-type", "text/html; charset=utf-8")
            self.send_header("content-length", str(len(body)))
            self.end_headers()
            self.wfile.write(body)
        else:
            self._json({"error": "not found"}, 404)

    def do_POST(self):
        if self.path != "/api/decide":
            return self._json({"error": "not found"}, 404)
        req = json.loads(self.rfile.read(int(self.headers.get("content-length", 0))))
        data = load_data()
        line = find_line(data, req.get("event_id"), req.get("part_id"))
        if line is None or not line.get("assessed"):
            return self._json({"error": "not an assessed line"}, 400)
        if req.get("decision") is None:
            return self._json({"decisions": clear_decision(req["event_id"], req["part_id"])})
        record, err = validate_and_build(data, req)
        if err:
            return self._json({"error": err}, 400)
        decisions = load_decisions()
        decisions[f"{req['event_id']}/{req['part_id']}"] = record
        os.makedirs(os.path.dirname(DECISIONS_PATH), exist_ok=True)
        with open(DECISIONS_PATH, "w") as f:
            json.dump(decisions, f, indent=2)
        self._json({"decisions": decisions})


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8766
    print(f"Planner V2 screen: http://127.0.0.1:{port}  (Ctrl+C to stop)")
    print(f"Decisions file: {DECISIONS_PATH}")
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
