#!/usr/bin/env python3
"""
V2 rule-engine layer, spec §5 — order-by-date-passed watchlist.

The watchlist surfaces the lines where the answer to "could we still
order our way out?" changed, or is about to change (§5.1) — not every
line whose order-by date is in the past (that is 31 of 33 lines, §2.3).
Two tiers, both code-computed (§5.2, Decision D4):

  - Tier A ORDER_BY_CLOSING: order-by date not yet passed and within
    WATCHLIST_HORIZON_DAYS of the reference date — "order soon" is
    still a real, losable option.
  - Tier B NO_ORDERING_FALLBACK: order-by date passed, the line's V1
    status is not OK (its coverage is a plan, not a fact), and the
    earliest arrival if ordered now falls after the event start —
    if the plan fails there is no ordering fallback inside the window.

A fully covered (OK) line with a passed order-by date is excluded on
purpose (§5.3): the stock is on the shelf; the passed date is a
replenishment-planning fact, not an exception. The watchlist is a view,
not a second gate (§5.4) — Tier A adds the order decision (§7); Tier B
adds context only.
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "ingest"))
import availability  # noqa: E402
from config import DB_PATH, REFERENCE_DATE  # noqa: E402
from datetime import date  # noqa: E402

WATCHLIST_HORIZON_DAYS = 21  # §5.2 named constant


def watchlist_line(event_id, part_id, db_path=DB_PATH):
    """Watchlist tier for one demand line, with the computed dates."""
    base = availability.check_availability(event_id, part_id, db_path)
    if "error" in base:
        return base
    lc = base["lead_time_check"]
    ref = date.fromisoformat(REFERENCE_DATE)
    order_by = date.fromisoformat(lc["order_by_date"])
    days_to_order_by = (order_by - ref).days
    if not lc["order_by_already_passed"] and days_to_order_by <= WATCHLIST_HORIZON_DAYS:
        tier = "ORDER_BY_CLOSING"
    elif (lc["order_by_already_passed"] and base["status"] != "OK"
          and lc["earliest_arrival_days_vs_event_start"] > 0):
        tier = "NO_ORDERING_FALLBACK"
    else:
        tier = "NONE"
    return {"event_id": event_id, "part_id": part_id, "v1_status": base["status"],
            "watchlist_tier": tier, "order_by_date": lc["order_by_date"],
            "order_by_already_passed": lc["order_by_already_passed"],
            "days_to_order_by": days_to_order_by,
            "lead_time_days": lc["lead_time_days"],
            "earliest_arrival_if_ordered_now": lc["earliest_arrival_if_ordered_now"],
            "earliest_arrival_days_vs_event_start": lc["earliest_arrival_days_vs_event_start"]}


def watchlist(db_path=DB_PATH):
    """The full watchlist over every demand line, split by tier (§5.2)."""
    con = availability._con(db_path)
    rows = con.execute("SELECT event_id, part_id FROM demand ORDER BY event_id, part_id").fetchall()
    con.close()
    tier_a, tier_b, excluded_passed_ok = [], [], 0
    for r in rows:
        w = watchlist_line(r["event_id"], r["part_id"], db_path)
        if w["watchlist_tier"] == "ORDER_BY_CLOSING":
            tier_a.append(w)
        elif w["watchlist_tier"] == "NO_ORDERING_FALLBACK":
            tier_b.append(w)
        elif w["order_by_already_passed"] and w["v1_status"] == "OK":
            excluded_passed_ok += 1
    return {"tier_a": tier_a, "tier_b": tier_b,
            "counts": {"tier_a": len(tier_a), "tier_b": len(tier_b),
                       "total": len(tier_a) + len(tier_b),
                       "excluded_ok_with_passed_order_by": excluded_passed_ok},
            "watchlist_horizon_days": WATCHLIST_HORIZON_DAYS}
