# MRO Supply Chain Control Tower (prototype)

An agentic decision-support prototype for spare-parts availability and
material-shortage exceptions in a fictional aerospace MRO (maintenance,
repair and overhaul) operation.

**Everything here is synthetic and hypothetical.** The data was designed and
generated for this project. No real company, client, aircraft, or operational
data is used anywhere. Built as a personal capability project, in stages,
with an evaluation set published *before* the agent was scored against it.

## Data Source
This project uses a 100% synthetic and hypothetical dataset created
specifically for this prototype. No real company, client, aircraft, or
operational data is used. Part numbers, suppliers, tail IDs, prices,
inventory levels, and operational scenarios are fictional and intended
solely for demonstration, development, and evaluation purposes.

The dataset is published separately on Hugging Face for reproducibility
and reuse: [View the synthetic MRO supply-chain dataset on Hugging Face](https://huggingface.co/datasets/Anahitarj/synthetic-mro-supply-chain).
Hugging Face is the dataset repository (data, dataset card, generation and
validation scripts, CC0-1.0). This GitHub repository holds the application:
agent code, ingestion, architecture, and instructions.

## What it does
For each scheduled maintenance event, the system checks every required part
against stock, inbound purchase orders, network stock at other sites, and
approved alternate parts, then produces a structured assessment with a
recommendation for a human planner, who approves or rejects it. The agent
recommends; it never acts. The system is read-only by design.

Design rule that runs through the whole build: **all arithmetic is done by
code, never by the language model.** The model orchestrates tools, grounds
its recommendations in a small policy knowledge base, and explains. It does
not compute stock, dates, or lead times.

## Architecture
- **Data** — 8 synthetic tables (parts, inventory, purchase orders, schedule,
  demand, history logs, knowledge notes, evaluation scenarios), published as a
  public dataset on Hugging Face (see Data Source above). The CSVs are not
  duplicated in this repo; download them into `data/` to run locally.
- **Ingestion** (`ingest/`) — loads the tables into a local SQLite store with
  integrity checks; indexes the knowledge notes (FTS5/BM25) for retrieval,
  with a calibrated relevance threshold so off-topic questions return nothing
  (abstention) instead of a weak match.
- **Agent** (`app/`) — Claude with five read-only tools. Coverage status comes
  from a deterministic rule engine (`app/availability.py`); lead-time dates
  (order-by date, already-passed flag, earliest arrival) are computed in code
  against a pinned reference date, 2026-11-02, so tests are reproducible.
- **Evaluation** (`evals/`) — the agent is scored against 10 ground-truth
  scenarios covering every coverage status, including traps: a PO arriving
  after the event starts, reserved stock that is not available, and a part
  with no record at the site (correct behaviour: report insufficient data and
  escalate, never estimate).

## Status
- Stage 1 — dataset: complete, validated 10/10, published (v1.1, realistic
  MRO lead times: engine hot-section parts 450–540 days).
- Stage 2 — ingestion + retrieval: complete; integrity checks pass;
  retrieval tests 10/10 including the abstention case.
- Stage 3 — agent workflow: complete; first live assessments match ground
  truth. Model: Claude Haiku (development), usage logged per run.
- Stage 4 — planner view (approve/reject): complete — a clickable planner
  screen lists every event and demand line, shows the stored agent
  assessments, and records the planner's Approve/Reject per assessed line
  (repo version: `app/planner.py`, local, standard library only). Decisions
  are written to a local file, never to the project data.
- Stage 5 — full evaluation: complete — **10/10**, status and shortage exact
  on all 10 scenarios (≈ US$0.10 of API usage). Narrative review, including
  the flaws found in the prose around the verdicts: `evals/evaluation_report.md`.
- Stage 6 — monitoring + write-up: complete — the two prose fixes from the
  evaluation landed (day-counts inside recommendations are now computed by
  the rule engine, and policy-driven assessments are citation-checked with
  one automatic retry), the evaluation was re-run fresh at **10/10**
  (≈ US$0.12), and `monitoring/summarize_runs.py` produces a run/cost/
  decision summary from the local logs.

Process, decisions, and the step-by-step roadmap: `docs/process-and-roadmap.md`.
Data definitions and the availability rule: `docs/data_dictionary.md`.

## Run it
First fetch the data: download the CSVs from the
[Hugging Face dataset](https://huggingface.co/datasets/Anahitarj/synthetic-mro-supply-chain/tree/main/data)
into `data/` (the dataset repo also carries `generate_dataset.py`, which can
regenerate them locally from scratch).
```
python3 generate_dataset.py        # regenerate the synthetic data (deterministic)
python3 validate_dataset.py        # verify the evaluation ground truth (10/10)
python3 ingest/ingest.py           # build the local store + retrieval index
python3 ingest/test_retrieval.py   # retrieval tests
python3 app/test_tools.py          # rule-engine tests (no API key needed)
python3 app/agent.py E001 P001     # one live assessment (needs an Anthropic API key)
python3 app/planner.py             # planner screen at http://127.0.0.1:8765 (approve/reject)
python3 monitoring/summarize_runs.py  # run/cost/decision summary -> monitoring/summary.md
```

## Honest limitations
- Synthetic data, deliberately small (24 parts, 6 events). The point is the
  architecture and the evaluation discipline, not scale.
- The model's prose around the verdicts was the weak layer, and it is
  documented rather than hidden: the first evaluation caught an invented
  day-count and unstable citations. Both are now constrained by code
  (day-counts are rule-engine outputs; policy-driven assessments must cite
  their grounding or are retried once) and the re-run is clean — see the
  Stage 6 addendum in `evals/evaluation_report.md`. Loose phrasing can
  still occur; wrong numbers traced to the tools have not survived a check.
- Lead times are modelled from public industry reporting, not from any
  operator's real procurement data.

## Credit
Project structure and staging modelled on the public LLM Zoomcamp capstone
by MathmoKiwi — https://github.com/MathmoKiwi/LLM-Zoomcamp-2026 — with data
and code original to this project.

## License
Code and data: CC0-1.0.
