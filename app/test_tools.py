#!/usr/bin/env python3
"""
Tool-layer tests (no API key needed): the availability engine behind
check_availability must reproduce all 10 ground-truth scenarios, and the
event/part lookups must return sane data.
Run:  python3 app/test_tools.py
"""
import os, sqlite3, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "app"))
sys.path.insert(0, os.path.join(ROOT, "ingest"))
from config import DB_PATH  # noqa: E402
import availability  # noqa: E402

con = sqlite3.connect(DB_PATH); con.row_factory = sqlite3.Row
evals = con.execute("SELECT * FROM eval_scenarios ORDER BY scenario_id").fetchall(); con.close()

fails = 0
for e in evals:
    r = availability.check_availability(e["event_id"], e["part_id"])
    ok = r["status"] == e["expected_status"] and r["shortage_qty"] == e["expected_shortage_qty"]
    fails += (not ok)
    print(f"{'PASS' if ok else 'FAIL'}  {e['scenario_id']} {e['event_id']}/{e['part_id']}: "
          f"engine={r['status']}/{r['shortage_qty']} expected={e['expected_status']}/{e['expected_shortage_qty']}")

ev = availability.get_event("E001")
ok = ev and ev["site"] == "YUL-H1" and ev["planned_start"] == "2026-11-16"
print(f"{'PASS' if ok else 'FAIL'}  get_event(E001)"); fails += (not ok)
lines = availability.get_demand("E001")
ok = len(lines) == 6
print(f"{'PASS' if ok else 'FAIL'}  get_demand(E001) -> {len(lines)} lines"); fails += (not ok)
p = availability.get_part("P003")
ok = p and p["alternate_part_id"] == "P023"
print(f"{'PASS' if ok else 'FAIL'}  get_part(P003) alternate = P023"); fails += (not ok)

print(f"\n{len(evals)+3-fails}/{len(evals)+3} tool-layer tests passed.")
sys.exit(1 if fails else 0)
