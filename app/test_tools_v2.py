#!/usr/bin/env python3
"""
Stage V2-4 tests — the four new agent tools (no API key needed).

For every one of the 20 V2 scenarios, the fields the agent is scored on
must be producible EXACTLY from tool outputs alone — that is the dry
inspection the stage gate asks for: there is no path by which the agent
can state an allocated status, tier or day-count that a tool did not
return, and the tools demonstrably return all of them.

Also proves the tools are read-only: the database and every data CSV
are hashed before and after a full sweep of tool calls.

Run:  python3 app/test_tools_v2.py
"""
import csv, hashlib, json, os, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "ingest"))
from tools import run_tool  # noqa: E402
from config import DB_PATH  # noqa: E402

fails = 0


def check(label, ok, detail=""):
    global fails
    fails += (not ok)
    print(f"{'PASS' if ok else 'FAIL'}  {label}" + (f"  {detail}" if detail and not ok else ""))


def digest(path):
    with open(path, "rb") as f:
        return hashlib.md5(f.read()).hexdigest()


data_files = [os.path.join(ROOT, "data", n) for n in sorted(os.listdir(os.path.join(ROOT, "data")))
              if n.endswith(".csv")] + [DB_PATH]
before = {p: digest(p) for p in data_files}

with open(os.path.join(ROOT, "data", "eval_scenarios_v2.csv")) as f:
    scenarios = list(csv.DictReader(f))

for s in scenarios:
    e, p = s["event_id"], s["part_id"]
    av = run_tool("check_availability", {"event_id": e, "part_id": p})
    al = run_tool("check_allocated_availability", {"event_id": e, "part_id": p})
    sl = run_tool("check_slippage_risk", {"event_id": e, "part_id": p})
    wl = run_tool("check_watchlist", {"event_id": e, "part_id": p})
    hz = run_tool("get_horizon", {"event_id": e, "part_id": p})
    bad = []
    if str(av["status"]) != s["expected_status"] or av["shortage_qty"] != int(s["expected_shortage_qty"]):
        bad.append("v1 status/shortage")
    if al["allocated_status"] != s["expected_allocated_status"] or \
            al["allocated_shortage_qty"] != int(s["expected_allocated_shortage_qty"]):
        bad.append("allocated status/shortage")
    if al["contention"] != s["expected_contention"]:
        bad.append("contention")
    if sl["slippage_tier"] != s["expected_slippage_tier"]:
        bad.append("slippage tier")
    if wl["watchlist_tier"] != s["expected_watchlist_tier"]:
        bad.append("watchlist tier")
    if hz["procurement"]["action"] != s["expected_procurement_action"]:
        bad.append("procurement action")
    if hz["notification"]["eligible"] != (s["expected_notify_eligible"] == "YES"):
        bad.append("notify eligibility")
    if s["expected_checkpoint_date"] and hz["notification"]["checkpoint_date"] != s["expected_checkpoint_date"]:
        bad.append("checkpoint date")
    if s["expected_feasible_recovery"]:
        feas = hz["recovery"]["feasible"]
        if ("YES" if feas else "NO") != s["expected_feasible_recovery"]:
            bad.append("feasible recovery")
    check(f"{s['scenario_id']} {e}/{p} all scored fields from tools", not bad, ", ".join(bad))

# full-watchlist tool shape
full = run_tool("check_watchlist", {})
check("check_watchlist() counts", full["counts"]["tier_a"] == 2 and full["counts"]["tier_b"] >= 13,
      json.dumps(full["counts"]))

after = {p: digest(p) for p in data_files}
check("tools are read-only (data files untouched)", before == after)

print(f"\n{'ALL PASS' if fails == 0 else f'{fails} FAILURES'} — V2 tool-layer tests")
sys.exit(1 if fails else 0)
