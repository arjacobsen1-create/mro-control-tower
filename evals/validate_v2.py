#!/usr/bin/env python3
"""
Stage V2-0 — pure-code validator for the V2 ground truth.

Recomputes every expected value in data/eval_scenarios_v2.csv from the raw
tables (data/*.csv), implementing spec docs/v2-spec.md §§3-5 directly and
independently of the app/ rule-engine modules (the same discipline as
validate_dataset.py for V1: ground truth is proved by a recomputation that
does not share code with the engine it will later judge).

Checks, beyond the 20 scenarios themselves:
  - spec §2.1  V1 verdict mix and contention counts (original 33 lines)
  - spec §3.3  the six-line worked allocation table, exactly
  - spec §4.2  slippage tiers across the six PO-counted lines (2 HIGH / 1 WATCH)
  - spec §5.2  watchlist split (Tier A 2 / Tier B 13 / excluded-with-passed 18)

Pinned reference date: 2026-11-02. Decided constants: WATCH_MARGIN_DAYS = 21
(D2), WATCHLIST_HORIZON_DAYS = 21 (§5.2), allocation chronological (D1),
partial allocation retained (§3.2).

Run:  python3 evals/validate_v2.py
"""
import csv, os, sys
from datetime import date, timedelta

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
D = os.path.join(ROOT, "data")
REF = date(2026, 11, 2)
SITES = ["YUL-H1", "YYZ-H2", "YYC-H3"]
WATCH_MARGIN_DAYS = 21
WATCHLIST_HORIZON_DAYS = 21
LONG_LEAD_DAYS = 180


def load(name):
    with open(os.path.join(D, name)) as f:
        return list(csv.DictReader(f))


PARTS = {r["part_id"]: r for r in load("parts.csv")}
INV = {(r["part_id"], r["site"]): r for r in load("inventory.csv")}
POS = load("purchase_orders.csv")
EVENTS = {r["event_id"]: r for r in load("maintenance_schedule.csv")}
DEMAND = load("demand.csv")
REQ = {(r["event_id"], r["part_id"]): int(r["qty_required"]) for r in DEMAND}
ORIG_EVENTS = ["E001", "E002", "E003", "E004", "E005", "E006"]


def d(s):
    return date.fromisoformat(s)


def add_months(dt, n):
    m = dt.month - 1 + n
    y, m = dt.year + m // 12, m % 12 + 1
    day = min(dt.day, [31, 29 if y % 4 == 0 and (y % 100 != 0 or y % 400 == 0) else 28,
                       31, 30, 31, 30, 31, 31, 30, 31, 30, 31][m - 1])
    return date(y, m, day)


def site_avail(pid, site):
    r = INV.get((pid, site))
    return None if r is None else int(r["qty_on_hand"]) - int(r["qty_reserved"])


def pos_for(pid):
    return [p for p in POS if p["part_id"] == pid]


def counted(po, site, start):
    return (po["status"] in ("open", "partially_received")
            and po["delivery_site"] == site and po["expected_date"] <= start
            and int(po["qty_ordered"]) - int(po["qty_received"]) > 0)


# ---------------------------------------------------------------- V1 rule
def v1_classify(eid, pid, exclude_po=None):
    ev = EVENTS[eid]
    site, start, req = ev["site"], ev["planned_start"], REQ[(eid, pid)]
    sa = site_avail(pid, site)
    po_rows = pos_for(pid)
    if sa is None and not po_rows:
        return "INSUFFICIENT_DATA", 0
    sa = sa or 0
    inbound = sum(int(p["qty_ordered"]) - int(p["qty_received"]) for p in po_rows
                  if counted(p, site, start) and p["po_id"] != exclude_po)
    network = sum(site_avail(pid, s) or 0 for s in SITES if s != site)
    alt_id = PARTS[pid]["alternate_part_id"]
    alt = (site_avail(alt_id, site) or 0) if alt_id else 0
    if sa >= req:
        return "OK", 0
    if sa + inbound >= req:
        return "COVERED_BY_PO", 0
    if sa + inbound + network >= req:
        return "COVERED_BY_TRANSFER", 0
    if sa + inbound + network + alt >= req:
        return "COVERED_BY_ALTERNATE", 0
    return "SHORT_UNCOVERED", req - (sa + inbound + network + alt)


def insufficient(eid, pid):
    return site_avail(pid, EVENTS[eid]["site"]) is None and not pos_for(pid)


# ---------------------------------------------------------------- §3 allocation
def _cascade(eid, pid, stock, po_bal):
    """One line against the given pools. Returns (status, shortage, draws).
    draws = {'site': q, 'po': {po_id: q}, 'network': {site: q}, 'alt': q}."""
    ev = EVENTS[eid]
    site, start, req = ev["site"], ev["planned_start"], REQ[(eid, pid)]
    need = req
    draws = {"site": 0, "po": {}, "network": {}, "alt": 0}
    q = min(need, stock.get((pid, site), 0))
    draws["site"] = q
    need -= q
    for po in sorted(pos_for(pid), key=lambda p: (p["expected_date"], p["po_id"])):
        if need <= 0:
            break
        if counted(po, site, start) and po_bal.get(po["po_id"], 0) > 0:
            q = min(need, po_bal[po["po_id"]])
            if q:
                draws["po"][po["po_id"]] = q
                need -= q
    for s in SITES:
        if s == site or need <= 0:
            continue
        q = min(need, stock.get((pid, s), 0))
        if q:
            draws["network"][s] = q
            need -= q
    alt_id = PARTS[pid]["alternate_part_id"]
    if alt_id and need > 0:
        q = min(need, stock.get((alt_id, site), 0))
        draws["alt"] = q
        need -= q
    site_q = draws["site"]
    po_q = sum(draws["po"].values())
    net_q = sum(draws["network"].values())
    if site_q >= req:
        status = "OK"
    elif site_q + po_q >= req:
        status = "COVERED_BY_PO"
    elif site_q + po_q + net_q >= req:
        status = "COVERED_BY_TRANSFER"
    elif site_q + po_q + net_q + draws["alt"] >= req:
        status = "COVERED_BY_ALTERNATE"
    else:
        status = "SHORT_UNCOVERED"
    return status, need if status == "SHORT_UNCOVERED" else 0, draws


def _fresh_pools():
    stock = {(pid, s): (site_avail(pid, s) or 0) for pid in PARTS for s in SITES}
    po_bal = {p["po_id"]: int(p["qty_ordered"]) - int(p["qty_received"])
              for p in POS if p["status"] in ("open", "partially_received")}
    return stock, po_bal


def allocate(exclude_po=None):
    """Chronological allocation over every demand line, per part.
    Returns {(eid, pid): dict(status, shortage, draws, alone_status,
    alone_draws)}. Partial allocation retained (§3.2)."""
    out = {}
    parts_lines = {}
    for (eid, pid) in REQ:
        parts_lines.setdefault(pid, []).append(eid)
    for pid, eids in parts_lines.items():
        ordered = sorted(eids, key=lambda e: (EVENTS[e]["planned_start"], e))
        stock, po_bal = _fresh_pools()
        if exclude_po:
            po_bal[exclude_po] = 0
        for eid in ordered:
            site = EVENTS[eid]["site"]
            if insufficient(eid, pid):
                out[(eid, pid)] = {"status": "INSUFFICIENT_DATA", "shortage": 0,
                                   "draws": {"site": 0, "po": {}, "network": {}, "alt": 0},
                                   "alone_status": "INSUFFICIENT_DATA",
                                   "alone_draws": {"site": 0, "po": {}, "network": {}, "alt": 0}}
                continue
            a_stock, a_po = _fresh_pools()
            if exclude_po:
                a_po[exclude_po] = 0
            a_status, a_short, a_draws = _cascade(eid, pid, a_stock, a_po)
            status, short, draws = _cascade(eid, pid, stock, po_bal)
            # consume
            stock[(pid, site)] -= draws["site"]
            for po_id, q in draws["po"].items():
                po_bal[po_id] -= q
            for s, q in draws["network"].items():
                stock[(pid, s)] -= q
            alt_id = PARTS[pid]["alternate_part_id"]
            if alt_id and draws["alt"]:
                stock[(alt_id, site)] -= draws["alt"]
            out[(eid, pid)] = {"status": status, "shortage": short, "draws": draws,
                               "alone_status": a_status, "alone_draws": a_draws}
    return out


ALLOC = allocate()


def contention(eid, pid):
    v1, _ = v1_classify(eid, pid)
    a = ALLOC[(eid, pid)]
    if v1 not in ("SHORT_UNCOVERED", "INSUFFICIENT_DATA") and a["status"] == "SHORT_UNCOVERED":
        return "CONTENDED_SHORT"
    if a["status"] in ("SHORT_UNCOVERED", "INSUFFICIENT_DATA"):
        return "UNCONTENDED"
    if a["status"] != v1 or a["draws"] != a["alone_draws"]:
        return "CONTENDED_COVERED"
    return "UNCONTENDED"


# ---------------------------------------------------------------- §4 slippage
def counted_pairs():
    pairs = []
    for (eid, pid), req in REQ.items():
        ev = EVENTS[eid]
        for po in pos_for(pid):
            if counted(po, ev["site"], ev["planned_start"]):
                pairs.append((eid, pid, po["po_id"]))
    return pairs


def slippage_tier(eid, pid):
    v1, _ = v1_classify(eid, pid)
    a = ALLOC[(eid, pid)]
    if v1 in ("SHORT_UNCOVERED", "INSUFFICIENT_DATA") or a["status"] in (
            "SHORT_UNCOVERED", "INSUFFICIENT_DATA"):
        return "NONE"  # §4.3 / §4.4: shortage handling takes precedence
    ev = EVENTS[eid]
    start = d(ev["planned_start"])
    tier = "NONE"
    for po in pos_for(pid):
        if not counted(po, ev["site"], ev["planned_start"]):
            continue
        slip = (d(po["expected_date"]) - d(po["promised_date"])).days
        margin = (start - d(po["expected_date"])).days
        alt_alloc = allocate(exclude_po=po["po_id"])
        lb = (alt_alloc[(eid, pid)]["status"], alt_alloc[(eid, pid)]["shortage"]) != \
             (a["status"], a["shortage"])
        if lb and slip > margin:
            return "SLIPPAGE_HIGH"
        if lb and margin <= WATCH_MARGIN_DAYS:
            tier = "SLIPPAGE_WATCH"
    return tier


# ---------------------------------------------------------------- §5.2 watchlist, §5.5 clocks, §5.6
def lead_check(eid, pid):
    ev = EVENTS[eid]
    lead = int(PARTS[pid]["lead_time_days"])
    start = d(ev["planned_start"])
    order_by = start - timedelta(days=lead)
    earliest = REF + timedelta(days=lead)
    return {"lead": lead, "order_by": order_by, "passed": order_by < REF,
            "earliest_vs_start": (earliest - start).days}


def watchlist_tier(eid, pid):
    v1, _ = v1_classify(eid, pid)
    lc = lead_check(eid, pid)
    if not lc["passed"] and (lc["order_by"] - REF).days <= WATCHLIST_HORIZON_DAYS:
        return "ORDER_BY_CLOSING"
    if lc["passed"] and v1 != "OK" and lc["earliest_vs_start"] > 0:
        return "NO_ORDERING_FALLBACK"
    return "NONE"


def clock1(eid, pid):
    lc = lead_check(eid, pid)
    ob = lc["order_by"]
    if ob < REF:
        band = "passed"
    elif ob <= add_months(REF, 3):
        band = "act-now"
    elif ob <= add_months(REF, 6):
        band = "advisory"
    else:
        band = "far"
    ev = EVENTS[eid]
    has_counted_po = any(counted(p, ev["site"], ev["planned_start"]) for p in pos_for(pid))
    return {"band": band, "order_by": ob.isoformat(),
            "escalated": band == "passed" and not has_counted_po}


def clock2(eid, pid):
    lc = lead_check(eid, pid)
    if lc["lead"] < LONG_LEAD_DAYS:
        return {"applicable": False}
    start = d(EVENTS[eid]["planned_start"])
    if start <= add_months(REF, 3):
        band = "<=3mo"
    elif start <= add_months(REF, 6):
        band = "3-6mo"
    else:
        band = ">6mo"
    due = []
    if REF >= add_months(start, -6):
        due.append("6-month")
    if REF >= add_months(start, -3):
        due.append("3-month")
    return {"applicable": True, "band": band, "reviews_due": due}


def procurement_action(eid, pid):
    """§5.6: RAISED iff Clock 1 act-now AND a documented outstanding need."""
    if clock1(eid, pid)["band"] != "act-now":
        return "NONE"
    pool = sum(site_avail(pid, s) or 0 for s in SITES)
    aggregate = sum(r for (e, p), r in REQ.items() if p == pid)
    demanders = {e for (e, p) in REQ if p == pid}
    lc = lead_check(eid, pid)
    start = d(EVENTS[eid]["planned_start"])
    need = (aggregate > pool) or (
        len(demanders) >= 2 and aggregate >= pool
        and lc["lead"] > (start - REF).days)
    return "RAISED" if need else "NONE"


# ---------------------------------------------------------------- §4.6 notification
def material_risk(eid, pid):
    """§5.5 material risk condition (planner exception side)."""
    a = ALLOC[(eid, pid)]
    return (a["status"] in ("SHORT_UNCOVERED", "INSUFFICIENT_DATA")
            or contention(eid, pid) == "CONTENDED_SHORT"
            or slippage_tier(eid, pid) == "SLIPPAGE_HIGH"
            or watchlist_tier(eid, pid) == "NO_ORDERING_FALLBACK")


def notify(eid, pid):
    """§4.6 stage-1 triggers only: SLIPPAGE_HIGH, or SHORT in either view.
    (Tier B / WATCH stay internal — the spec's own X02b example settles
    that the §5.5 material-risk list is the planner-exception side, not
    the customer side.) Returns (eligible, checkpoint_date)."""
    v1, _ = v1_classify(eid, pid)
    a = ALLOC[(eid, pid)]
    if slippage_tier(eid, pid) == "SLIPPAGE_HIGH":
        ev = EVENTS[eid]
        cps = [p["expected_date"] for p in pos_for(pid)
               if counted(p, ev["site"], ev["planned_start"])]
        return "YES", min(cps)
    if v1 == "SHORT_UNCOVERED" or a["status"] == "SHORT_UNCOVERED":
        return "YES", EVENTS[eid]["planned_start"]
    return "NO", ""


# ---------------------------------------------------------------- X01 recovery feasibility
def feasible_recovery(eid, pid):
    ev = EVENTS[eid]
    start = d(ev["planned_start"])
    part = PARTS[pid]
    lead = int(part["lead_time_days"])
    po_dates = [d(p["expected_date"]) for p in pos_for(pid)
                if int(p["qty_ordered"]) - int(p["qty_received"]) > 0]
    expedite = (min(po_dates) <= start) if po_dates else False
    expedite = expedite or (REF + timedelta(days=lead) <= start)
    alt_id = part["alternate_part_id"]
    exchange = bool(alt_id) and sum(site_avail(alt_id, s) or 0 for s in SITES) > 0
    # transfer: stock remaining anywhere after the full allocation
    stock2, po2 = _fresh_pools()
    for (e2, p2) in sorted(REQ, key=lambda k: (EVENTS[k[0]]["planned_start"], k[0], k[1])):
        a = ALLOC[(e2, p2)]
        site2 = EVENTS[e2]["site"]
        stock2[(p2, site2)] -= a["draws"]["site"]
        for s, q in a["draws"]["network"].items():
            stock2[(p2, s)] -= q
        alt2 = PARTS[p2]["alternate_part_id"]
        if alt2 and a["draws"]["alt"]:
            stock2[(alt2, site2)] -= a["draws"]["alt"]
    transfer = sum(stock2.get((pid, s), 0) for s in SITES) >= ALLOC[(eid, pid)]["shortage"] \
        and ALLOC[(eid, pid)]["shortage"] > 0
    resequence = part["criticality"] != "AOG"
    return "YES" if (expedite or exchange or transfer or resequence) else "NO"


def line_state(eid, pid):
    v1, v1short = v1_classify(eid, pid)
    a = ALLOC[(eid, pid)]
    n_el, n_ck = notify(eid, pid)
    return {"status": v1, "shortage": v1short,
            "allocated_status": a["status"], "allocated_shortage": a["shortage"],
            "contention": contention(eid, pid),
            "slippage": slippage_tier(eid, pid),
            "watchlist": watchlist_tier(eid, pid),
            "procurement": procurement_action(eid, pid),
            "notify_eligible": n_el, "checkpoint": n_ck,
            "clock1": clock1(eid, pid), "clock2": clock2(eid, pid)}


# ---------------------------------------------------------------- main
def main():
    fails = []

    def check(label, got, want):
        ok = got == want
        print(f"{'PASS' if ok else 'FAIL'}  {label}: got={got} want={want}")
        if not ok:
            fails.append(label)

    # --- §2.1 global facts (original 33 lines)
    orig = [(e, p) for (e, p) in REQ if e in ORIG_EVENTS]
    mix = {}
    for (e, p) in orig:
        s, _ = v1_classify(e, p)
        mix[s] = mix.get(s, 0) + 1
    check("§2.1 V1 mix", mix, {"OK": 19, "COVERED_BY_PO": 4, "COVERED_BY_TRANSFER": 4,
                               "COVERED_BY_ALTERNATE": 1, "SHORT_UNCOVERED": 3,
                               "INSUFFICIENT_DATA": 2})
    # §2's facts describe the original dataset; after the V2-3B forward
    # annex the same checks are scoped to the original six events (the
    # annex is additive and later — it must not rewrite §2's facts).
    contended_parts = {p for (e, p) in orig
                       if sum(1 for (e2, p2) in orig if p2 == p) >= 2}
    check("§2.1 contended parts", len(contended_parts), 10)
    check("§2.1 lines on contended parts",
          sum(1 for (e, p) in orig if p in contended_parts), 22)
    orig_pairs = [t for t in counted_pairs() if t[0] in ORIG_EVENTS]
    check("§2.2 PO-counted (line, PO) pairs", len(orig_pairs), 6)

    # --- §3.3 worked table
    worked = {("E003", "P001"): ("SHORT_UNCOVERED", 1), ("E006", "P006"): ("SHORT_UNCOVERED", 1),
              ("E006", "P011"): ("SHORT_UNCOVERED", 3), ("E006", "P016"): ("SHORT_UNCOVERED", 3),
              ("E005", "P002"): ("COVERED_BY_TRANSFER", 0), ("E005", "P005"): ("COVERED_BY_TRANSFER", 0)}
    for (e, p), (st, sh) in worked.items():
        a = ALLOC[(e, p)]
        check(f"§3.3 {e}/{p}", (a["status"], a["shortage"]), (st, sh))
    changed = [(e, p) for (e, p) in orig
               if ALLOC[(e, p)]["status"] != v1_classify(e, p)[0]]
    check("§3.3 lines whose allocated status changes", len(changed), 6)
    for (e, p) in orig:  # alone-cascade must reproduce the V1 verdict (§3.2)
        if ALLOC[(e, p)]["alone_status"] != v1_classify(e, p)[0]:
            check(f"§3.2 alone==V1 {e}/{p}", ALLOC[(e, p)]["alone_status"], v1_classify(e, p)[0])

    # --- §4.2 tiers over the counted lines (original dataset)
    tier_by_line = {}
    for (e, p, po) in orig_pairs:
        tier_by_line[(e, p)] = slippage_tier(e, p)
    check("§4.2 HIGH lines", sorted(k for k, v in tier_by_line.items() if v == "SLIPPAGE_HIGH"),
          [("E001", "P002"), ("E002", "P006")])
    check("§4.2 WATCH lines", sorted(k for k, v in tier_by_line.items() if v == "SLIPPAGE_WATCH"),
          [("E002", "P015")])

    # --- §5.2 watchlist split (original 33 lines)
    tiers = [watchlist_tier(e, p) for (e, p) in orig]
    check("§5.2 Tier A count", tiers.count("ORDER_BY_CLOSING"), 2)
    check("§5.2 Tier B count", tiers.count("NO_ORDERING_FALLBACK"), 13)
    check("§5.2 Tier A lines",
          sorted(f"{e}/{p}" for (e, p) in orig if watchlist_tier(e, p) == "ORDER_BY_CLOSING"),
          ["E004/P011", "E006/P011"])
    passed_ok = sum(1 for (e, p) in orig
                    if lead_check(e, p)["passed"] and v1_classify(e, p)[0] == "OK")
    check("§5.2/§5.3 excluded OK-with-passed-order-by", passed_ok, 18)

    # --- the 20 scenarios
    with open(os.path.join(D, "eval_scenarios_v2.csv")) as f:
        scenarios = list(csv.DictReader(f))
    check("scenario count", len(scenarios), 20)
    field_map = {"expected_status": "status", "expected_shortage_qty": "shortage",
                 "expected_allocated_status": "allocated_status",
                 "expected_allocated_shortage_qty": "allocated_shortage",
                 "expected_contention": "contention", "expected_slippage_tier": "slippage",
                 "expected_watchlist_tier": "watchlist",
                 "expected_procurement_action": "procurement",
                 "expected_notify_eligible": "notify_eligible",
                 "expected_checkpoint_date": "checkpoint"}
    npass = 0
    for s in scenarios:
        st = line_state(s["event_id"], s["part_id"])
        bad = []
        for csv_field, key in field_map.items():
            want = s[csv_field]
            if want == "":
                continue
            got = str(st[key])
            if got != want:
                bad.append(f"{csv_field}: got {got} want {want}")
        if s["expected_feasible_recovery"]:
            got = feasible_recovery(s["event_id"], s["part_id"])
            if got != s["expected_feasible_recovery"]:
                bad.append(f"feasible_recovery: got {got} want {s['expected_feasible_recovery']}")
        if s["expected_customer_escalation"]:
            want_esc = s["expected_customer_escalation"]
            got_esc = "PREPARE_DRAFT" if st["notify_eligible"] == "YES" else "NONE"
            if got_esc != want_esc:
                bad.append(f"customer_escalation: got {got_esc} want {want_esc}")
        ok = not bad
        npass += ok
        print(f"{'PASS' if ok else 'FAIL'}  {s['scenario_id']} {s['event_id']}/{s['part_id']}"
              + ("" if ok else "  -> " + "; ".join(bad)))
        if not ok:
            fails.append(s["scenario_id"])
    print(f"\nScenarios: {npass}/20 reproduced by pure-code recomputation.")
    if fails:
        print("FAILED checks:", fails)
        sys.exit(1)
    print("All V2-0 validator checks passed.")


if __name__ == "__main__":
    main()
