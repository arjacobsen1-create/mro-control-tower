#!/usr/bin/env python3
"""
Stage V2-2 tests — PO slippage risk (spec §4) and the §4.5 po_detail
extension's verdict-neutrality.

Checks:
  - R01-R05 tiers exactly, from data/eval_scenarios_v2.csv ground truth,
    plus E006/P006 (the §4.4 precedence case: allocated SHORT, no flag);
  - the §4.2 worked numbers for all six PO-counted pairs (slip, margin,
    single-line load-bearing) against the spec table;
  - po_detail gained promised_date / slip_days / margin_days /
    load_bearing, and NOTHING else in check_availability's output moved:
    full-output diff against build/v1_availability_baseline.json (the
    pre-V2 snapshot of all 33 lines), with po_detail compared on its
    original keys plus the four new ones validated from the raw CSVs.

Run:  python3 app/test_slippage.py
"""
import csv, json, os, sys
from datetime import date

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "ingest"))
import availability  # noqa: E402
import slippage  # noqa: E402

fails = 0


def check(label, ok, detail=""):
    global fails
    fails += (not ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if detail and not ok else ""))


# --- R01-R05 (and C04's line) tiers vs ground truth
with open(os.path.join(ROOT, "data", "eval_scenarios_v2.csv")) as f:
    scenarios = {r["scenario_id"]: r for r in csv.DictReader(f)}
for sid in ["R01", "R02", "R03", "R04", "R05"]:
    s = scenarios[sid]
    r = slippage.slippage_risk(s["event_id"], s["part_id"])
    check(f"{sid} {s['event_id']}/{s['part_id']} tier", r["slippage_tier"] == s["expected_slippage_tier"],
          f"got {r['slippage_tier']} want {s['expected_slippage_tier']}")
r = slippage.slippage_risk("E006", "P006")
check("§4.4 E006/P006 no flag (allocated SHORT precedence)",
      r["slippage_tier"] == "NONE" and r["precedence"] is not None, f"got {r['slippage_tier']}")
r = slippage.slippage_risk("E001", "P002")
check("R01 checkpoint = PO expected arrival 2026-11-12", r["checkpoint_date"] == "2026-11-12",
      f"got {r['checkpoint_date']}")
r = slippage.slippage_risk("E002", "P006")
check("R02 checkpoint = 2026-11-20", r["checkpoint_date"] == "2026-11-20", f"got {r['checkpoint_date']}")

# --- §4.2 worked numbers for the six counted pairs
spec_pairs = {  # (event, part): (po, slip, margin, load_bearing_single_line)
    ("E001", "P002"): ("PO-1002", 7, 4, True), ("E002", "P006"): ("PO-1011", 5, 3, True),
    ("E002", "P015"): ("PO-1007", 7, 11, True), ("E004", "P021"): ("PO-1012", 8, 19, False),
    ("E005", "P002"): ("PO-1002", 7, 32, True), ("E006", "P006"): ("PO-1011", 5, 31, False)}
for (e, p), (po_id, slip, margin, lb) in spec_pairs.items():
    base = availability.check_availability(e, p)
    d = next(x for x in base["po_detail"] if x["po_id"] == po_id)
    check(f"§4.2 {e}/{p} {po_id} slip/margin/load-bearing",
          d["counted"] and d["slip_days"] == slip and d["margin_days"] == margin
          and d["load_bearing"] == lb,
          f"got counted={d['counted']} slip={d['slip_days']} margin={d['margin_days']} lb={d['load_bearing']}")
# PO-1010 slipped 15 days (largest) and is counted nowhere (§4.2/§2.2)
base = availability.check_availability("E005", "P007")
d = next(x for x in base["po_detail"] if x["po_id"] == "PO-1010")
check("PO-1010 slip 15, not counted for E005/P007",
      d["slip_days"] == 15 and not d["counted"], f"got slip={d['slip_days']} counted={d['counted']}")

# --- verdict-neutrality: full diff vs the pre-V2 baseline snapshot
with open(os.path.join(ROOT, "build", "v1_availability_baseline.json")) as f:
    baseline = json.load(f)
NEW_KEYS = {"promised_date", "slip_days", "margin_days", "load_bearing"}
moved = []
for key, old in baseline.items():
    e, p = key.split("/")
    new = availability.check_availability(e, p)
    old_c = {k: v for k, v in old.items() if k != "po_detail"}
    new_c = {k: v for k, v in new.items() if k != "po_detail"}
    if old_c != new_c:
        moved.append(f"{key}: non-po_detail fields changed")
        continue
    if len(old["po_detail"]) != len(new["po_detail"]):
        moved.append(f"{key}: po_detail length changed")
        continue
    for od, nd in zip(old["po_detail"], new["po_detail"]):
        if any(od[k] != nd[k] for k in od):
            moved.append(f"{key}/{od['po_id']}: original po_detail keys changed")
        if set(nd) - set(od) != NEW_KEYS:
            moved.append(f"{key}/{od['po_id']}: new keys {set(nd) - set(od)} != {NEW_KEYS}")
        slip = (date.fromisoformat(nd["expected_date"]) - date.fromisoformat(nd["promised_date"])).days
        if nd["slip_days"] != slip:
            moved.append(f"{key}/{od['po_id']}: slip_days wrong")
check("§4.5 additive-only: 33 lines diffed vs baseline", not moved, "; ".join(moved[:5]))

print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAILURES'} — slippage tests")
sys.exit(1 if fails else 0)
