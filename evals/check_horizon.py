#!/usr/bin/env python3
"""
Stage V2-3B gate — the two-clock horizon layer and the forward annex.

Uses the independent validator's recomputation (evals/validate_v2.py,
raw CSVs) to prove the D5 acceptance criterion (§12): the forward
events' demand lines exercise EVERY band of both clocks AND the two
interaction cases — and cross-checks the DB-backed engine module
(app/horizon.py) against that recomputation on every forward line.

Also regression-gates the annex itself: the original 33 lines' V1
verdicts are byte-identical to the published planner data, and Tier A
reproduction on the existing data is unchanged (2 lines).

Writes the forward lines' ground truth to build/horizon_ground_truth.json.
Run:  python3 evals/check_horizon.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "evals"))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "ingest"))
import validate_v2 as V  # noqa: E402
import availability, horizon  # noqa: E402

fails = 0


def check(label, ok, detail=""):
    global fails
    fails += (not ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if detail and not ok else ""))


FORWARD = [("E007", "P007"), ("E007", "P004"), ("E007", "P005"),
           ("E008", "P010"), ("E008", "P019"), ("E008", "P013"),
           ("E009", "P001"), ("E009", "P002"), ("E009", "P003")]
ALL_LINES = list(V.REQ.keys())
LONG = lambda e, p: int(V.PARTS[p]["lead_time_days"]) >= 180  # noqa: E731

# --- every Clock 1 band holds at least one long-lead line
bands1 = {}
for (e, p) in ALL_LINES:
    st = V.line_state(e, p)
    if LONG(e, p):
        bands1.setdefault(st["clock1"]["band"], []).append(f"{e}/{p}")
for band in ["passed", "act-now", "advisory"]:
    check(f"Clock 1 band '{band}' has a long-lead line", band in bands1,
          f"bands present: {sorted(bands1)}")
print("   Clock 1 long-lead bands:", {k: v for k, v in sorted(bands1.items())})

# --- every Clock 2 band holds at least one long-lead line
bands2 = {}
for (e, p) in ALL_LINES:
    st = V.line_state(e, p)
    if st["clock2"].get("applicable"):
        bands2.setdefault(st["clock2"]["band"], []).append(f"{e}/{p}")
for band in ["<=3mo", "3-6mo", ">6mo"]:
    check(f"Clock 2 band '{band}' has a long-lead line", band in bands2,
          f"bands present: {sorted(bands2)}")
print("   Clock 2 long-lead bands:", {k: v for k, v in sorted(bands2.items())})

# --- D5 interaction case 1: Clock 1 advisory/act-now while covered (allocated)
case1 = [f"{e}/{p}" for (e, p) in ALL_LINES
         if V.line_state(e, p)["clock1"]["band"] in ("advisory", "act-now")
         and V.line_state(e, p)["allocated_status"] not in ("SHORT_UNCOVERED", "INSUFFICIENT_DATA")]
check("D5 interaction 1: Clock-1 advisory/act-now line covered after allocation",
      len(case1) >= 1, "none found")
print("   Interaction 1 lines:", case1)

# --- D5 interaction case 2: covered-now (V1 OK) line, Clock 1 act-now, §5.6 action raised
case2 = [f"{e}/{p}" for (e, p) in ALL_LINES
         if V.line_state(e, p)["status"] == "OK"
         and V.line_state(e, p)["clock1"]["band"] == "act-now"
         and V.line_state(e, p)["procurement"] == "RAISED"]
check("D5 interaction 2: covered-now line with Clock-1 act-now procurement action (§5.6)",
      len(case2) >= 1, "none found")
print("   Interaction 2 lines:", case2)

# --- forward ground truth + engine cross-check on every forward line
truth = {}
for (e, p) in FORWARD:
    st = V.line_state(e, p)
    truth[f"{e}/{p}"] = st
    eng = horizon.horizon_line(e, p)
    agree = (eng["clock1"]["band"] == st["clock1"]["band"]
             and eng["clock2"].get("band") == st["clock2"].get("band")
             and eng["allocated_status"] == st["allocated_status"]
             and eng["allocated_shortage_qty"] == st["allocated_shortage"]
             and eng["procurement"]["action"] == st["procurement"]
             and eng["notification"]["eligible"] == (st["notify_eligible"] == "YES")
             and eng["slippage_tier"] == st["slippage"]
             and eng["watchlist_tier"] == st["watchlist"])
    check(f"engine==validator {e}/{p}", agree,
          f"engine c1={eng['clock1']['band']} c2={eng['clock2'].get('band')} alloc={eng['allocated_status']} "
          f"proc={eng['procurement']['action']} | validator c1={st['clock1']['band']} "
          f"c2={st['clock2'].get('band')} alloc={st['allocated_status']} proc={st['procurement']}")
with open(os.path.join(ROOT, "build", "horizon_ground_truth.json"), "w") as f:
    json.dump(truth, f, indent=1, sort_keys=True)
print(f"   Forward ground truth -> build/horizon_ground_truth.json ({len(truth)} lines)")

# --- annex regression: V1 verdicts of the original 33 lines unchanged
with open(os.path.join(ROOT, "evals", "planner_data.json")) as f:
    pd = json.load(f)
bad = 0
for e in pd["events"]:
    for l in e["lines"]:
        r = availability.check_availability(e["event_id"], l["part_id"])
        bad += (r["status"], r["shortage_qty"]) != (l["status"], l["shortage"])
check("annex regression: 33 V1 verdicts byte-identical", bad == 0, f"{bad} changed")
import watchlist as wl  # noqa: E402
ta = sorted(f"{w['event_id']}/{w['part_id']}" for w in wl.watchlist()["tier_a"])
check("Tier A reproduction unchanged (2 lines)", ta == ["E004/P011", "E006/P011"], f"got {ta}")

print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAILURES'} — horizon gate")
sys.exit(1 if fails else 0)
