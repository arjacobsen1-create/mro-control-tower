#!/usr/bin/env python3
"""
Stage V2-6 — build the static V2 planner page (docs/planner_v2.html)
from the shared template in app/planner_v2_page.py and the data in
evals/planner_data_v2.json. Static mode: data embedded, decisions
kept in the browser's localStorage, the §7 decision model enforced
client-side by the same code the server page uses (the local server
in app/planner_v2.py enforces it server-side). The V1 planner page
is untouched.

Run:  python3 build_planner_page_v2.py
"""
import json, os, sys

ROOT = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(ROOT, "app"))
from planner_v2_page import PAGE_TEMPLATE  # noqa: E402


def main():
    with open(os.path.join(ROOT, "evals", "planner_data_v2.json")) as f:
        data = json.load(f)
    page = (PAGE_TEMPLATE.replace("__MODE__", "static")
            .replace("__DATA__", json.dumps(data)))
    out = os.path.join(ROOT, "docs", "planner_v2.html")
    with open(out, "w") as f:
        f.write(page)
    print(f"Wrote {out} ({len(page)} bytes) — embedded data: "
          f"{len(data['events'])} events, {data['counts']['assessed_lines']} assessed lines, "
          f"{len(data['allocation_ledgers'])} allocation ledgers, "
          f"{len(data['forward_events'])} forward events")


if __name__ == "__main__":
    main()
