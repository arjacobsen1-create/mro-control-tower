# MRO Control Tower — Monitoring Summary

Reference date (pinned): 2026-11-02 · Generated from local logs by `monitoring/summarize_runs.py`.

## Runs

- Total agent runs logged: **54**
- Status mix across all runs: COVERED_BY_ALTERNATE ×5, COVERED_BY_PO ×11, COVERED_BY_TRANSFER ×6, INSUFFICIENT_DATA ×6, OK ×14, SHORT_UNCOVERED ×12
- Tokens: 714,904 input + 62,212 output
- Estimated cost at Haiku list prices ($1/$5 per 1M in/out): **US$1.03**

## Evaluation scenarios — latest run vs ground truth

| Scenario | Line | Expected status / shortage | Latest agent status / shortage | Result |
|---|---|---|---|---|
| S01 | E001/P001 | SHORT_UNCOVERED / 1 | SHORT_UNCOVERED / 1 | PASS |
| S02 | E001/P002 | COVERED_BY_PO / 0 | COVERED_BY_PO / 0 | PASS |
| S03 | E002/P016 | COVERED_BY_TRANSFER / 0 | COVERED_BY_TRANSFER / 0 | PASS |
| S04 | E003/P003 | COVERED_BY_ALTERNATE / 0 | COVERED_BY_ALTERNATE / 0 | PASS |
| S05 | E003/P005 | OK / 0 | OK / 0 | PASS |
| S06 | E004/P019 | INSUFFICIENT_DATA / 0 | INSUFFICIENT_DATA / 0 | PASS |
| S07 | E005/P007 | SHORT_UNCOVERED / 2 | SHORT_UNCOVERED / 2 | PASS |
| S08 | E002/P006 | COVERED_BY_PO / 0 | COVERED_BY_PO / 0 | PASS |
| S09 | E006/P011 | OK / 0 | OK / 0 | PASS |
| S10 | E005/P020 | SHORT_UNCOVERED / 1 | SHORT_UNCOVERED / 1 | PASS |

Latest-run score: **10/10**

## Grounding behaviour (recorded proxy)

- Runs citing at least one knowledge note: 38/54
- Stage 6 citation retries fired: 7
- Per-run retrieval hits are not logged; `notes_cited` is the audit record of what grounded each recommendation.

## Human gate — planner decisions

- Assessed lines: 10
- Decided: 0 · Escalated: 0 · Pending: 10
- No decisions recorded yet (the planner screen starts clean).

## V2 — cross-event, slippage, watchlist, horizon (Stage V2-5/6)

- V2 evaluation runs logged: 28 (the new-scenario runs that logged + 10 V1 regression; two new-scenario runs failed before logging)
- Evaluation pass of record: **18/20** new scenarios, **10/10** V1 regression (`evals/results_v2_2026-11-06.json`). Two scenarios (R01, X02a) failed as *run errors* and logged nothing — root cause identified and fixed post-pass (validation retry); see the evaluation report addendum. The rows below show the latest logged run per scenario, so those two read 'no run logged'.
- Validation retries fired (all runs): 0

| Scenario | Line | Expected allocated / slippage / watchlist | Latest agent | Result |
|---|---|---|---|---|
| C01 | E003/P001 | SHORT_UNCOVERED / NONE / NONE | SHORT_UNCOVERED / NONE / NONE | PASS |
| C02 | E006/P016 | SHORT_UNCOVERED / NONE / NO_ORDERING_FALLBACK | SHORT_UNCOVERED / NONE / NO_ORDERING_FALLBACK | PASS |
| C03 | E006/P011 | SHORT_UNCOVERED / NONE / ORDER_BY_CLOSING | SHORT_UNCOVERED / NONE / ORDER_BY_CLOSING | PASS |
| C04 | E006/P006 | SHORT_UNCOVERED / NONE / NONE | SHORT_UNCOVERED / NONE / NONE | PASS |
| C05 | E005/P005 | COVERED_BY_TRANSFER / NONE / NONE | COVERED_BY_TRANSFER / NONE / NONE | PASS |
| C06 | E002/P016 | COVERED_BY_TRANSFER / NONE / NO_ORDERING_FALLBACK | COVERED_BY_TRANSFER / NONE / NO_ORDERING_FALLBACK | PASS |
| P01 | E006/P011 | SHORT_UNCOVERED / NONE / ORDER_BY_CLOSING | SHORT_UNCOVERED / NONE / ORDER_BY_CLOSING | PASS |
| R01 | E001/P002 | COVERED_BY_PO / SLIPPAGE_HIGH / NO_ORDERING_FALLBACK | — | no run logged |
| R02 | E002/P006 | COVERED_BY_PO / SLIPPAGE_HIGH / NO_ORDERING_FALLBACK | COVERED_BY_PO / SLIPPAGE_HIGH / NO_ORDERING_FALLBACK | PASS |
| R03 | E002/P015 | COVERED_BY_PO / SLIPPAGE_WATCH / NO_ORDERING_FALLBACK | COVERED_BY_PO / SLIPPAGE_WATCH / NO_ORDERING_FALLBACK | PASS |
| R04 | E005/P002 | COVERED_BY_TRANSFER / NONE / NO_ORDERING_FALLBACK | COVERED_BY_TRANSFER / NONE / NO_ORDERING_FALLBACK | PASS |
| R05 | E004/P021 | OK / NONE / NONE | OK / NONE / NONE | PASS |
| W01 | E004/P011 | COVERED_BY_TRANSFER / NONE / ORDER_BY_CLOSING | COVERED_BY_TRANSFER / NONE / ORDER_BY_CLOSING | PASS |
| W02 | E006/P011 | SHORT_UNCOVERED / NONE / ORDER_BY_CLOSING | SHORT_UNCOVERED / NONE / ORDER_BY_CLOSING | PASS |
| W03 | E001/P005 | OK / NONE / NONE | OK / NONE / NONE | PASS |
| W04 | E001/P001 | SHORT_UNCOVERED / NONE / NO_ORDERING_FALLBACK | SHORT_UNCOVERED / NONE / NO_ORDERING_FALLBACK | PASS |
| W05 | E003/P003 | COVERED_BY_ALTERNATE / NONE / NO_ORDERING_FALLBACK | COVERED_BY_ALTERNATE / NONE / NO_ORDERING_FALLBACK | PASS |
| X01 | E001/P001 | SHORT_UNCOVERED / NONE / NO_ORDERING_FALLBACK | SHORT_UNCOVERED / NONE / NO_ORDERING_FALLBACK | PASS |
| X02a | E001/P002 | COVERED_BY_PO / SLIPPAGE_HIGH / NO_ORDERING_FALLBACK | — | no run logged |
| X02b | E002/P015 | COVERED_BY_PO / SLIPPAGE_WATCH / NO_ORDERING_FALLBACK | COVERED_BY_PO / SLIPPAGE_WATCH / NO_ORDERING_FALLBACK | PASS |

Latest-logged-run check: **18/20** (differs from the pass of record only by the two unlogged run failures)

## V2 layer — engine counts (current dataset, code-computed)

- Contended parts: 10 (15 incl. forward annex)
- Lines changed under allocation: 6, of which flipped to short: 4
- Slippage: 2 HIGH · 1 WATCH (WATCH_MARGIN_DAYS = 21)
- Watchlist: 2 Tier A (act now) · 13 Tier B (no ordering fallback)

## Human gate V2 — planner decisions

- Assessed lines: 15
- Decided: 0 · Escalated: 0 · Pending: 15
- No V2 decisions recorded yet (the V2 planner screen starts clean).
