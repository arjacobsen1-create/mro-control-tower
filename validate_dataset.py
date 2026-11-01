#!/usr/bin/env python3
"""
Validate the synthetic MRO dataset: recompute every eval scenario outcome
from parts/inventory/POs/schedule/demand using the documented availability
rule, and compare against the ground truth in eval_scenarios.csv.

Availability rule (data dictionary):
  site_available    = qty_on_hand - qty_reserved at the event site
                      (missing inventory row at the event site counts as no record)
  inbound           = sum(qty_ordered - qty_received) over POs for the part with
                      status in {open, partially_received}, delivery_site = event site,
                      expected_date <= event planned_start
  network_available = sum of site_available over all other sites
  alternate_avail   = site_available of the part's alternate at the event site
Classification order:
  INSUFFICIENT_DATA (no inventory row at event site AND no PO rows for the part)
  > OK > COVERED_BY_PO > COVERED_BY_TRANSFER > COVERED_BY_ALTERNATE > SHORT_UNCOVERED
"""
import csv, os, sys

D = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
def load(name):
    with open(os.path.join(D, name)) as f: return list(csv.DictReader(f))

parts = {r["part_id"]: r for r in load("parts.csv")}
inv = {(r["part_id"], r["site"]): r for r in load("inventory.csv")}
pos = load("purchase_orders.csv")
events = {r["event_id"]: r for r in load("maintenance_schedule.csv")}
demand = {(r["event_id"], r["part_id"]): int(r["qty_required"]) for r in load("demand.csv")}
evals = load("eval_scenarios.csv")
SITES = ["YUL-H1", "YYZ-H2", "YYC-H3"]

def site_avail(pid, site):
    r = inv.get((pid, site))
    return None if r is None else int(r["qty_on_hand"]) - int(r["qty_reserved"])

def classify(eid, pid):
    ev = events[eid]; site = ev["site"]; start = ev["planned_start"]
    req = demand[(eid, pid)]
    sa = site_avail(pid, site)
    po_rows = [p for p in pos if p["part_id"] == pid]
    if sa is None and not po_rows:
        return "INSUFFICIENT_DATA", 0
    sa = sa or 0
    inbound = sum(int(p["qty_ordered"]) - int(p["qty_received"]) for p in po_rows
                  if p["status"] in ("open", "partially_received")
                  and p["delivery_site"] == site and p["expected_date"] <= start)
    network = sum(site_avail(pid, s) or 0 for s in SITES if s != site)
    alt_id = parts[pid]["alternate_part_id"]
    alt = (site_avail(alt_id, site) or 0) if alt_id else 0
    if sa >= req: return "OK", 0
    if sa + inbound >= req: return "COVERED_BY_PO", 0
    if sa + inbound + network >= req: return "COVERED_BY_TRANSFER", 0
    if sa + inbound + network + alt >= req: return "COVERED_BY_ALTERNATE", 0
    return "SHORT_UNCOVERED", req - (sa + inbound + network + alt)

fails = 0
for e in evals:
    status, shortage = classify(e["event_id"], e["part_id"])
    ok = status == e["expected_status"] and shortage == int(e["expected_shortage_qty"])
    print(f"{e['scenario_id']} {e['event_id']}/{e['part_id']}: computed={status} shortage={shortage} "
          f"expected={e['expected_status']} shortage={e['expected_shortage_qty']} -> {'PASS' if ok else 'FAIL'}")
    fails += (not ok)
print(f"\n{len(evals)-fails}/{len(evals)} scenarios match ground truth.")
sys.exit(1 if fails else 0)
