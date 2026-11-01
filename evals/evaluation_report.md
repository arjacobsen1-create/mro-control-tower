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

---

## Stage 6 addendum — re-run after the two fixes (1 November 2026)

Both fixes from the review above were implemented and the full evaluation
was re-run fresh, live, same method. Raw output:
`evals/results_stage6_2026-11-01.json`.

**Score: 10/10 again** — status and shortage exact on every scenario.
Usage 75,960 input + 8,276 output tokens ≈ **US$0.12**.

**Fix 1 — day-counts computed by code: verified.** `app/availability.py`
now returns day differences alongside every date: `days_vs_event_start` /
`days_vs_event_end` for each purchase order, and
`earliest_arrival_days_vs_event_start` / `..._vs_event_end` in the
lead-time check; the agent prompt forbids stating any day-count that is
not one of those numbers. S06 — the scenario that produced the invented
"227 days" — now reads *"earliest arrival 2027-08-29 is 265 days after
event start 2026-12-07"*: exactly the code-computed figure. Every other
day-count in the run (8 statements across S01, S02, S05, S07, S08, S10)
was checked against the rule engine and is exact. Two wording residues,
neither a wrong number: S06's recommendation calls the 35 code-provided
days-to-event a "35-day event timeline" (loose phrasing, right number),
and S07's summary carries one convoluted sentence about net shortage —
its verdict and shortage (2) are correct, and the Stage 5 "count to
expedite" muddle is gone.

**Fix 2 — citation stability: verified for the runs it governs.** The
agent now validates its own output: if a policy-driven status
(SHORT_UNCOVERED with escalation, COVERED_BY_TRANSFER,
COVERED_BY_ALTERNATE, INSUFFICIENT_DATA) returns with `notes_cited`
empty, the call is retried once with the gap named explicitly, and the
retry is flagged in the run log (`usage.citation_retry`). In this re-run,
every one of the 6 policy-driven scenarios cited at least one note —
S06 cited N11 and N05 on the first pass, closing the exact gap the
Stage 5 review flagged. The retry fired once (S01), and the retried
answer cited N05, N03, N11. Overall runs citing ≥1 note is unchanged at
6/10 — but the composition is different: the four non-citing runs are now
the OK and COVERED_BY_PO cases, whose recommendations are monitoring
actions (watch a delivery, confirm receipt) rather than policy actions.
Citations are recorded where a policy drives the recommendation; whether
routine-coverage runs should also always cite is left as a judgement
call, noted rather than forced.

**What did not change:** verdicts were already exact and remain so — the
fixes touched only the prose layer and the citation gate, which is where
the Stage 5 findings lived.
