# MRO Control Tower — Monitoring Summary

Reference date (pinned): 2026-11-02 · Generated from local logs by `monitoring/summarize_runs.py`.

## Runs

- Total agent runs logged: **25**
- Status mix across all runs: COVERED_BY_ALTERNATE ×3, COVERED_BY_PO ×4, COVERED_BY_TRANSFER ×2, INSUFFICIENT_DATA ×5, OK ×4, SHORT_UNCOVERED ×7
- Tokens: 167,142 input + 19,882 output
- Estimated cost at Haiku list prices ($1/$5 per 1M in/out): **US$0.27**

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

- Runs citing at least one knowledge note: 17/25
- Stage 6 citation retries fired: 1
- Per-run retrieval hits are not logged; `notes_cited` is the audit record of what grounded each recommendation.

## Human gate — planner decisions

- Assessed lines awaiting a decision: 10
- Approved: 0 · Rejected: 0 · Pending: 10
- No decisions recorded yet (the planner screen starts clean).
