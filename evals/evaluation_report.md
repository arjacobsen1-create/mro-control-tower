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

---

## V2 addendum — cross-event, slippage, watchlist, horizon (Stage V2-5, 6 November 2026)

**Run:** 6 November 2026 · **Model:** claude-haiku-4-5 · **Reference date:** 2026-11-02 (pinned)
**Method:** `evals/run_evaluation_v2.py` ran the 20 V2 scenarios
(`data/eval_scenarios_v2.csv` — written in Stage V2-0 and reproduced
20/20 by the independent pure-code recomputation in
`evals/validate_v2.py` *before* any agent run) live through the V2
agent path, then re-ran the 10 V1 scenarios unchanged through the
untouched V1 agent path as a regression set. Scoring is exact-match
per scenario on the fields that scenario tests (spec §6.1). Raw
output: `evals/results_v2_2026-11-06.json`; every run is also in
`monitoring/runs.jsonl`.

## Headline results

**V2 scenarios: 18/20. V1 regression: 10/10** — the V1 verdicts are
undisturbed by the V2 layer, as designed.

| # | Event/Part | Fields tested | Result |
|---|---|---|---|
| C01 | E003/P001 | allocated SHORT / 1, CONTENDED_SHORT | PASS |
| C02 | E006/P016 | allocated SHORT / 3, CONTENDED_SHORT | PASS |
| C03 | E006/P011 | allocated SHORT / 3, CONTENDED_SHORT | PASS |
| C04 | E006/P006 | allocated SHORT / 1, CONTENDED_SHORT | PASS |
| C05 | E005/P005 | allocated COVERED_BY_TRANSFER, CONTENDED_COVERED | PASS |
| C06 | E002/P016 | allocated = V1, UNCONTENDED | PASS |
| R01 | E001/P002 | slippage tier SLIPPAGE_HIGH | **FAIL — run error (below)** |
| R02 | E002/P006 | slippage tier SLIPPAGE_HIGH | PASS |
| R03 | E002/P015 | slippage tier SLIPPAGE_WATCH | PASS |
| R04 | E005/P002 | slippage tier NONE (same PO as R01) | PASS |
| R05 | E004/P021 | slippage tier NONE (not load-bearing) | PASS |
| W01 | E004/P011 | watchlist ORDER_BY_CLOSING | PASS |
| W02 | E006/P011 | watchlist ORDER_BY_CLOSING | PASS |
| W03 | E001/P005 | watchlist NONE (the noise trap) | PASS |
| W04 | E001/P001 | watchlist NO_ORDERING_FALLBACK | PASS |
| W05 | E003/P003 | watchlist NO_ORDERING_FALLBACK | PASS |
| P01 | E006/P011 | OK + ORDER_BY_CLOSING + procurement RAISED with documented need | PASS |
| X01 | E001/P001 | no feasible recovery → defer + prepared draft | PASS |
| X02a | E001/P002 | draft prepared, checkpoint 2026-11-12, verifications outstanding | **FAIL — run error (below)** |
| X02b | E002/P015 | no customer escalation (paired control) | PASS |

**Cost:** the 30-run pass used 483,205 input + 39,385 output tokens
≈ **US$0.68** at Haiku list prices. A V2 run costs roughly 3× a V1
run (≈US$0.023 vs ≈US$0.011): nine tools return richer payloads
across a longer tool loop. The §10 planning estimate (US$0.33 for
the pass) was extrapolated from V1 actuals and understated this;
the measured figure is the one recorded here.

## The two misses — run failures, analysed before V2-6 (per the stage gate)

R01 and X02a both failed the same way: the agent run raised an
exception and produced **no assessment at all** — they are not wrong
answers, they are missing answers. Both were on the same line
(E001/P002). Three honest qualifications:

1. **Root cause — identified during V2-6 (this paragraph replaces
   the initial "not identifiable" note).** The runner stored
   `str(ex)`, which was empty because the failing asserts carried no
   message; at that point the cause could not be proved from the
   record, and the runner was fixed to store full tracebacks. The
   failure then reproduced live during the V2-6 planner-data build,
   with the traceback intact: `validate_v2` rejected the run on
   `feasible_recovery_exists` not being a boolean. The mechanism is
   specific to this line's shape: E001/P002 is not short in either
   view, so `get_horizon` returns `recovery.feasible: null` (no
   shortage to recover from), while the output format requires a
   boolean — the prompt's "otherwise true" rule asks the model to
   synthesise `true` rather than copy a value, and on these runs it
   copied the null instead. A schema/type failure on a field whose
   correct value is fully determined by the tools — not a wrong
   verdict, and not a ground-truth or engine error (the tool layer
   returns the correct values deterministically, and the pure-code
   validator reproduces the scenario).
2. **Fix, and its verification.** Three changes, all in the agent
   layer (no ground truth, engine or scoring change): the prompt
   rule now states explicitly that the tool's null means "no
   shortage" and must never be copied into the boolean field; the
   validator's asserts all carry messages; and `assess_v2` gained a
   validation retry — the Stage 6 citation-retry pattern applied to
   schema failures: on a validation `AssertionError` the run is
   retried once with the failure named, flagged in the usage record
   as `validation_retry`. Post-fix verification: five consecutive
   runs of E001/P002 all succeeded with every scored field correct
   (the retry fired once and caught that run's slip), and the
   short-line cases still copy the tool value exactly (E006/P011
   feasible=true, E001/P001 feasible=false, no retry). **The
   recorded evaluation score stays 18/20** — it is the honest
   record of the pass as run; the fix is verified by targeted runs,
   not by re-running the evaluation until the number improves.
3. The failure mode matters for how V2 should be operated: an
   assessment that fails validation produces nothing, and a planner
   surface must treat "no assessment" as an escalation trigger, not
   as silence. Recorded here rather than smoothed over.

## Narrative review

- **Decision-value variance on an unscored field:** E006/P011 was
  assessed three times (C03, W02, P01). Twice the recommended
  decision was `escalate_expedite` (the shortage row of §7); once
  (W02's run) it was `place_order` (the Tier A row). Both values are
  real decisions on different dimensions of the same line — §7
  precedence puts the shortage row first, so `place_order` is the
  weaker reading — but no scored field was affected (W02 scores the
  watchlist tier only) and the procurement action with its
  documented need was raised in all three runs. A future prompt
  revision should pin the primary-decision precedence harder;
  recorded as a known variance, not fixed by re-running.
- **Citations:** 15 of 18 completed V2 runs cited at least one
  knowledge note; the citation retry fired twice (C03, W02) and both
  retried runs cited. The three non-citing completions (R05, W03,
  X02b) are the plain-OK / correctly-unflagged cases, the same
  composition as the V1 Stage 6 pattern.
- **The traps all held:** the phantom stock/PO/transfer cases (C01,
  C02, C04), contention-without-shortage (C05), the same-PO
  different-line trap (R04), the not-load-bearing trap (R05), the
  watchlist noise trap (W03), the escalation boundary from both
  sides (X02a's expectation was met by the diagnostic run; X02b's
  control passed live), and the honest no-recovery output (X01)
  all behaved as the ground truth requires.

## Conclusion

The V2 layer does what the spec claims: allocation exposes shortages
the single-line view cannot see (4 flips to short, all reproduced by
the agent), slippage risk attaches to (line, PO) pairs rather than
POs, the watchlist stays a 15-line exception surface instead of a
31-line dump, and the dimension separation (§1 rule 8) survives
contact with the agent — a procurement decision was raised on a
green line without being reported as a shortage (P01), and a
customer escalation was prepared with its governance attached
(X01) and withheld where it was not earned (X02b). The recorded
score is 18/20 with two run failures analysed above; the V1
regression is 10/10.
