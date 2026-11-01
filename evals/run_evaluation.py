#!/usr/bin/env python3
"""
Stage 5 - full evaluation of the assessment agent against published
ground truth (data/eval_scenarios.csv, written BEFORE the agent was built).

Method: for each of the 10 scenarios, run the agent live (same code path
as app/agent.py main), then score:
  - status must match expected_status exactly
  - shortage_qty must match expected_shortage_qty exactly
  - notes_cited recorded (grounding evidence, reviewed by a human in the
    report - not auto-scored, because citation quality is a judgement)
Raw assessments are saved verbatim to evals/results_2026-11-01.json.
Runs are also appended to monitoring/runs.jsonl, like normal agent runs.

Reference date is pinned to 2026-11-02 by ingest/config.py - results do
not depend on the wall-clock date this script is run.
"""
import csv, json, os, sys
from datetime import datetime, timezone

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
from agent import assess, MODEL, LOG_PATH  # noqa: E402
from config import REFERENCE_DATE  # noqa: E402  (via ingest/ on path in agent)

RESULTS_PATH = os.path.join(ROOT, "evals", "results_2026-11-01.json")


def main():
    with open(os.path.join(ROOT, "data", "eval_scenarios.csv")) as f:
        scenarios = list(csv.DictReader(f))
    results, tot_in, tot_out = [], 0, 0
    for s in scenarios:
        a, usage = assess(None, s["event_id"], s["part_id"])
        rec = {"run_at": datetime.now(timezone.utc).isoformat(),
               "reference_date": REFERENCE_DATE, "model": MODEL,
               "usage": usage, "assessment": a, "evaluation": s["scenario_id"]}
        os.makedirs(os.path.dirname(LOG_PATH), exist_ok=True)
        with open(LOG_PATH, "a") as f:
            f.write(json.dumps(rec) + "\n")
        status_ok = a["status"] == s["expected_status"]
        qty_ok = a["shortage_qty"] == int(s["expected_shortage_qty"])
        tot_in += usage["input_tokens"]; tot_out += usage["output_tokens"]
        results.append({"scenario": s["scenario_id"], "event": s["event_id"],
                        "part": s["part_id"],
                        "expected_status": s["expected_status"],
                        "agent_status": a["status"], "status_match": status_ok,
                        "expected_shortage": int(s["expected_shortage_qty"]),
                        "agent_shortage": a["shortage_qty"], "shortage_match": qty_ok,
                        "notes_cited": a.get("notes_cited", []),
                        "coverage_summary": a.get("coverage_summary", ""),
                        "recommendation": a.get("recommendation", ""),
                        "usage": usage})
        print(f"{s['scenario_id']} {s['event_id']}/{s['part_id']}: "
              f"agent={a['status']}/{a['shortage_qty']} "
              f"expected={s['expected_status']}/{s['expected_shortage_qty']} "
              f"-> {'PASS' if status_ok and qty_ok else 'FAIL'}", flush=True)
    passed = sum(1 for r in results if r["status_match"] and r["shortage_match"])
    with open(RESULTS_PATH, "w") as f:
        json.dump({"model": MODEL, "reference_date": REFERENCE_DATE,
                   "score": f"{passed}/{len(results)}",
                   "total_usage": {"input_tokens": tot_in, "output_tokens": tot_out},
                   "results": results}, f, indent=2)
    print(f"\nScore: {passed}/{len(results)} (status + shortage, exact match)")
    print(f"Total usage: {tot_in} input + {tot_out} output tokens")
    print(f"Raw results -> {RESULTS_PATH}")


if __name__ == "__main__":
    main()
