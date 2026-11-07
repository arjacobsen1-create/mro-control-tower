#!/usr/bin/env python3
"""
V2 rule-engine layer, spec §5.5/§5.6 — the two-clock horizon model,
plus the §4.6 notification eligibility that rides on it.

Two clocks, both code-computed from dates the rule engine produces,
and never merged into one indicator (§5.5, §1 rule 8):

  Clock 1 — ORDER-BY (procurement warning): driven by order_by_date.
    Bands: passed / act-now (<= 3 months away) / advisory (<= 6 months)
    / far. "Escalated" = passed with no PO placed that counts for the
    line. Tier A (§5.2) is this clock's innermost band, not a separate
    mechanism.
  Clock 2 — EVENT (coverage and customer warning): driven by days to
    event start; applies only to lines dependent on long-lead parts
    (lead_time_days >= 180). At 6 and 3 months before the event the
    tower runs a SCHEDULED coverage review for every long-lead line;
    a review raises an exception / customer advisory ONLY if it finds
    a material risk condition (§5.5): post-allocation SHORT or
    INSUFFICIENT_DATA, CONTENDED_SHORT, SLIPPAGE_HIGH, or counted-PO
    coverage with no ordering fallback (the Tier B condition).

§5.6: an OK verdict does not suppress an independently valid
procurement action — but the action requires a documented outstanding
procurement need, computed here from the data (shared pool with
aggregate demand above the pool, or a pool other events also claim
that cannot be re-ordered inside the window).

§4.6: notification eligibility (stage 1) belongs to SLIPPAGE_HIGH
lines and lines SHORT in either view; the checkpoint date is the
counted PO's expected arrival (slippage) or the event start
(shortage). The system prepares a draft; it never sends.
"""
import os, sys
from datetime import date, timedelta

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingest"))
import availability  # noqa: E402
import allocation  # noqa: E402
import slippage as slippage_mod  # noqa: E402
import watchlist as watchlist_mod  # noqa: E402
from config import DB_PATH, REFERENCE_DATE  # noqa: E402

LONG_LEAD_DAYS = 180
REF = date.fromisoformat(REFERENCE_DATE)


def add_months(dt, n):
    m = dt.month - 1 + n
    y, m = dt.year + m // 12, m % 12 + 1
    mdays = [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
             31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1]
    return date(y, m, min(dt.day, mdays))


def _demand_map(db_path):
    con = availability._con(db_path)
    rows = con.execute("SELECT event_id, part_id, qty_required FROM demand").fetchall()
    ev = {r["event_id"]: dict(r) for r in con.execute("SELECT * FROM maintenance_schedule")}
    con.close()
    return rows, ev


def procurement_need(event_id, part_id, db_path=DB_PATH):
    """§5.6 documented outstanding procurement need, or None.

    Need exists when the pool this line draws on is shared and claimed
    beyond itself (aggregate demand across all events exceeds the total
    physical pool), or when other events also claim the pool and the
    part cannot be re-ordered inside the window (lead time longer than
    the time left to this event). Returns a human-readable statement
    composed from the computed numbers."""
    rows, events = _demand_map(db_path)
    con = availability._con(db_path)
    pool = 0
    for s in availability.SITES:
        v = availability._site_available(con, part_id, s)
        pool += v or 0
    con.close()
    demanders = sorted({r["event_id"] for r in rows if r["part_id"] == part_id},
                       key=lambda e: (events[e]["planned_start"], e))
    aggregate = sum(r["qty_required"] for r in rows if r["part_id"] == part_id)
    part = availability.get_part(part_id, db_path)
    lead = part["lead_time_days"]
    days_to_event = (date.fromisoformat(events[event_id]["planned_start"]) - REF).days
    if aggregate > pool:
        return (f"Pool for {part_id} is shared across {len(demanders)} events "
                f"({', '.join(demanders)}): aggregate demand {aggregate} exceeds the "
                f"total physical pool {pool}; the stock cannot be replenished inside "
                f"the horizon once the order-by date passes.")
    if len(demanders) >= 2 and aggregate >= pool and lead > days_to_event:
        return (f"Pool for {part_id} ({pool} units) is fully claimed by "
                f"{len(demanders)} events ({', '.join(demanders)}), aggregate demand "
                f"{aggregate}; lead time {lead} days exceeds the {days_to_event} days "
                f"to this event, so the position cannot be re-ordered inside the window.")
    return None


def horizon_line(event_id, part_id, db_path=DB_PATH, policy="chronological"):
    """Full horizon state for one demand line: both clocks, the §5.6
    procurement action, material-risk condition and §4.6 eligibility."""
    base = availability.check_availability(event_id, part_id, db_path)
    if "error" in base:
        return base
    alloc = allocation.allocate_all(db_path, policy)
    line = alloc["lines"][(event_id, part_id)]
    slip = slippage_mod.slippage_risk(event_id, part_id, db_path, policy)
    watch = watchlist_mod.watchlist_line(event_id, part_id, db_path)
    lc = base["lead_time_check"]
    order_by = date.fromisoformat(lc["order_by_date"])
    start = date.fromisoformat(base["event_start"])

    # Clock 1 — order-by
    if order_by < REF:
        band1 = "passed"
    elif order_by <= add_months(REF, 3):
        band1 = "act-now"
    elif order_by <= add_months(REF, 6):
        band1 = "advisory"
    else:
        band1 = "far"
    has_counted_po = any(d["counted"] for d in base["po_detail"])
    clock1 = {"band": band1, "order_by_date": lc["order_by_date"],
              "escalated": band1 == "passed" and not has_counted_po}

    # Clock 2 — event (long-lead lines only)
    long_lead = lc["lead_time_days"] >= LONG_LEAD_DAYS
    if not long_lead:
        clock2 = {"applicable": False, "lead_time_days": lc["lead_time_days"]}
    else:
        if start <= add_months(REF, 3):
            band2 = "<=3mo"
        elif start <= add_months(REF, 6):
            band2 = "3-6mo"
        else:
            band2 = ">6mo"
        due = []
        if REF >= add_months(start, -6):
            due.append("6-month")
        if REF >= add_months(start, -3):
            due.append("3-month")
        clock2 = {"applicable": True, "band": band2, "lead_time_days": lc["lead_time_days"],
                  "review_points": {"6-month": add_months(start, -6).isoformat(),
                                    "3-month": add_months(start, -3).isoformat()},
                  "reviews_due": due}

    # Material risk condition (§5.5) — planner exception side
    risk_conditions = []
    if line["allocated_status"] in ("SHORT_UNCOVERED", "INSUFFICIENT_DATA"):
        risk_conditions.append(f"allocated_{line['allocated_status']}")
    if line["contention"] == "CONTENDED_SHORT":
        risk_conditions.append("CONTENDED_SHORT")
    if slip["slippage_tier"] == "SLIPPAGE_HIGH":
        risk_conditions.append("SLIPPAGE_HIGH")
    if watch["watchlist_tier"] == "NO_ORDERING_FALLBACK":
        risk_conditions.append("NO_ORDERING_FALLBACK")

    # §5.6 procurement action (procurement dimension, kept separate)
    need = procurement_need(event_id, part_id, db_path) if band1 == "act-now" else None
    procurement = {"action": "RAISED" if need else "NONE",
                   "documented_need": need}

    # Recovery feasibility (the X01 question): can any lever actually
    # close this line's allocated shortage inside the window? Each lever
    # is a computed fact, not a judgement: expedite — an existing PO with
    # outstanding balance lands by the event start, or a fresh order
    # (reference date + lead time) does; exchange/rotable — an approved
    # alternate exists with stock somewhere; transfer — stock remaining
    # after allocation covers the shortage; re-sequence — the check can
    # be re-ordered around the part (not possible for an AOG part that
    # is itself the subject of the event).
    part = availability.get_part(part_id, db_path)
    shortage = line["allocated_shortage_qty"]
    po_dates = [d for d in base["po_detail"] if d["outstanding"] > 0]
    expedite = any(d["expected_date"] <= base["event_start"] for d in po_dates) or \
        (REF + timedelta(days=lc["lead_time_days"]) <= start)
    alt_id = part["alternate_part_id"]
    exchange = False
    if alt_id:
        con = availability._con(db_path)
        exchange = sum(availability._site_available(con, alt_id, s) or 0
                       for s in availability.SITES) > 0
        con.close()
    remaining_stock = sum(alloc["pools"][part_id]["remaining"]["stock"].values())
    recovery = {"feasible": None,  # set below
                "levers": {"expedite": bool(expedite), "exchange_rotable": bool(exchange),
                           "transfer": bool(shortage > 0 and remaining_stock >= shortage),
                           "re_sequence": part["criticality"] != "AOG"}}
    recovery["feasible"] = any(recovery["levers"].values()) if shortage > 0 else None

    # §4.6 customer notification (customer-impact dimension, kept separate)
    if slip["slippage_tier"] == "SLIPPAGE_HIGH":
        notify = {"eligible": True, "checkpoint_date": slip["checkpoint_date"],
                  "basis": "SLIPPAGE_HIGH"}
    elif base["status"] == "SHORT_UNCOVERED" or line["allocated_status"] == "SHORT_UNCOVERED":
        notify = {"eligible": True, "checkpoint_date": base["event_start"],
                  "basis": "SHORT_UNCOVERED"}
    else:
        notify = {"eligible": False, "checkpoint_date": None, "basis": None}

    return {"event_id": event_id, "part_id": part_id,
            "v1_status": base["status"], "v1_shortage_qty": base["shortage_qty"],
            "allocated_status": line["allocated_status"],
            "allocated_shortage_qty": line["allocated_shortage_qty"],
            "contention": line["contention"],
            "slippage_tier": slip["slippage_tier"],
            "watchlist_tier": watch["watchlist_tier"],
            "clock1": clock1, "clock2": clock2,
            "material_risk": bool(risk_conditions), "risk_conditions": risk_conditions,
            "procurement": procurement, "notification": notify,
            "recovery": recovery}
