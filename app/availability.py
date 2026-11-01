#!/usr/bin/env python3
"""
Availability rule engine — the deterministic core of the Control Tower.

ALL stock arithmetic lives here, in code. The language model never computes
quantities; it calls check_availability() and works from the returned,
auditable breakdown. Rule as documented in docs/data_dictionary.md,
evaluated as of the pinned reference date (see ingest/config.py).
"""
import os, sqlite3, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingest"))
from config import DB_PATH, REFERENCE_DATE  # noqa: E402

SITES = ["YUL-H1", "YYZ-H2", "YYC-H3"]


def _con(db_path):
    con = sqlite3.connect(db_path)
    con.row_factory = sqlite3.Row
    return con


def get_event(event_id, db_path=DB_PATH):
    con = _con(db_path)
    r = con.execute("SELECT * FROM maintenance_schedule WHERE event_id=?", (event_id,)).fetchone()
    con.close()
    return dict(r) if r else None


def get_demand(event_id, db_path=DB_PATH):
    con = _con(db_path)
    rows = con.execute(
        "SELECT d.part_id, p.description, d.qty_required FROM demand d "
        "JOIN parts p ON p.part_id=d.part_id WHERE d.event_id=? ORDER BY d.part_id",
        (event_id,)).fetchall()
    con.close()
    return [dict(r) for r in rows]


def get_part(part_id, db_path=DB_PATH):
    con = _con(db_path)
    r = con.execute("SELECT * FROM parts WHERE part_id=?", (part_id,)).fetchone()
    con.close()
    return dict(r) if r else None


def _site_available(con, part_id, site):
    r = con.execute("SELECT qty_on_hand, qty_reserved FROM inventory WHERE part_id=? AND site=?",
                    (part_id, site)).fetchone()
    if r is None:
        return None
    return r["qty_on_hand"] - r["qty_reserved"]


def check_availability(event_id, part_id, db_path=DB_PATH):
    """Full coverage breakdown for one (event, part) demand line."""
    con = _con(db_path)
    ev = con.execute("SELECT * FROM maintenance_schedule WHERE event_id=?", (event_id,)).fetchone()
    dem = con.execute("SELECT qty_required FROM demand WHERE event_id=? AND part_id=?",
                      (event_id, part_id)).fetchone()
    part = con.execute("SELECT * FROM parts WHERE part_id=?", (part_id,)).fetchone()
    if ev is None or dem is None or part is None:
        con.close()
        return {"error": "unknown event/part or no demand line for this combination"}
    site, start, req = ev["site"], ev["planned_start"], dem["qty_required"]

    site_avail = _site_available(con, part_id, site)
    po_rows = con.execute("SELECT * FROM purchase_orders WHERE part_id=?", (part_id,)).fetchall()

    if site_avail is None and not po_rows:
        con.close()
        return {"event_id": event_id, "part_id": part_id, "part_description": part["description"],
                "site": site, "event_start": start, "qty_required": req,
                "status": "INSUFFICIENT_DATA", "shortage_qty": 0,
                "evidence": {"site_available": None, "inbound_before_need": 0,
                             "network_available": 0, "alternate_available": 0},
                "lead_time_check": _lead_time_check(part["lead_time_days"], start),
                "po_detail": [], "network_detail": {},
                "reason": "No inventory record at the event site and no purchase orders for this part."}

    inbound, po_detail = 0, []
    for po in po_rows:
        outstanding = po["qty_ordered"] - po["qty_received"]
        counted = (po["status"] in ("open", "partially_received")
                   and po["delivery_site"] == site and po["expected_date"] <= start
                   and outstanding > 0)
        if counted:
            inbound += outstanding
        po_detail.append({"po_id": po["po_id"], "outstanding": outstanding,
                          "expected_date": po["expected_date"], "delivery_site": po["delivery_site"],
                          "status": po["status"], "counted": counted})
    network_detail = {s: (_site_available(con, part_id, s) or 0) for s in SITES if s != site}
    network = sum(network_detail.values())
    alt_id = part["alternate_part_id"]
    alt_avail = (_site_available(con, alt_id, site) or 0) if alt_id else 0
    con.close()

    sa = site_avail or 0
    if sa >= req:
        status, shortage = "OK", 0
    elif sa + inbound >= req:
        status, shortage = "COVERED_BY_PO", 0
    elif sa + inbound + network >= req:
        status, shortage = "COVERED_BY_TRANSFER", 0
    elif sa + inbound + network + alt_avail >= req:
        status, shortage = "COVERED_BY_ALTERNATE", 0
    else:
        status, shortage = "SHORT_UNCOVERED", req - (sa + inbound + network + alt_avail)

    return {"event_id": event_id, "part_id": part_id, "part_description": part["description"],
            "criticality": part["criticality"], "site": site, "event_start": start,
            "qty_required": req, "status": status, "shortage_qty": shortage,
            "evidence": {"site_available": sa, "inbound_before_need": inbound,
                         "network_available": network, "alternate_available": alt_avail},
            "lead_time_check": _lead_time_check(part["lead_time_days"], start),
            "alternate_part_id": alt_id, "po_detail": po_detail, "network_detail": network_detail}


def _lead_time_check(lead_days, event_start):
    """Date arithmetic done in code, as of the pinned reference date.
    order_by_date = latest order date that still arrives by the event start.
    If that date is already past, ordering today is the only option left and
    its earliest arrival is reference date + lead time."""
    ref = date.fromisoformat(REFERENCE_DATE)
    start = date.fromisoformat(event_start)
    order_by = start - timedelta(days=lead_days)
    return {"lead_time_days": lead_days,
            "reference_date": REFERENCE_DATE,
            "order_by_date": order_by.isoformat(),
            "order_by_already_passed": order_by < ref,
            "earliest_arrival_if_ordered_now": (ref + timedelta(days=lead_days)).isoformat(),
            "days_until_event_start": (start - ref).days}
