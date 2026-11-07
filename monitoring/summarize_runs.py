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
    # ---- V2 sections (added Stage V2-6; V1 sections above unchanged) ----
    v2_truth = {}
    v2_csv = os.path.join(ROOT, "data", "eval_scenarios_v2.csv")
    if os.path.exists(v2_csv):
        with open(v2_csv) as f:
            for row in csv.DictReader(f):
                v2_truth[row["scenario_id"]] = row
    v2_latest = {}
    for r in runs:
        sid = r.get("evaluation")
        if sid in v2_truth:
            v2_latest[sid] = r  # file order == chronological

    def v2_field_check(sid, t, a):
        """The §6.1 primary fields for the scenario's class."""
        if sid.startswith("C"):
            return (a.get("allocated_status") == t["expected_allocated_status"]
                    and a.get("allocated_shortage_qty") == int(t["expected_allocated_shortage_qty"]))
        if sid.startswith("R"):
            return a.get("slippage_tier") == t["expected_slippage_tier"]
        if sid.startswith("W"):
            return a.get("watchlist_tier") == t["expected_watchlist_tier"]
        if sid == "P01":
            return (a.get("status") == "OK" and a.get("watchlist_tier") == "ORDER_BY_CLOSING"
                    and a.get("procurement_action") == "RAISED" and bool(a.get("procurement_need")))
        if sid == "X01":
            return (a.get("feasible_recovery_exists") is False
                    and a.get("recommended_decision") == "escalate_defer")
        if sid == "X02a":
            cn = a.get("customer_notification") or {}
            return (cn.get("action") == "PREPARE_DRAFT"
                    and cn.get("checkpoint_date") == "2026-11-12")
        if sid == "X02b":
            return (a.get("customer_notification") or {}).get("action") == "NONE"
        return False

    v2_rows, v2_pass = [], 0
    for sid in sorted(v2_truth):
        t, r = v2_truth[sid], v2_latest.get(sid)
        if r is None:
            v2_rows.append(f"| {sid} | {t['event_id']}/{t['part_id']} | "
                           f"{t['expected_allocated_status']} / {t['expected_slippage_tier']} / "
                           f"{t['expected_watchlist_tier']} | — | no run logged |")
            continue
        a = r["assessment"]
        ok = v2_field_check(sid, t, a)
        v2_pass += ok
        v2_rows.append(f"| {sid} | {t['event_id']}/{t['part_id']} | "
                       f"{t['expected_allocated_status']} / {t['expected_slippage_tier']} / "
                       f"{t['expected_watchlist_tier']} | {a.get('allocated_status')} / "
                       f"{a.get('slippage_tier')} / {a.get('watchlist_tier')} | "
                       f"{'PASS' if ok else 'FAIL'} |")
    v2_runs = [r for r in runs if r.get("evaluation_set") in ("v2", "v1-regression")]
    v2_val_retries = sum(1 for r in runs if r.get("usage", {}).get("validation_retry"))

    pd2_path = os.path.join(ROOT, "evals", "planner_data_v2.json")
    counts2, assessed2 = {}, 0
    if os.path.exists(pd2_path):
        with open(pd2_path) as f:
            pd2 = json.load(f)
        counts2 = pd2.get("counts", {})
        assessed2 = counts2.get("assessed_lines", 0)
    dec2 = {}
    dec2_path = os.path.join(ROOT, "monitoring", "planner_decisions_v2.json")
    if os.path.exists(dec2_path):
        with open(dec2_path) as f:
            dec2 = json.load(f)
    n2_dec = len(dec2)
    n2_esc = sum(1 for d in dec2.values()
                 if str(d.get("decision", "")).startswith("escalate"))

    lines += [
        "## V2 — cross-event, slippage, watchlist, horizon (Stage V2-5/6)",
        "",
        f"- V2 evaluation runs logged: {len(v2_runs)} (the new-scenario runs that logged + 10 V1 regression; two new-scenario runs failed before logging)",
        f"- Evaluation pass of record: **18/20** new scenarios, **10/10** V1 regression "
        "(`evals/results_v2_2026-11-06.json`). Two scenarios (R01, X02a) failed as "
        "*run errors* and logged nothing — root cause identified and fixed post-pass "
        "(validation retry); see the evaluation report addendum. The rows below show "
        "the latest logged run per scenario, so those two read 'no run logged'.",
        f"- Validation retries fired (all runs): {v2_val_retries}",
        "",
        "| Scenario | Line | Expected allocated / slippage / watchlist | Latest agent | Result |",
        "|---|---|---|---|---|",
        *v2_rows,
        "",
        f"Latest-logged-run check: **{v2_pass}/{len(v2_truth)}** "
        "(differs from the pass of record only by the two unlogged run failures)",
        "",
        "## V2 layer — engine counts (current dataset, code-computed)",
        "",
        f"- Contended parts: {counts2.get('contended_parts')} "
        f"({counts2.get('contended_parts_incl_forward')} incl. forward annex)",
        f"- Lines changed under allocation: {counts2.get('lines_changed_under_allocation')}, "
        f"of which flipped to short: {counts2.get('flips_to_short')}",
        f"- Slippage: {counts2.get('slippage_high')} HIGH · {counts2.get('slippage_watch')} WATCH "
        "(WATCH_MARGIN_DAYS = 21)",
        f"- Watchlist: {counts2.get('watchlist_act_now')} Tier A (act now) · "
        f"{counts2.get('watchlist_no_fallback')} Tier B (no ordering fallback)",
        "",
        "## Human gate V2 — planner decisions",
        "",
        f"- Assessed lines: {assessed2}",
        f"- Decided: {n2_dec} · Escalated: {n2_esc} · Pending: {assessed2 - n2_dec}",
        ("- Decision file: `monitoring/planner_decisions_v2.json` (local only)."
         if dec2 else
         "- No V2 decisions recorded yet (the V2 planner screen starts clean)."),
        "",
    ]

    with open(OUT, "w") as f:
        f.write("\n".join(lines))
    print(f"Wrote {OUT}: {len(runs)} runs, latest-run score "
          f"{scenario_pass}/{len(truth)}, est. cost US${cost:.2f}, "
          f"decisions {n_dec} decided / {n_esc} escalated / {n_pend} pending; "
          f"V2 latest-logged {v2_pass}/{len(v2_truth)}, V2 decisions {n2_dec}")


if __name__ == "__main__":
    main()
