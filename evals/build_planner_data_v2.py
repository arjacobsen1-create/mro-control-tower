#!/usr/bin/env python3
"""
Stage V2-6 — build evals/planner_data_v2.json, the V2 planner's data
file. Its OWN file: evals/planner_data.json (V1) is untouched.

Every number comes from the rule engines (availability, allocation,
slippage, watchlist, horizon). The narrative fields (summary /
recommendation / notes cited) come from the stored V2 evaluation
assessments (evals/results_v2_2026-11-06.json) for the 15 distinct
scenario lines. One line — E001/P002 — has no stored passing
assessment because both of its evaluation runs failed (see the
evaluation report addendum); for that line alone this builder makes
one live assessment run, labels it in the file as a planner-build run
and logs it to monitoring/runs.jsonl as such. It does not change the
recorded evaluation score.

Run:  python3 evals/build_planner_data_v2.py
"""
import json, os, sqlite3, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "ingest"))
from availability import check_availability  # noqa: E402
from allocation import allocate_all  # noqa: E402
from slippage import slippage_risk  # noqa: E402
from watchlist import watchlist_line  # noqa: E402
from horizon import horizon_line  # noqa: E402
from config import REFERENCE_DATE, DB_PATH  # noqa: E402

OUT = os.path.join(ROOT, "evals", "planner_data_v2.json")
ORIGINAL_EVENTS = ["E001", "E002", "E003", "E004", "E005", "E006"]
FORWARD_EVENTS = ["E007", "E008", "E009"]
ALLOC = allocate_all()


def line_block(ev, pid, assessed, assessment, source):
    v1 = check_availability(ev, pid)
    alloc = ALLOC["lines"][(ev, pid)]
    slip = slippage_risk(ev, pid)
    wl = watchlist_line(ev, pid)
    hz = horizon_line(ev, pid)
    return {
        "part_id": pid, "part_name": v1["part_description"],
        "criticality": v1.get("criticality"), "needed": v1["qty_required"],
        "status": v1["status"], "shortage_qty": v1["shortage_qty"],
        "allocated_status": alloc["allocated_status"],
        "allocated_shortage_qty": alloc["allocated_shortage_qty"],
        "contention": alloc["contention"],
        "slippage_tier": slip["slippage_tier"],
        "slippage_detail": slip,
        "watchlist_tier": wl["watchlist_tier"],
        "order_by_date": wl["order_by_date"],
        "clock1": hz["clock1"], "clock2": hz["clock2"],
        "material_risk": hz["material_risk"],
        "risk_conditions": hz["risk_conditions"],
        "procurement_action": hz["procurement"]["action"],
        "procurement_need": hz["procurement"]["documented_need"],
        "notification": hz["notification"],
        "recovery": hz["recovery"],
        "assessed": assessed, "assessment": assessment,
        "assessment_source": source if assessed else None,
    }


def main():
    results = json.load(open(os.path.join(ROOT, "evals", "results_v2_2026-11-06.json")))
    stored = {}
    for r in results["results"]:
        if r["assessment"]:
            stored[(r["event"], r["part"])] = r["assessment"]  # latest wins
    scenario_lines = {(r["event"], r["part"]) for r in results["results"]}

    supplementary = {}
    missing = scenario_lines - set(stored)
    if missing:
        # Reuse a planner-build run already in the log if one exists
        # (idempotent rebuilds); only run live for lines still missing.
        from agent import LOG_PATH
        if os.path.exists(LOG_PATH):
            for line in open(LOG_PATH):
                rec = json.loads(line)
                key = None
                if rec.get("evaluation_set") == "planner-build" and rec.get("assessment"):
                    key = (rec["assessment"]["event_id"], rec["assessment"]["part_id"])
                if key in missing:
                    supplementary[key] = rec["assessment"]
        missing -= set(supplementary)
    if missing:
        from agent import assess_v2, MODEL, LOG_PATH
        for (ev, pid) in sorted(missing):
            a, usage = assess_v2(None, ev, pid)
            rec = {"run_at": datetime.now(timezone.utc).isoformat(),
                   "reference_date": REFERENCE_DATE, "model": MODEL,
                   "usage": usage, "assessment": a, "evaluation": None,
                   "evaluation_set": "planner-build"}
            with open(LOG_PATH, "a") as f:
                f.write(json.dumps(rec) + "\n")
            supplementary[(ev, pid)] = a
            print(f"supplementary planner-build run: {ev}/{pid} (logged)")

    conn = sqlite3.connect(DB_PATH)
    sched = {r[0]: {"event_name": r[1], "tail": r[2], "start": r[3], "end": r[4]}
             for r in conn.execute("SELECT event_id, check_type, tail_id, "
                                   "planned_start, planned_end FROM maintenance_schedule")}
    parts = {r[0]: r[1] for r in conn.execute("SELECT part_id, description FROM parts")}
    demand = {}
    for ev, pid in conn.execute("SELECT event_id, part_id FROM demand ORDER BY part_id"):
        demand.setdefault(ev, []).append(pid)
    conn.close()

    def build_events(ids):
        out = []
        for ev in ids:
            lines = []
            for pid in demand.get(ev, []):
                key = (ev, pid)
                if key in stored:
                    lines.append(line_block(ev, pid, True, stored[key],
                                            "V2 evaluation 2026-11-06"))
                elif key in supplementary:
                    lines.append(line_block(ev, pid, True, supplementary[key],
                                            "planner-build run (evaluation runs failed; see report)"))
                else:
                    lines.append(line_block(ev, pid, False, None, None))
            out.append({"event_id": ev, **sched[ev], "lines": lines})
        return out

    events = build_events(ORIGINAL_EVENTS)
    forward = build_events(FORWARD_EVENTS)
    all_lines = [l for e in events for l in e["lines"]]

    # "Contended part" is a demand fact (§2.1): demanded by 2+ events.
    # (The per-line contention FLAG is narrower — it means allocation
    # actually bit for that line; §3.2's UNCONTENDED covers
    # "allocation changed nothing", e.g. P008/P009/P015.)
    from collections import Counter
    demand_counts_all = Counter(pid for ev in demand for pid in demand[ev])
    demand_counts_orig = Counter(pid for ev in ORIGINAL_EVENTS for pid in demand[ev])
    contended = sorted(p for p, n in demand_counts_all.items() if n >= 2)
    contended_orig = sum(1 for n in demand_counts_orig.values() if n >= 2)
    ledgers = {}
    for pid in contended:
        rows = []
        for ev in ORIGINAL_EVENTS + FORWARD_EVENTS:
            if (ev, pid) in ALLOC["lines"]:
                l = ALLOC["lines"][(ev, pid)]
                rows.append({"event_id": ev, "event_start": sched[ev]["start"],
                             "v1_status": l["v1_status"],
                             "allocated_status": l["allocated_status"],
                             "allocated_shortage_qty": l["allocated_shortage_qty"],
                             "contention": l["contention"], "ledger": l["ledger"]})
        ledgers[pid] = {"part_name": parts.get(pid, pid), "rows": rows,
                        "pool_initial": ALLOC["pools"][pid]["initial"],
                        "pool_remaining": ALLOC["pools"][pid]["remaining"]}

    data = {
        "reference_date": REFERENCE_DATE,
        "allocation_policy": "chronological",
        "generated_from": ("rule engines + evals/results_v2_2026-11-06.json; "
                           "see evals/build_planner_data_v2.py"),
        "v2_evaluation": {"score": results["v2_score"],
                          "v1_regression": results["v1_regression_score"]},
        "events": events,
        "forward_events": forward,
        "allocation_ledgers": ledgers,
        "counts": {
            "lines": len(all_lines),
            "contended_parts": contended_orig,
            "contended_parts_incl_forward": len(contended),
            "lines_changed_under_allocation": sum(
                1 for l in all_lines if l["allocated_status"] != l["status"]
                or l["allocated_shortage_qty"] != l["shortage_qty"]),
            "flips_to_short": sum(1 for l in all_lines
                                  if l["allocated_status"] == "SHORT_UNCOVERED"
                                  and l["status"] != "SHORT_UNCOVERED"),
            "slippage_high": sum(1 for l in all_lines if l["slippage_tier"] == "SLIPPAGE_HIGH"),
            "slippage_watch": sum(1 for l in all_lines if l["slippage_tier"] == "SLIPPAGE_WATCH"),
            "watchlist_act_now": sum(1 for l in all_lines if l["watchlist_tier"] == "ORDER_BY_CLOSING"),
            "watchlist_no_fallback": sum(1 for l in all_lines
                                         if l["watchlist_tier"] == "NO_ORDERING_FALLBACK"),
            "assessed_lines": len(scenario_lines),
        },
    }
    with open(OUT, "w") as f:
        json.dump(data, f, indent=2)
    print(f"wrote {OUT}: {data['counts']}")


if __name__ == "__main__":
    main()
