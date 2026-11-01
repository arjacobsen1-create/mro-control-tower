# Stage 5 — Evaluation Report

**Run:** 1 November 2026 · **Model:** claude-haiku-4-5 · **Reference date:** 2026-11-02 (pinned)
**Method:** `evals/run_evaluation.py` ran all 10 published ground-truth scenarios
(`data/eval_scenarios.csv`, written and published *before* the agent was built)
live through the agent, exactly as a planner query would run. Scoring is exact
match on status and shortage quantity. Raw agent output: `evals/results_2026-11-01.json`.
Every run is also in `monitoring/runs.jsonl`.

## Headline result

**10/10 — status and shortage quantity exact on every scenario.**

| # | Event/Part | Expected | Agent | Shortage | Notes cited |
|---|---|---|---|---|---|
| S01 | E001/P001 | SHORT_UNCOVERED | SHORT_UNCOVERED | 1 = 1 | N05 |
| S02 | E001/P002 | COVERED_BY_PO | COVERED_BY_PO | 0 = 0 | N06 |
| S03 | E002/P016 | COVERED_BY_TRANSFER | COVERED_BY_TRANSFER | 0 = 0 | N03, N12 |
| S04 | E003/P003 | COVERED_BY_ALTERNATE | COVERED_BY_ALTERNATE | 0 = 0 | N01 |
| S05 | E003/P005 | OK | OK | 0 = 0 | — |
| S06 | E004/P019 | INSUFFICIENT_DATA | INSUFFICIENT_DATA | 0 = 0 | — |
| S07 | E005/P007 | SHORT_UNCOVERED | SHORT_UNCOVERED | 2 = 2 | N05, N03 |
| S08 | E002/P006 | COVERED_BY_PO | COVERED_BY_PO | 0 = 0 | — |
| S09 | E006/P011 | OK | OK | 0 = 0 | — |
| S10 | E005/P020 | SHORT_UNCOVERED | SHORT_UNCOVERED | 1 = 1 | N02 |

**Cost of the full evaluation:** 59,782 input + 7,825 output tokens ≈ **US$0.10**
at Haiku list prices. The whole of Stage 3 + Stage 5 development to date has
used well under US$0.25 of the US$5 credit.

## Why the verdicts are exact (and why that is the design, not luck)

Every quantity, status, and lead-time date in an assessment comes from the
deterministic rule engine (`app/availability.py`) via the `check_availability`
tool. The model cannot state a stock figure the code did not compute — the
same reason the dataset's own validator scores 10/10. The agent's job is
orchestration, grounding, and explanation. This evaluation confirms the
orchestration routes every scenario to the correct rule outcome, including
the three planted traps (late PO, reserved stock, no-record part).

## Narrative review — where the words around the verdicts stand

Verdicts are machine-exact; the prose is the residual risk, and it is not
perfect. Findings, by severity:

1. **S06 — an unverified number in prose (the one real error).** The
   recommendation says a new order would arrive "missing the event by
   227 days." The arrival date it quotes (2027-08-29, code-computed from
   the 300-day lead time) is correct, but 227 matches neither the event
   start (265 days before arrival) nor the event end (256 days). The day
   count was produced in prose, not by code — the same failure class as
   the original Oct/Nov order-by wording issue, in a less critical place.
   The recommended action (physical count, escalate) is correct.
   *Fix direction: any day-count a planner might repeat must come from
   the rule engine, the way lead-time dates now do.*
2. **S06 — citations vary between runs.** This run cited no knowledge
   notes; two earlier runs of the same scenario cited N05 and N11. The
   verdict is unaffected (it is code-derived), but grounding behaviour is
   not yet stable across runs. 6 of 10 runs in this evaluation cited at
   least one note; every run whose recommendation leaned on a policy
   (AOG escalation, transfer procedure, alternate approval) cited the
   correct one — except S06.
3. **S07 — one muddled sentence.** Recommendation step 2 asks for a
   physical count of a partially received PO "to expedite receipt" — a
   count does not expedite anything. The underlying evidence (1 unit on a
   partially received PO arriving after the event) and the other steps
   are correct.
4. **S01 — accurate but framed on the less useful date.** "PO arrives
   after event end (2026-11-27)" is true; the decision-relevant fact is
   that it arrives after the event *start* (2026-11-16), which the
   summary's other figures make clear. No action needed.

## Conclusion

The architecture's central claim holds under test: separate the arithmetic
from the language model and the decisions become exact and auditable, at
trivial cost. The remaining work is prose discipline — extending the same
"code computes it or it doesn't get said" rule to the day-counts inside
recommendations, and stabilising citation behaviour. Both are Stage 6
write-up items, recorded here rather than smoothed over.
