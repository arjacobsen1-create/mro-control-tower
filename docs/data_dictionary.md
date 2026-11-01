# Data Dictionary — Synthetic MRO Supply Chain Dataset
As-of date for the whole snapshot: **2026-11-02**. All data is synthetic and hypothetical.
**Testing rule: this reference date is pinned.** All tests, evaluations, and
coverage calculations for this project must use 2026-11-02 as "today" — never
the date the test happens to run on — so results stay reproducible.

## parts.csv
| Column | Meaning |
|---|---|
| part_id | Internal key (P001–P024) |
| part_number | Fictional part number |
| description | Part description |
| ata_chapter | ATA chapter (2-digit) the part belongs to |
| criticality | AOG / HIGH / ROUTINE |
| lead_time_days | Typical supplier lead time |
| unit_cost_usd | Invented unit cost |
| alternate_part_id | Approved alternate part, blank if none (see knowledge notes for conditions) |
| supplier | Fictional supplier name |

## inventory.csv
One row per part per site (a *missing* row is meaningful — it is how the
INSUFFICIENT_DATA case is represented).
| Column | Meaning |
|---|---|
| qty_on_hand | Physical stock at the site |
| qty_reserved | Committed to in-progress work — **never** counts as available |
| reorder_point / bin_location / last_count_date | Planning and location metadata |

## purchase_orders.csv
| Column | Meaning |
|---|---|
| qty_ordered / qty_received | Outstanding balance = ordered − received |
| promised_date vs expected_date | Planning always uses **expected_date** |
| status | open / partially_received / received |
| delivery_site | Site the balance will arrive at |

## maintenance_schedule.csv
Events E001–E006: tail_id (fictional), aircraft_model, check_type, site,
planned_start / planned_end, status.

## demand.csv
Bill of materials: event_id, part_id, qty_required.

## maintenance_logs.csv
Historical service rows (seeded filler) shaped on public maintenance-log
templates: service date, aircraft, site, work type, component, parts used,
labour hours, cost, scheduled flag, status.

## knowledge_notes.csv
The retrieval layer: 12 short notes (interchangeability, procedure, policy,
supplier) that a RAG component grounds its recommendations in. Several notes
encode rules the scenarios test (transfer takes 2 working days; reserved stock
is excluded; rotable returns are not inbound coverage).

## eval_scenarios.csv
Ground truth for 10 (event, part) demand lines: expected_status,
expected_shortage_qty, rationale.

## The availability rule (the contract for any consumer of this data)
For a demand line (event, part) with quantity required R at event site S, event start D:
1. `site_available` = qty_on_hand − qty_reserved at S. No inventory row at S = no record.
2. `inbound` = sum of PO outstanding balances for the part where status ∈ {open, partially_received}, delivery_site = S, and expected_date ≤ D.
3. `network_available` = sum of site_available over all other sites.
4. `alternate_available` = site_available at S of the part's approved alternate (if any).

Classification, in order:
- **INSUFFICIENT_DATA** — no inventory row at S *and* no PO rows exist for the part. Escalate; never estimate.
- **OK** — site_available ≥ R
- **COVERED_BY_PO** — site_available + inbound ≥ R
- **COVERED_BY_TRANSFER** — + network_available ≥ R
- **COVERED_BY_ALTERNATE** — + alternate_available ≥ R
- **SHORT_UNCOVERED** — otherwise; shortage = R − (all of the above)
