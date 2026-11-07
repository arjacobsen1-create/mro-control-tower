#!/usr/bin/env python3
"""
Stage V2-5 — evaluation of the V2 agent against the V2 ground truth
(data/eval_scenarios_v2.csv, written and code-validated in Stage V2-0
BEFORE any agent run), with the 10 V1 scenarios re-run unchanged as a
regression set through the untouched V1 agent path.

Scoring is exact-match per scenario on the fields that scenario tests
(spec §6.1):
  C01-C06   allocated status + allocated shortage
  R01-R05   slippage tier
  W01-W05   watchlist tier
  P01       single-line status OK + watchlist ORDER_BY_CLOSING +
            procurement action RAISED with a documented need quoted
  X01       feasible_recovery_exists = false, recommended decision
            escalate_defer, recovery path defer, draft notification
  X02a      draft notification prepared, checkpoint 2026-11-12,
            recovery path recorded, four verifications outstanding
  X02b      NO customer escalation (notification NONE) and an internal
            handling decision (approve_monitor_po / escalate_expedite)
  V1 set    status + shortage (as Stage 5)

Every run is appended to monitoring/runs.jsonl, as in V1. Raw results
go to evals/results_v2_2026-11-06.json. The gate for this stage is
that the run happened, was scored exact-match and is written up —
scores are whatever they are (spec §10, Stage V2-5).

Run:  python3 evals/run_evaluation_v2.py
"""
import csv, json, os, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "ingest"))
from agent import assess, assess_v2, MODEL, LOG_PATH  # noqa: E402
from config import REFERENCE_DATE  # noqa: E402

RESULTS_PATH = os.path.join(ROOT, "evals", "results_v2_2026-11-06.json")
PRICE_IN, PRICE_OUT = 1.0, 5.0  # Haiku list prices, as in monitoring


def log_run(a, usage, sid, eset):
    rec = {"run_at": datetime.now(timezone.utc).isoformat(),
           "reference_date": REFERENCE_DATE, "model": MODEL,
           "usage": usage, "assessment": a, "evaluation": sid,
           "evaluation_set": eset}
    os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
    with open(LOG_PATH, "a") as f:
        f.write(json.dumps(rec) + "\n")


def score_v2(s, a):
    """Returns (passed, [field results]) for one V2 scenario."""
    sid = s["scenario_id"]
    F = []
    def chk(name, got, want):
        F.append({"field": name, "got": got, "want": want, "match": got == want})
    if sid.startswith("C"):
        chk("allocated_status", a["allocated_status"], s["expected_allocated_status"])
        chk("allocated_shortage_qty", a["allocated_shortage_qty"],
            int(s["expected_allocated_shortage_qty"]))
        chk("contention", a["contention"], s["expected_contention"])
    elif sid.startswith("R"):
        chk("slippage_tier", a["slippage_tier"], s["expected_slippage_tier"])
    elif sid.startswith("W"):
        chk("watchlist_tier", a["watchlist_tier"], s["expected_watchlist_tier"])
    elif sid == "P01":
        chk("status", a["status"], "OK")
        chk("watchlist_tier", a["watchlist_tier"], "ORDER_BY_CLOSING")
        chk("procurement_action", a["procurement_action"], "RAISED")
        chk("procurement_need_documented",
            bool(a.get("procurement_need")), True)
    elif sid == "X01":
        chk("feasible_recovery_exists", a["feasible_recovery_exists"], False)
        chk("recommended_decision", a["recommended_decision"], "escalate_defer")
        chk("recovery_path", a["recovery_path"], "defer")
        chk("customer_notification.action", a["customer_notification"]["action"], "PREPARE_DRAFT")
    elif sid == "X02a":
        chk("customer_notification.action", a["customer_notification"]["action"], "PREPARE_DRAFT")
        chk("customer_notification.checkpoint_date",
            a["customer_notification"]["checkpoint_date"], "2026-11-12")
        chk("recovery_path_recorded", bool(a.get("recovery_path")), True)
        chk("verifications_outstanding", a["customer_notification"]["verifications_outstanding"],
            ["affected event", "material shortfall", "recovery options", "proposed communication"])
    elif sid == "X02b":
        chk("customer_notification.action", a["customer_notification"]["action"], "NONE")
        chk("recommended_decision_internal",
            a["recommended_decision"] in ("approve_monitor_po", "escalate_expedite"), True)
    return all(f["match"] for f in F), F


def main():
    with open(os.path.join(ROOT, "data", "eval_scenarios_v2.csv")) as f:
        v2_scenarios = list(csv.DictReader(f))
    with open(os.path.join(ROOT, "data", "eval_scenarios.csv")) as f:
        v1_scenarios = list(csv.DictReader(f))

    results, tot_in, tot_out = [], 0, 0
    for s in v2_scenarios:
        try:
            a, usage = assess_v2(None, s["event_id"], s["part_id"])
            log_run(a, usage, s["scenario_id"], "v2")
            passed, fields = score_v2(s, a)
            err = None
        except Exception as ex:  # recorded, counted as a miss — never hidden
            import traceback
            a, usage, passed, fields = None, {"input_tokens": 0, "output_tokens": 0}, False, []
            err = repr(ex) + "\n" + traceback.format_exc()
        tot_in += usage["input_tokens"]; tot_out += usage["output_tokens"]
        results.append({"scenario": s["scenario_id"], "set": "v2",
                        "event": s["event_id"], "part": s["part_id"],
                        "passed": passed, "fields": fields, "error": err,
                        "assessment": a, "usage": usage})
        print(f"{s['scenario_id']} {s['event_id']}/{s['part_id']}: "
              f"{'PASS' if passed else 'FAIL'}" + (f" ({err})" if err else ""), flush=True)

    reg = []
    for s in v1_scenarios:
        try:
            a, usage = assess(None, s["event_id"], s["part_id"])
            log_run(a, usage, s["scenario_id"], "v1-regression")
            passed = (a["status"] == s["expected_status"]
                      and a["shortage_qty"] == int(s["expected_shortage_qty"]))
            err = None
        except Exception as ex:
            import traceback
            a, usage, passed = None, {"input_tokens": 0, "output_tokens": 0}, False
            err = repr(ex) + "\n" + traceback.format_exc()
        tot_in += usage["input_tokens"]; tot_out += usage["output_tokens"]
        reg.append({"scenario": s["scenario_id"], "set": "v1-regression",
                    "event": s["event_id"], "part": s["part_id"], "passed": passed,
                    "expected_status": s["expected_status"],
                    "agent_status": a["status"] if a else None,
                    "expected_shortage": int(s["expected_shortage_qty"]),
                    "agent_shortage": a["shortage_qty"] if a else None,
                    "error": err, "assessment": a, "usage": usage})
        print(f"{s['scenario_id']} {s['event_id']}/{s['part_id']} (V1 regression): "
              f"{'PASS' if passed else 'FAIL'}" + (f" ({err})" if err else ""), flush=True)

    v2_pass = sum(1 for r in results if r["passed"])
    reg_pass = sum(1 for r in reg if r["passed"])
    cost = tot_in / 1e6 * PRICE_IN + tot_out / 1e6 * PRICE_OUT
    with open(RESULTS_PATH, "w") as f:
        json.dump({"model": MODEL, "reference_date": REFERENCE_DATE,
                   "v2_score": f"{v2_pass}/{len(results)}",
                   "v1_regression_score": f"{reg_pass}/{len(reg)}",
                   "total_usage": {"input_tokens": tot_in, "output_tokens": tot_out},
                   "estimated_cost_usd": round(cost, 4),
                   "results": results, "v1_regression": reg}, f, indent=2)
    print(f"\nV2 score: {v2_pass}/{len(results)}   V1 regression: {reg_pass}/{len(reg)}")
    print(f"Total usage: {tot_in} input + {tot_out} output tokens (est. US${cost:.2f})")
    print(f"Raw results -> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
