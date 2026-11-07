#!/usr/bin/env python3
"""
Stage V2-3 tests — order-by watchlist (spec §5.2).

Checks W01-W05 against the V2-0 ground truth and the exact 2 / 13 / 18
split (Tier A / Tier B / OK lines with passed order-by, excluded §5.3).

Run:  python3 app/test_watchlist.py
"""
import csv, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "ingest"))
import watchlist  # noqa: E402

fails = 0


def check(label, ok, detail=""):
    global fails
    fails += (not ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if detail and not ok else ""))


with open(os.path.join(ROOT, "data", "eval_scenarios_v2.csv")) as f:
    scenarios = {r["scenario_id"]: r for r in csv.DictReader(f)}
for sid in ["W01", "W02", "W03", "W04", "W05"]:
    s = scenarios[sid]
    w = watchlist.watchlist_line(s["event_id"], s["part_id"])
    check(f"{sid} {s['event_id']}/{s['part_id']} tier", w["watchlist_tier"] == s["expected_watchlist_tier"],
          f"got {w['watchlist_tier']} want {s['expected_watchlist_tier']}")

# §5.2's counts describe the original 33-line dataset. Since Stage
# V2-3B the demand table also carries the forward-event annex (E007+),
# whose lines are horizon fixtures (their watchlist state is reported
# by evals/check_horizon.py); the split below is therefore scoped to
# the original six events, exactly as in evals/validate_v2.py.
ORIG = {"E001", "E002", "E003", "E004", "E005", "E006"}
full = watchlist.watchlist()
ta = [w for w in full["tier_a"] if w["event_id"] in ORIG]
tb = [w for w in full["tier_b"] if w["event_id"] in ORIG]
check("§5.2 Tier A count = 2 (original dataset)", len(ta) == 2, f"got {len(ta)}")
check("§5.2 Tier B count = 13 (original dataset)", len(tb) == 13, f"got {len(tb)}")
check("§5.2 watchlist total = 15 (original dataset)", len(ta) + len(tb) == 15,
      f"got {len(ta) + len(tb)}")
import csv as _csv
with open(os.path.join(ROOT, "data", "demand.csv")) as f:
    _dem = list(_csv.DictReader(f))
excl = sum(1 for r in _dem if r["event_id"] in ORIG
           and (lambda w: w["order_by_already_passed"] and w["v1_status"] == "OK"
                and w["watchlist_tier"] == "NONE")(
               watchlist.watchlist_line(r["event_id"], r["part_id"])))
check("§5.3 excluded OK-with-passed-order-by = 18 (original dataset)", excl == 18, f"got {excl}")
check("§5.2 Tier A lines are E004/P011 + E006/P011",
      sorted(f"{w['event_id']}/{w['part_id']}" for w in ta) == ["E004/P011", "E006/P011"],
      f"got {[w['event_id'] + '/' + w['part_id'] for w in ta]}")
w = watchlist.watchlist_line("E004", "P011")
check("W01 order-by 2026-11-07, 5 days out", w["order_by_date"] == "2026-11-07" and w["days_to_order_by"] == 5,
      f"got {w['order_by_date']} / {w['days_to_order_by']}")

print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAILURES'} — watchlist tests")
sys.exit(1 if fails else 0)
