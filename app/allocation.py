#!/usr/bin/env python3
"""
V2 rule-engine layer, spec §3 — cross-event allocation.

Beside availability.check_availability, which is NOT modified: the V1
function keeps answering "could this line be covered, alone?" and this
module answers "can they ALL be covered?" by allocating the physical
pools to events in priority order (Decision D1: chronological by
planned_start, tie-break event_id) and recomputing each line's verdict
against what remains. Partial allocation is retained: a line that ends
short still consumes what it drew (§3.2).

All arithmetic is done here, in code. Pools per part (§3.2):
  (a) site stock (on hand - reserved) per (part, site);
  (b) PO pool — each countable PO's outstanding balance, drawable only
      by lines at its delivery site with expected_date <= event start;
  (c) network stock = the other sites' site-stock pools, drawn after
      the line's own site and PO pools, in the fixed site order;
  (d) alternate pool — the alternate part's available stock at the
      consuming event's site.
Consumption order within a line mirrors the V1 cascade exactly.
INSUFFICIENT_DATA lines do not consume and are not re-evaluated.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingest"))
import availability  # noqa: E402
from availability import SITES  # noqa: E402
from config import DB_PATH  # noqa: E402

POLICIES = ("chronological",)


def _priority(events, policy):
    if policy == "chronological":
        return sorted(events, key=lambda e: (e["planned_start"], e["event_id"]))
    raise ValueError(f"unknown allocation policy {policy!r}")


def _load(con):
    parts = {r["part_id"]: dict(r) for r in con.execute("SELECT * FROM parts")}
    inv = {}
    for r in con.execute("SELECT * FROM inventory"):
        inv[(r["part_id"], r["site"])] = r["qty_on_hand"] - r["qty_reserved"]
    pos = [dict(r) for r in con.execute("SELECT * FROM purchase_orders")]
    events = {r["event_id"]: dict(r) for r in con.execute("SELECT * FROM maintenance_schedule")}
    demand = {}
    for r in con.execute("SELECT * FROM demand"):
        demand.setdefault(r["part_id"], []).append(
            {"event_id": r["event_id"], "qty_required": r["qty_required"]})
    return parts, inv, pos, events, demand


def _counted(po, site, start):
    return (po["status"] in ("open", "partially_received")
            and po["delivery_site"] == site and po["expected_date"] <= start
            and po["qty_ordered"] - po["qty_received"] > 0)


def _cascade(ev, part_id, req, stock, po_bal, pos_by_part, parts):
    """Draw against the given pools (mutated). Returns (status, shortage, ledger)."""
    site, start = ev["site"], ev["planned_start"]
    need = req
    ledger = {"site_stock": 0, "po": {}, "network": {}, "alternate": 0,
              "alternate_part_id": parts[part_id]["alternate_part_id"]}
    q = min(need, stock.get((part_id, site), 0))
    ledger["site_stock"] = q
    stock[(part_id, site)] = stock.get((part_id, site), 0) - q
    need -= q
    for po in sorted(pos_by_part.get(part_id, []),
                     key=lambda p: (p["expected_date"], p["po_id"])):
        if need <= 0:
            break
        if _counted(po, site, start) and po_bal.get(po["po_id"], 0) > 0:
            q = min(need, po_bal[po["po_id"]])
            if q:
                ledger["po"][po["po_id"]] = q
                po_bal[po["po_id"]] -= q
                need -= q
    for s in SITES:
        if s == site or need <= 0:
            continue
        q = min(need, stock.get((part_id, s), 0))
        if q:
            ledger["network"][s] = q
            stock[(part_id, s)] -= q
            need -= q
    alt_id = parts[part_id]["alternate_part_id"]
    if alt_id and need > 0:
        q = min(need, stock.get((alt_id, site), 0))
        ledger["alternate"] = q
        stock[(alt_id, site)] = stock.get((alt_id, site), 0) - q
        need -= q
    site_q, po_q = ledger["site_stock"], sum(ledger["po"].values())
    net_q = sum(ledger["network"].values())
    if site_q >= req:
        status = "OK"
    elif site_q + po_q >= req:
        status = "COVERED_BY_PO"
    elif site_q + po_q + net_q >= req:
        status = "COVERED_BY_TRANSFER"
    elif site_q + po_q + net_q + ledger["alternate"] >= req:
        status = "COVERED_BY_ALTERNATE"
    else:
        status = "SHORT_UNCOVERED"
    return status, (need if status == "SHORT_UNCOVERED" else 0), ledger


def _empty_ledger(alt_id):
    return {"site_stock": 0, "po": {}, "network": {}, "alternate": 0,
            "alternate_part_id": alt_id}


def allocate_all(db_path=DB_PATH, policy="chronological", exclude_po=None):
    """Allocate every part's pools across its demanding events.

    Returns {"policy": policy,
             "lines": {(event_id, part_id): {allocated_status,
                        allocated_shortage_qty, ledger, contention,
                        v1_status}},
             "pools": {part_id: {"initial": {...}, "remaining": {...}}}}.
    Contention (§3.2): CONTENDED_SHORT (covered in V1, short after
    allocation), CONTENDED_COVERED (still covered, but tier or sources
    changed vs the line's alone-cascade), UNCONTENDED otherwise.
    exclude_po zeroes one PO's balance everywhere — the §4.4
    load-bearing re-check used by the slippage module."""
    if policy not in POLICIES:
        raise ValueError(f"unknown allocation policy {policy!r}")
    con = availability._con(db_path)
    parts, inv, pos, events, demand = _load(con)
    con.close()
    pos_by_part = {}
    for po in pos:
        pos_by_part.setdefault(po["part_id"], []).append(po)

    def fresh():
        stock = dict(inv)
        po_bal = {p["po_id"]: p["qty_ordered"] - p["qty_received"]
                  for p in pos if p["status"] in ("open", "partially_received")}
        if exclude_po:  # §4.4 load-bearing re-check: pretend this PO is absent
            po_bal[exclude_po] = 0
        return stock, po_bal

    lines, pools = {}, {}
    for part_id, dlines in demand.items():
        evs = _priority([events[d["event_id"]] for d in dlines], policy)
        req = {d["event_id"]: d["qty_required"] for d in dlines}
        stock, po_bal = fresh()
        initial = {"stock": {s: stock.get((part_id, s), 0) for s in SITES},
                   "po": {p["po_id"]: po_bal.get(p["po_id"], 0)
                          for p in pos_by_part.get(part_id, [])}}
        for ev in evs:
            eid = ev["event_id"]
            v1 = availability.check_availability(eid, part_id, db_path)
            alt_id = parts[part_id]["alternate_part_id"]
            if v1["status"] == "INSUFFICIENT_DATA":
                lines[(eid, part_id)] = {
                    "allocated_status": "INSUFFICIENT_DATA", "allocated_shortage_qty": 0,
                    "ledger": _empty_ledger(alt_id), "contention": "UNCONTENDED",
                    "v1_status": "INSUFFICIENT_DATA"}
                continue
            a_stock, a_po = fresh()
            a_status, _, a_ledger = _cascade(ev, part_id, req[eid], a_stock, a_po,
                                             pos_by_part, parts)
            status, shortage, ledger = _cascade(ev, part_id, req[eid], stock, po_bal,
                                                pos_by_part, parts)
            if v1["status"] != "SHORT_UNCOVERED" and status == "SHORT_UNCOVERED":
                contention = "CONTENDED_SHORT"
            elif status == "SHORT_UNCOVERED":
                contention = "UNCONTENDED"
            elif status != v1["status"] or ledger != a_ledger:
                contention = "CONTENDED_COVERED"
            else:
                contention = "UNCONTENDED"
            lines[(eid, part_id)] = {
                "allocated_status": status, "allocated_shortage_qty": shortage,
                "ledger": ledger, "contention": contention, "v1_status": v1["status"]}
        pools[part_id] = {"initial": initial,
                          "remaining": {"stock": {s: stock.get((part_id, s), 0) for s in SITES},
                                        "po": {p["po_id"]: po_bal.get(p["po_id"], 0)
                                               for p in pos_by_part.get(part_id, [])}}}
    return {"policy": policy, "lines": lines, "pools": pools}


def allocated_availability(event_id, part_id, db_path=DB_PATH, policy="chronological"):
    """V1 breakdown plus the allocated view for one demand line (§3.2 output)."""
    base = availability.check_availability(event_id, part_id, db_path)
    if "error" in base:
        return base
    alloc = allocate_all(db_path, policy)
    line = alloc["lines"].get((event_id, part_id))
    if line is None:
        return {**base, "error": "no demand line for this combination"}
    return {**base,
            "allocated_status": line["allocated_status"],
            "allocated_shortage_qty": line["allocated_shortage_qty"],
            "contention": line["contention"],
            "allocation_policy": policy,
            "pool_ledger": line["ledger"],
            "pool_remaining": alloc["pools"][part_id]["remaining"]}
