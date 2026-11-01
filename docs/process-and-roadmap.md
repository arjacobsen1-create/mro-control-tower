# MRO Control Tower — Process and Roadmap

Project documentation: how this project started, the rules it runs under, what
has been built so far, and what remains, stage by stage.

- **Project:** Agentic MRO Supply Chain Control Tower (prototype)
- **Setting:** hypothetical aerospace maintenance, repair and overhaul (MRO)
- **Status as of 31 Oct 2026:** Stages 1–2 complete and verified. Stages 3–6 planned.

---

## 1. How this started

On 31 Oct 2026, a portfolio-project discussion rated a **Supply Chain Control
Tower** the highest-value project to build. The scope was then narrowed
deliberately:

- **One exception type:** a part projected short against scheduled overhaul demand.
- **One workflow:** detect → assess → recommend → human decides.

Boundaries set at the start, before anything was built:

- **Study and certifications are the main track.** This project is built in
  stages, in the gaps, and never competes with exam preparation.
- **Industry focus:** aerospace MRO.
- **Everything hypothetical.** Synthetic data only — no client, employer, or
  account information anywhere in the project.

The build is modelled on a reference repository,
[MathmoKiwi/LLM-Zoomcamp-2026](https://github.com/MathmoKiwi/LLM-Zoomcamp-2026)
("Technote Copilot") — a complete, reproducible capstone with the layout
`app/ ingest/ evals/ monitoring/`, a retrieval component, structured
evaluation, monitoring, and a README that documents failures honestly. This
project follows the same skeleton and the same discipline.

An architecture brief (v0.1) was written and agreed **before** any code:
`~/workspace/your_files/mro-control-tower-architecture-brief.md`. Only after
that were stages started, one at a time, each verified before the next.

---

## 2. Standing rules

1. **Synthetic data only.** No real company, aircraft, or operational data.
2. **Pinned reference date: 2026-11-02.** The dataset's simulated "today."
   Every test and evaluation uses this date, never the date the test runs on,
   so results are reproducible.
3. **Code does the arithmetic.** Stock availability, coverage, and shortage
   quantities are computed by code/tools. The language model never estimates
   numbers.
4. **Read-only, human-gated.** The system recommends; it never acts. A human
   approves or rejects every recommendation.
5. **Abstain rather than guess.** If the system cannot see the data or find
   grounding, it reports insufficient data and escalates.

**The availability rule, in brief:** for a part required by an event,
availability = stock on hand minus reserved stock at the event's site, plus
inbound purchase-order balances that arrive on or before the event start,
plus transferable stock at other sites, plus approved alternate-part stock.
Each demand line is classified OK, COVERED_BY_PO, COVERED_BY_TRANSFER,
COVERED_BY_ALTERNATE, SHORT_UNCOVERED (with the shortage quantity), or
INSUFFICIENT_DATA. The full rule is specified in `docs/data_dictionary.md`.

---

## 3. What has been done

### Stage 1 — Dataset (complete, 31 Oct 2026)

A search of Hugging Face found no usable public MRO dataset: nothing public
models parts on shelves against parts required by scheduled maintenance. So a
synthetic dataset was designed from the shapes of public templates
(supply-chain order data, road-fleet maintenance logs, aircraft maintenance
records) and generated deterministically by `generate_dataset.py`
(core data hand-specified; filler seeded).

**8 tables, 216 rows:**

| Table | Rows | Content |
|---|---|---|
| parts | 24 | Part master: ATA chapter, criticality, lead time, alternate part, supplier |
| inventory | 69 | Stock by part and site: on hand, reserved, reorder point |
| purchase_orders | 14 | Ordered/received quantities, promised vs expected dates, delivery site |
| maintenance_schedule | 6 | Events (overhauls, C-checks, shop visits) Nov–Dec 2026 |
| demand | 33 | Bill of materials per event |
| maintenance_logs | 48 | Historical service rows |
| knowledge_notes | 12 | Policy/procedure/interchangeability notes (retrieval layer) |
| eval_scenarios | 10 | Ground-truth scenarios covering every outcome class, including deliberate traps (late PO, partially received PO, reserved stock, missing record) |

**Verification:** `validate_dataset.py` recomputes every scenario outcome from
the raw tables using only the documented availability rule. Result: **10/10
match ground truth.** The check caught one design error on its first run
(an unpinned inventory value); the data was fixed and the check re-run clean.

**Published:** public on Hugging Face, CC0-1.0, commit `7655c01`, dataset
viewer live:
https://huggingface.co/datasets/Anahitarj/synthetic-mro-supply-chain

### Stage 2 — Ingestion + retrieval (complete, 31 Oct 2026)

**Ingestion** (`ingest/ingest.py`): all 8 tables load into a local SQLite
store (`data/mro.db`). Seven integrity checks run on every load and pass:
every demand line references a real part and event, every eval scenario maps
to a real demand line, no negative stock, no purchase order received beyond
its ordered quantity, and row counts match the specification.

**Retrieval** (`ingest/retrieval.py`): the 12 knowledge notes are indexed
with FTS5/BM25, titles weighted above body text, behind a `search_notes()`
function. Tested with 9 realistic planner questions (alternate part use,
transfer timing, reserved stock, escalation, late-PO coverage, rotable
returns, missing records, pooling, configuration checks): **10/10 tests pass**,
including the abstention case below.

**Design lesson — abstention needed calibration.** Out of the box, an
off-topic query ("what's on the catering menu?") weakly matched real notes on
common words and returned results it should not have. The fix was a relevance
threshold calibrated from measured scores: genuine top matches score −4.7 to
−15.4 (BM25; more negative is stronger), the off-topic query's best accidental
match scored −1.05, so the acceptance threshold is set at −2.5. Below that,
retrieval returns nothing, and the agent layer treats "no grounding found" as
an escalation, not an invitation to improvise.

---

## 4. What remains

### Stage 3 — Agent workflow

**What gets built:** the detect → assess → recommend loop over the store.
Tool functions the agent calls: availability computation (code, per the
documented rule), purchase-order and schedule lookups, lead-time estimation,
and `search_notes()` for grounding in policy and interchangeability notes.
Output is a validated JSON assessment per exception (status, shortage,
evidence, recommendation). Every run and every human decision is logged.

**What Anahita needs to do:** provide the Claude API key (the same key used
for the Building with the Claude API course) when runs against the model
start. Prototype-scale spend only.

**How we verify:** the agent's assessments are checked field-by-field against
hand-computed results for known demand lines before the full evaluation in
Stage 5.

### Stage 4 — Planner view

**What gets built:** a Streamlit screen listing detected exceptions with
their assessments, evidence, and an approve/reject control per
recommendation — the human approval gate made visible. Decisions are written
to the run log.

**What Anahita needs to do:** review the screen layout; click through one
approve and one reject as an acceptance test.

**How we verify:** an approved and a rejected decision both appear correctly
in the log; no action exists in the UI that changes any underlying data
(read-only by design).

### Stage 5 — Evaluation

**What gets built:** a runner that executes the agent on all 10 published
eval scenarios and scores its output against the ground truth in
`eval_scenarios.csv` — status match, shortage quantity match, and grounding
(the note(s) cited must support the recommendation).

**What Anahita needs to do:** nothing to run it; review the results.

**How we verify:** the score is whatever it is — misses are reported as
misses, with the failing scenario and the agent's reasoning preserved for the
README. Reference date pinned at 2026-11-02, as everywhere.

### Stage 6 — Monitoring + README

**What gets built:** run/approval logging surfaced in a simple dashboard
(runs, decisions, latency, retrieval hit/abstain rates), and the project
README: problem, data, architecture, how to run, evaluation results, and a
rubric-style self-assessment including limitations — following the reference
repository's practice of documenting what did not work.

**What Anahita needs to do:** read the README once before it is published.

**How we verify:** a fresh clone-style run from the README instructions alone
reproduces ingestion, tests, and the evaluation.

---

## 5. File map

Project root: `~/workspace/mro-control-tower/`

| Path | What it is |
|---|---|
| `data/` | The 8 dataset CSVs, plus `mro.db` (SQLite store, built by ingestion) |
| `generate_dataset.py` | Deterministic dataset generator |
| `validate_dataset.py` | Ground-truth recomputation check (10/10) |
| `ingest/config.py` | Project config, including the pinned reference date 2026-11-02 |
| `ingest/ingest.py` | Stage 2 ingestion + integrity checks |
| `ingest/retrieval.py` | `search_notes()` — BM25 retrieval with abstention threshold |
| `ingest/test_retrieval.py` | Retrieval tests (10/10) |
| `app/`, `evals/`, `monitoring/` | Reserved for Stages 3–6, per the reference layout |
| `docs/data_dictionary.md` | Full availability rule, column definitions, testing rule |
| `docs/process-and-roadmap.md` | This document |
| `README.md` | Dataset card (also the Hugging Face dataset page text) |

Outside the project root:

- Architecture brief: `~/workspace/your_files/mro-control-tower-architecture-brief.md`
- Published dataset: https://huggingface.co/datasets/Anahitarj/synthetic-mro-supply-chain
- Packaged dataset (zip): `~/workspace/your_files/mro-synthetic-dataset.zip`
