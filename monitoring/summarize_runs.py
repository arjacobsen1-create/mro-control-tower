#!/usr/bin/env python3
"""
Stage 6 — monitoring summary.

Reads the local run log and the planner's decision file and writes a
one-page Markdown summary: how many agent runs exist, whether the latest
run of each evaluation scenario still matches ground truth, what the runs
cost, how grounding behaved, and where the human decision gate stands.

    python3 monitoring/summarize_runs.py     # writes monitoring/summary.md

Sources (all local):
  monitoring/runs.jsonl             every agent run (agent.py + evaluations)
  data/eval_scenarios.csv           ground truth the scenarios are scored on
  monitoring/planner_decisions.json planner decisions, if any exist yet
  evals/planner_data.json           the assessed lines awaiting a decision

Cost estimate uses Claude Haiku list prices (US$1 / 1M input tokens,
US$5 / 1M output tokens) — an estimate, clearly labelled as such.
Retrieval is not logged per run; the recorded proxy for grounding
behaviour is each assessment's notes_cited list (plus the Stage 6
citation-retry flag in the usage block).
"""
import csv, json, os
from collections import Counter

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RUNS = os.path.join(ROOT, "monitoring", "runs.jsonl")
DECISIONS = os.path.join(ROOT, "monitoring", "planner_decisions.json")
PLANNER_DATA = os.path.join(ROOT, "evals", "planner_data.json")
SCENARIOS = os.path.join(ROOT, "data", "eval_scenarios.csv")
OUT = os.path.join(ROOT, "monitoring", "summary.md")

PRICE_IN, PRICE_OUT = 1.0, 5.0  # US$ per 1M tokens, claude-haiku-4-5 list


def load_jsonl(path):
    if not os.path.exists(path):
        return []
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def main():
    runs = load_jsonl(RUNS)
    with open(SCENARIOS) as f:
        truth = {r["scenario_id"]: r for r in csv.DictReader(f)}

    tot_in = sum(r.get("usage", {}).get("input_tokens", 0) for r in runs)
    tot_out = sum(r.get("usage", {}).get("output_tokens", 0) for r in runs)
    cost = tot_in / 1e6 * PRICE_IN + tot_out / 1e6 * PRICE_OUT

    # Latest evaluation run per scenario (runs.jsonl is append-only, so the
    # last matching line wins).
    latest = {}
    for r in runs:
        sid = r.get("evaluation")
        if sid in truth:
            latest[sid] = r
    scenario_rows, scenario_pass = [], 0
    for sid in sorted(truth):
        t, r = truth[sid], latest.get(sid)
        if r is None:
            scenario_rows.append(f"| {sid} | {t['event_id']}/{t['part_id']} | "
                                 f"{t['expected_status']} / {t['expected_shortage_qty']} | — | no run logged |")
            continue
        a = r["assessment"]
        ok = (a["status"] == t["expected_status"]
              and a["shortage_qty"] == int(t["expected_shortage_qty"]))
        scenario_pass += ok
        scenario_rows.append(f"| {sid} | {t['event_id']}/{t['part_id']} | "
                             f"{t['expected_status']} / {t['expected_shortage_qty']} | "
                             f"{a['status']} / {a['shortage_qty']} | {'PASS' if ok else 'FAIL'} |")

    statuses = Counter(r["assessment"]["status"] for r in runs)
    cited = sum(1 for r in runs if r["assessment"].get("notes_cited"))
    retries = sum(1 for r in runs if r.get("usage", {}).get("citation_retry"))

    decisions = {}
    if os.path.exists(DECISIONS):
        with open(DECISIONS) as f:
            decisions = json.load(f)
    assessed = 0
    if os.path.exists(PLANNER_DATA):
        with open(PLANNER_DATA) as f:
            pd = json.load(f)
        assessed = sum(1 for e in pd["events"] for l in e["lines"] if l.get("assessed"))
    # Fixed decision model (2026-11-06): counts are Decided / Escalated /
    # Pending. Any recorded decision counts as decided — including legacy
    # 'approved'/'rejected' values from the pre-fix gate. Escalated means
    # the decision value starts with 'escalate'.
    n_dec = len(decisions)
    n_esc = sum(1 for d in decisions.values()
                if str(d.get("decision", "")).startswith("escalate"))
    n_pend = assessed - n_dec

    lines = [
        "# MRO Control Tower — Monitoring Summary",
        "",
        f"Reference date (pinned): 2026-11-02 · Generated from local logs by "
        f"`monitoring/summarize_runs.py`.",
        "",
        "## Runs",
        "",
        f"- Total agent runs logged: **{len(runs)}**",
        f"- Status mix across all runs: "
        + ", ".join(f"{k} ×{v}" for k, v in sorted(statuses.items())),
        f"- Tokens: {tot_in:,} input + {tot_out:,} output",
        f"- Estimated cost at Haiku list prices ($1/$5 per 1M in/out): **US${cost:.2f}**",
        "",
        "## Evaluation scenarios — latest run vs ground truth",
        "",
        "| Scenario | Line | Expected status / shortage | Latest agent status / shortage | Result |",
        "|---|---|---|---|---|",
        *scenario_rows,
        "",
        f"Latest-run score: **{scenario_pass}/{len(truth)}**",
        "",
        "## Grounding behaviour (recorded proxy)",
        "",
        f"- Runs citing at least one knowledge note: {cited}/{len(runs)}",
        f"- Stage 6 citation retries fired: {retries}",
        "- Per-run retrieval hits are not logged; `notes_cited` is the audit "
        "record of what grounded each recommendation.",
        "",
        "## Human gate — planner decisions",
        "",
        f"- Assessed lines: {assessed}",
        f"- Decided: {n_dec} · Escalated: {n_esc} · Pending: {n_pend}",
        ("- Decision file: `monitoring/planner_decisions.json` (local only)."
         if decisions else
         "- No decisions recorded yet (the planner screen starts clean)."),
        "",
    ]
    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {OUT}: {len(runs)} runs, latest-run score "
          f"{scenario_pass}/{len(truth)}, est. cost US${cost:.2f}, "
          f"decisions {n_dec} decided / {n_esc} escalated / {n_pend} pending")


if __name__ == "__main__":
    main()
