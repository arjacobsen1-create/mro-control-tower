# MRO Control Tower — Process and Roadmap

Project documentation: how this project started, the rules it runs under, what
has been built so far, and what remains, stage by stage.

- **Project:** Agentic MRO Supply Chain Control Tower (prototype)
- **Setting:** hypothetical aerospace maintenance, repair and overhaul (MRO)
- **Status as of 1 Nov 2026:** Stages 1–6 complete and verified; dataset at
  v1.1; agent live; Stage 5 evaluation 10/10, Stage 6 re-run 10/10 after the
  two prose fixes. Code for Stages 1–3 and 5 published on GitHub; the
  Stage 4/6 files are built locally and published via the same route.

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

**v1.1 update (1 Nov 2026) — realistic lead times.** Real engine hot-section
parts take 12–24 months to procure (titanium disks 18–24 months, HPT blades
9–15+, castings/forgings 12–18), so the lead times were rebuilt to match
public industry reporting (blade and nozzle sets 450–540 days; common
consumables 30–120 days) and PO order dates shifted back accordingly.
Scenario outcomes unchanged — lead time feeds the timing check, not the
classification. Republished, commit `cdeb899`; all checks re-run green
(dataset 10/10, retrieval 10/10, tool layer 13/13).

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

### Stage 3 — Agent workflow (complete, 1 Nov 2026)

**Built:** `app/availability.py` (the deterministic rule engine, including a
code-computed lead-time check: lead time, order-by date, already-passed flag,
earliest arrival if ordered on the reference date), `app/tools.py` (five
read-only tools: `get_event`, `get_demand`, `get_part`, `check_availability`,
`search_knowledge`), and `app/agent.py` (Claude tool-use loop producing a
schema-validated JSON assessment; every run logged to `monitoring/runs.jsonl`).
Tool-layer tests: **13/13**. Model: `claude-haiku-4-5`.

**API access:** Anahita created an Anthropic Console account (Individual),
bought $5 credit, declined auto-reload, and created a key (30-day expiry,
~1 Dec 2026) stored via the secure connector — never in code, chat, or the
repo. Total spend across Stages 3 and 5: under US$0.25.

**Live verification:** first three assessments (E001/P001, E004/P019,
E003/P003) all matched ground truth exactly. One narrative flaw found and
fixed during verification: the model presented an already-passed order-by
date as forward advice, in prose. The lead-time check was moved into the
rule engine so dates are code-computed, and the system prompt requires the
agent to state plainly when an order-by date has passed.

### Stage 5 — Evaluation (complete, 1 Nov 2026)

`evals/run_evaluation.py` ran all 10 published ground-truth scenarios live.
**Score: 10/10, status and shortage exact on every scenario**, for ≈ US$0.10
of API usage. Full findings in `evals/evaluation_report.md`, including the
honest narrative review: verdicts machine-exact (they are code-derived),
with one unverified day-count in S06's prose (227 days, matching neither
the start-based 265 nor end-based 256), citation behaviour varying between
runs (S06 cited N05/N11 previously, none in the scored run), and one muddled
sentence in S07. Both fixes are recorded as Stage 6 items.

### Stage 4 — Planner view (complete, 1 Nov 2026)

The human approval gate, made visible, in two forms with identical
behaviour: a web planner screen (built first) and a repo version,
`app/planner.py` (Python standard library only — `python3 app/planner.py`,
then open http://127.0.0.1:8765). Both read `evals/planner_data.json`
(all 6 events, all 33 demand lines with rule-engine verdicts; the 10
evaluated lines carry their full agent assessments). The planner picks an
event, reads each assessed line's verdict, coverage summary,
recommendation, and cited notes, and records **Approve** or **Reject**
per line — with undo and change, and a timestamped decision log.
Decisions are written to `monitoring/planner_decisions.json` (local only,
gitignored). Nothing in the screen can alter the underlying data:
read-only by design, exactly as specified. The screen starts clean — all
10 assessed lines pending a decision.

### Stage 6 — Monitoring + fixes (complete, 1 Nov 2026)

The two fixes recorded from the Stage 5 evaluation, landed and re-tested:

1. **Day-counts are code-computed.** `check_availability` now returns day
   differences next to every date it reports: per-PO `days_vs_event_start`
   / `days_vs_event_end`, and `earliest_arrival_days_vs_event_start` /
   `..._vs_event_end` in the lead-time check. The agent prompt forbids
   stating a day-count that is not one of those numbers, and requires
   omitting the number when the needed difference was not provided.
2. **Citation stability.** The agent validates its own assessment: a
   policy-driven status (SHORT_UNCOVERED with escalation,
   COVERED_BY_TRANSFER, COVERED_BY_ALTERNATE, INSUFFICIENT_DATA) returned
   with an empty `notes_cited` is retried once, with the gap named, and
   the retry flagged in the run log (`usage.citation_retry`).

**Re-evaluation:** `evals/run_evaluation.py` re-run fresh after the fixes
— **10/10 again** (75,960 input + 8,276 output tokens ≈ US$0.12). S06 now
states the code-computed "265 days after event start" instead of the
invented 227; every day-count in the run traces to a tool-provided
number; all 6 policy-driven scenarios cited at least one note (S06 cited
N11 + N05 unprompted; the citation retry fired once, on S01, and worked).
Full addendum in `evals/evaluation_report.md`.

**Monitoring summary:** `monitoring/summarize_runs.py` reads the run log
and the decision file and writes `monitoring/summary.md` — run totals,
latest-run status per scenario vs ground truth, token totals and
estimated cost, citation behaviour, and decisions
approved/rejected/pending. First production: 25 runs logged, latest-run
score 10/10, cumulative estimated cost US$0.27, decisions 0/0/10 pending.

### Publication (1 Nov 2026)

Code published publicly at
https://github.com/arjacobsen1-create/mro-control-tower — README (with the
Data Source section), code, and docs only. The dataset is **not** duplicated
there; Hugging Face remains its single home and the README links to it.
Account note: the owner's GitHub username is `arjacobsen1-create`
(Google-linked, password set 1 Nov 2026 and stored in the vault); the GitHub
handle "Anahitarj" belongs to a different person — it is her Hugging Face
username only.

---

## 4. What remains

All six stages are built and verified. What remains is use and upkeep,
not construction:

- **Anahita's planner decisions.** The 10 assessed lines sit pending in
  the planner screen; approving/rejecting them is the acceptance test of
  the human gate, done by hand, whenever she chooses.
- **README read-through.** The final README text is hers to read once
  before the Stage 4/6 files are published — the same rule as Stage 5.
- **Publication of the Stage 4/6 files** to GitHub via the established
  route (code and docs only; no data, no logs, no decision file).
- **API key renewal.** The current Anthropic key expires ~1 Dec 2026;
  a fresh key is created the same way when runs start returning 401.

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
| `app/availability.py` | Deterministic rule engine, incl. code-computed lead-time check |
| `app/tools.py` | The agent's five read-only tools |
| `app/agent.py` | Claude tool-use agent; validated JSON assessments |
| `app/planner.py` | Stage 4 planner screen (local web UI, stdlib only) |
| `app/test_tools.py` | Tool-layer tests (13/13) |
| `evals/run_evaluation.py` | Stage 5/6 evaluation runner |
| `evals/evaluation_report.md` | Stage 5 findings (10/10, with narrative review) + Stage 6 addendum |
| `evals/results_2026-11-01.json` | Raw agent output from the Stage 5 scored run |
| `evals/results_stage6_2026-11-01.json` | Raw agent output from the Stage 6 re-run (10/10) |
| `evals/planner_data.json` | All 6 events / 33 lines + the 10 stored assessments (planner screen input) |
| `monitoring/runs.jsonl` | Local run log (not published) |
| `monitoring/summarize_runs.py` | Stage 6 monitoring summary generator |
| `monitoring/summary.md` | Generated monitoring summary (runs, cost, decisions) |
| `monitoring/planner_decisions.json` | Planner approve/reject record (local only, not published) |
| `docs/data_dictionary.md` | Full availability rule, column definitions, testing rule |
| `docs/process-and-roadmap.md` | This document |
| `docs/step-by-step-guide.md` | Plain-language rebuild guide: every step, accounts to publication |
| `README.md` | Dataset card (also the Hugging Face dataset page text) |
| `repo_README.md` | Source of the GitHub repository's README.md |

Outside the project root:

- Architecture brief: `~/workspace/your_files/mro-control-tower-architecture-brief.md`
- Published dataset: https://huggingface.co/datasets/Anahitarj/synthetic-mro-supply-chain
- Published code: https://github.com/arjacobsen1-create/mro-control-tower
- Packaged dataset (zip): `~/workspace/your_files/mro-synthetic-dataset.zip`
