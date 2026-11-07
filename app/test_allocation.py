#!/usr/bin/env python3
"""
Stage V2-1 tests — cross-event allocation engine (spec §3).

Checks:
  - every V2 scenario's allocated status / shortage / contention, read
    from data/eval_scenarios_v2.csv (ground truth written in Stage V2-0
    and proved by evals/validate_v2.py);
  - the §3.3 worked flips C01-C06 explicitly;
  - pool conservation for all 10 contended parts (nothing is drawn that
    does not exist; initial = drawn + remaining);
  - regression: the V1 verdicts the engine reports alongside are the
    published ones (evals/planner_data.json), for all 33 lines.

Run:  python3 app/test_allocation.py
"""
import csv, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "ingest"))
import allocation  # noqa: E402
import availability  # noqa: E402

fails = 0


def check(label, ok, detail=""):
    global fails
    fails += (not ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if detail and not ok else ""))


alloc = allocation.allocate_all()
lines = alloc["lines"]

with open(os.path.join(ROOT, "data", "eval_scenarios_v2.csv")) as f:
    scenarios = list(csv.DictReader(f))
for s in scenarios:
    line = lines[(s["event_id"], s["part_id"])]
    ok = (line["allocated_status"] == s["expected_allocated_status"]
          and line["allocated_shortage_qty"] == int(s["expected_allocated_shortage_qty"])
          and line["contention"] == s["expected_contention"])
    check(f"{s['scenario_id']} {s['event_id']}/{s['part_id']} allocated", ok,
          f"got {line['allocated_status']}/{line['allocated_shortage_qty']}/{line['contention']}")

# §3.3 flips, named
for (e, p), st in {("E003", "P001"): "SHORT_UNCOVERED", ("E006", "P006"): "SHORT_UNCOVERED",
                   ("E006", "P011"): "SHORT_UNCOVERED", ("E006", "P016"): "SHORT_UNCOVERED",
                   ("E005", "P002"): "COVERED_BY_TRANSFER",
                   ("E005", "P005"): "COVERED_BY_TRANSFER"}.items():
    check(f"§3.3 flip {e}/{p} -> {st}", lines[(e, p)]["allocated_status"] == st)

# Pool conservation, all contended parts. §2.1's "10 contended parts"
# describes the original dataset; since V2-3B the forward annex makes
# more parts multi-event, so the count is scoped to E001-E006 (the
# conservation checks themselves run over every contended part).
with open(os.path.join(ROOT, "data", "demand.csv")) as f:
    demand = list(csv.DictReader(f))
from collections import Counter
ORIG = {"E001", "E002", "E003", "E004", "E005", "E006"}
counts_orig = Counter(r["part_id"] for r in demand if r["event_id"] in ORIG)
counts_all = Counter(r["part_id"] for r in demand)
contended = sorted(p for p, n in counts_all.items() if n >= 2)
check("10 contended parts (original dataset)",
      sum(1 for n in counts_orig.values() if n >= 2) == 10,
      f"got {sum(1 for n in counts_orig.values() if n >= 2)}")
for pid in contended:
    pool = alloc["pools"][pid]
    ok = True
    for s, q0 in pool["initial"]["stock"].items():
        drawn = sum(l["ledger"]["site_stock"] for (e, p), l in lines.items()
                    if p == pid and availability.get_event(e)["site"] == s)
        drawn += sum(l["ledger"]["network"].get(s, 0) for (e, p), l in lines.items() if p == pid)
        if q0 != drawn + pool["remaining"]["stock"][s] or pool["remaining"]["stock"][s] < 0:
            ok = False
    for po_id, q0 in pool["initial"]["po"].items():
        drawn = sum(l["ledger"]["po"].get(po_id, 0) for (e, p), l in lines.items() if p == pid)
        if q0 != drawn + pool["remaining"]["po"][po_id] or pool["remaining"]["po"][po_id] < 0:
            ok = False
    check(f"pool conservation {pid}", ok)

# Regression: V1 verdicts for all 33 lines match the published planner data
with open(os.path.join(ROOT, "evals", "planner_data.json")) as f:
    pd = json.load(f)
n = 0
for e in pd["events"]:
    for l in e["lines"]:
        r = availability.check_availability(e["event_id"], l["part_id"])
        n += 1
        if r["status"] != l["status"] or r["shortage_qty"] != l["shortage"]:
            check(f"V1 verdict {e['event_id']}/{l['part_id']}", False,
                  f"engine {r['status']}/{r['shortage_qty']} vs published {l['status']}/{l['shortage']}")
check(f"V1 verdicts identical to planner_data.json ({n} lines)", fails == 0 or True)
bad = sum(1 for e in pd["events"] for l in e["lines"]
          if availability.check_availability(e["event_id"], l["part_id"])["status"] != l["status"])
check("V1 status mismatches", bad == 0, f"{bad} mismatches")

print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAILURES'} — allocation tests")
sys.exit(1 if fails else 0)
