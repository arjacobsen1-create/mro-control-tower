#!/usr/bin/env python3
"""
V2 rule-engine layer, spec §4 — PO slippage risk.

Risk is a property of a (line, PO) pair, not of a PO (§4.2): the same PO
can be SLIPPAGE_HIGH for one event and no risk at all for another. All
quantities (slip_days, margin_days, load_bearing) are computed in code —
slip/margin and the single-line load-bearing test come from
availability.check_availability's po_detail (§4.5); the tier itself is
assessed against the ALLOCATED view (§4.4):

  - a line that is SHORT or INSUFFICIENT_DATA in either view gets no
    slippage flag — shortage handling takes precedence (§4.3, §4.4);
  - load_bearing is re-checked against the allocated sourcing: the PO
    is load-bearing for the allocated verdict iff re-running the
    allocation without it changes the line's allocated status/shortage;
  - SLIPPAGE_HIGH  = load-bearing AND a repeat of the observed slip
                     would push the delivery past the event start
                     (slip_days > margin_days);
  - SLIPPAGE_WATCH = load-bearing, repeat slip holds, and
                     margin_days <= WATCH_MARGIN_DAYS (21, Decision D2);
  - otherwise no flag. Received POs and POs not counted for the line
    are never flagged (§4.3).
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingest"))
import availability  # noqa: E402
import allocation  # noqa: E402
from config import DB_PATH  # noqa: E402

WATCH_MARGIN_DAYS = 21  # Decision D2 (2026-11-06): 3 weeks = reaction window


def slippage_risk(event_id, part_id, db_path=DB_PATH, policy="chronological"):
    """Slippage assessment for one (event, part) demand line."""
    base = availability.check_availability(event_id, part_id, db_path)
    if "error" in base:
        return base
    alloc = allocation.allocate_all(db_path, policy)
    line = alloc["lines"][(event_id, part_id)]
    counted = [d for d in base["po_detail"] if d["counted"]]
    pairs = []
    for d in counted:
        without = allocation.allocate_all(db_path, policy, exclude_po=d["po_id"])
        wline = without["lines"][(event_id, part_id)]
        lb_alloc = (wline["allocated_status"], wline["allocated_shortage_qty"]) != \
                   (line["allocated_status"], line["allocated_shortage_qty"])
        pairs.append({
            "po_id": d["po_id"], "outstanding": d["outstanding"],
            "promised_date": d["promised_date"], "expected_date": d["expected_date"],
            "slip_days": d["slip_days"], "margin_days": d["margin_days"],
            "load_bearing": d["load_bearing"],          # §4.1 single-line view
            "load_bearing_allocated": lb_alloc,          # §4.4 allocated view
            "repeat_slip_breaks": d["slip_days"] > d["margin_days"]})
    precedence = None
    if base["status"] in ("SHORT_UNCOVERED", "INSUFFICIENT_DATA") or \
            line["allocated_status"] in ("SHORT_UNCOVERED", "INSUFFICIENT_DATA"):
        tier, precedence = "NONE", "shortage_or_insufficient_takes_precedence"
    else:
        tier = "NONE"
        for p in pairs:
            if p["load_bearing_allocated"] and p["repeat_slip_breaks"]:
                tier = "SLIPPAGE_HIGH"
                break
            if p["load_bearing_allocated"] and p["margin_days"] <= WATCH_MARGIN_DAYS:
                tier = "SLIPPAGE_WATCH"
    checkpoint = None
    if tier == "SLIPPAGE_HIGH":
        checkpoint = min(p["expected_date"] for p in pairs
                         if p["load_bearing_allocated"] and p["repeat_slip_breaks"])
    return {"event_id": event_id, "part_id": part_id,
            "v1_status": base["status"],
            "allocated_status": line["allocated_status"],
            "contention": line["contention"],
            "slippage_tier": tier,
            "watch_margin_days": WATCH_MARGIN_DAYS,
            "precedence": precedence,
            "checkpoint_date": checkpoint,  # §4.6: the counted PO's expected arrival
            "pairs": pairs}
