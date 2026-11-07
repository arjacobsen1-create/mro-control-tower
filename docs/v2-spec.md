# MRO Control Tower — V2 Specification

- **Project:** Agentic MRO Supply Chain Control Tower (prototype)
- **Document:** V2 build specification — SPEC ONLY. No build code, no data
  changes and no publication are authorised by this document.
- **Date:** 2026-11-06
- **Status:** FULLY DECIDED 2026-11-06. All five decisions in §12
  (D1–D5) are settled and recorded; the spec is ready for build.
  Build has not started, and nothing in V2 is published.
- **Amendments (2026-11-06, both Anahita's catches, made after the
  first draft):** (A) customer at-risk notification (§4.6, §7) —
  waiting until mitigation fails is too late to tell the customer;
  (B) the two-clock horizon model (§5.5, §9, §10, §12 D5) — with
  450–540-day lead times, flags inside the current 8-week event
  window are a last-minute alarm. Both amendments were tested against
  the current data before being written in; results are in Appendix A.
- **Refinement package (ADOPTED 2026-11-06, at Anahita's
  confirmation):** four refinements adopted as clarified — three
  decision dimensions kept separate (§1 rule 8; §5.5, §7); scheduled
  Clock 2 reviews for every long-lead line, with advisories only on
  an identified material risk (§5.5); prepared-draft customer
  notification governance with four pre-release verification checks
  (§4.6); and two new evaluation classes (§6.2). The package also
  resolves the E006/P011 question as a principle (§5.6, §6.2 P01,
  §7) and decides D5 as (a) under a stricter acceptance criterion
  (§12). D2, D3 and D4 were **not** decided by this package.
  All three were decided separately, later the same day — see
  the notes below.
- **D2 DECIDED (2026-11-06, Anahita, individually):**
  WATCH_MARGIN_DAYS = **21 days** (§4.2, §12) — chosen over the
  recommended 14 (early-chase preference). Recomputed in code from
  the data at the decided value: the wider band changes **no**
  current-data flag (still 2 HIGH / 1 WATCH across the 6 counted
  pairs); it binds on future data. D3 and D4 were decided
  separately, later the same day — see the notes below.
- **D3 DECIDED (2026-11-06, Anahita, individually): the full
  evaluation set (§6, §12)** — 20 new scenarios (16 core C/R/W
  plus P01, X01, X02a and X02b from the adopted refinement
  package), 30 total with the 10 V1 scenarios re-run unchanged
  as regression. D4 was decided separately, later the same
  day — see the next note.
- **D4 DECIDED (2026-11-06, Anahita, individually): the
  two-tier watchlist (§5.2, §12)** — Tier A (2 lines) + Tier B
  (13 lines) = 15 of 33 lines, option (a) as recommended,
  decided on its own operational implications. With D4, all
  five decisions (D1–D5) are decided; see the Status line
  above and §12.
- **Scope agreed (Anahita, 2026-11-06):** three new exception types —
  (1) competing demand across events, (2) PO slippage risk,
  (3) order-by-date-passed watchlist — built on the FIXED V1 gate model
  (6 Nov 2026): the human decision is on the *recommended action*, and
  SHORT_UNCOVERED / INSUFFICIENT_DATA lines are escalation-only, never
  accepted.
- **Out of scope:** V3 what-if planner (separate build, separate spec);
  any change to V1's published verdicts; publishing (see §9).

---

## 1. Standing rules (unchanged from V1, restated for this build)

1. **Synthetic data only.** No real company, aircraft, or operational data.
2. **Pinned reference date: 2026-11-02.** Every calculation, test and
   evaluation in V2 uses this date as "today", never the run date.
3. **Code does the arithmetic.** Every quantity, date difference, margin
   and tier in V2 is computed by the rule engine. The language model
   never estimates a number, and may only state numbers a tool returned
   (the Stage 6 day-count rule applies to every new field in this spec).
4. **Read-only, human-gated.** The system recommends; it never acts.
   Every decision follows the fixed status→action model (§7).
5. **Abstain rather than guess.** Missing data escalates as
   INSUFFICIENT_DATA; it is never filled in.
6. **Ground truth before agent.** New evaluation scenarios (§6) are
   written and validated by a pure-code recomputation *before* any agent
   run, exactly as V1's 10 scenarios were. Scoring is exact-match.
7. **V1 is history.** V1's single-line verdicts — the published 10/10
   evaluation, `evals/planner_data.json`, the planner and dashboard as
   published — are not rewritten by V2. V2 adds a separate layer beside
   them (§3.4).
8. **Three decision dimensions, kept separate (adopted 2026-11-06).**
   V2 tracks three different decisions, which share the same
   underlying computed data but are never merged into one flag or
   one decision:
   - **Procurement readiness** — is the ordering decision being
     taken in time? Owner: the procurement / buying role.
   - **Material coverage risk** — will the material actually be
     there for the event? Owner: the maintenance planning role.
   - **Customer impact** — does the event's customer need to be
     told, and when? Owner: the customer-facing account role.

   The three dimensions have different owners, different thresholds
   and different actions. A line can be green on one dimension and
   red on another — a fully covered line can still carry an urgent
   procurement decision (§5.6), and a material risk can be real
   without yet being a customer impact (§5.5). No UI surface, gate
   action or evaluation may collapse the three into a single
   indicator; where a line is shown, its state on each dimension
   in play is shown separately (§7, §8).

---

## 2. Verified ground facts (author's working, from the current files)

Every count below was recomputed from `data/*.csv` on 2026-11-06 using
the documented availability rule. The V2-1 validator must reproduce all
of them; if it cannot, the spec — not the data — is re-examined first.

### 2.1 Demand and contention

- 33 demand lines, 21 distinct parts demanded, 6 events with distinct
  start dates (E001 2026-11-16, E002 2026-11-23, E003 2026-11-30,
  E004 2026-12-07, E005 2026-12-14, E006 2026-12-21). Chronological
  order is therefore a total order on the current data.
- **10 of the 21 demanded parts are demanded by 2–3 events** (22 of the
  33 lines involve a contended part):
  8 parts × 2 events — P001 (E001, E003), P002 (E001, E005),
  P006 (E002, E006), P008 (E001, E005), P009 (E001, E003),
  P013 (E004, E006), P015 (E002, E004), P016 (E002, E006);
  2 parts × 3 events — P005 (E001, E003, E005), P011 (E002, E004, E006).
- Recomputed V1 verdicts for all 33 lines (matches the published mix):
  19 OK, 4 COVERED_BY_PO, 4 COVERED_BY_TRANSFER, 1 COVERED_BY_ALTERNATE,
  3 SHORT_UNCOVERED, 2 INSUFFICIENT_DATA.

### 2.2 Purchase orders and slippage

- 14 POs: 9 open, 2 partially_received, 3 received.
- **All 14 POs have expected_date later than promised_date.** Slippage
  (expected − promised) ranges **4–15 days**: 4 (PO-1006), 5 (PO-1011),
  6 (PO-1013), 7 (seven POs), 8 (three POs), 15 (PO-1010).
  *(Correction to the V2 pitch, which said 7–15 days: three POs slip by
  less than 7. This spec uses the verified 4–15.)*
- Planning already uses expected_date (data dictionary rule), so the
  slippage observed so far is **already inside** every V1 verdict.
  Slippage *risk* (§4) is about a further slip beyond expected_date.
- Only **6 (event, part) lines actually count a PO** under the V1
  inbound rule (open/partially_received, delivery site = event site,
  expected_date ≤ event start, outstanding > 0):

  | Line | PO | Outstanding | Expected | Event start | Margin (start − expected) | Observed slip | PO load-bearing* |
  |---|---|---|---|---|---|---|---|
  | E001/P002 | PO-1002 | 4 | 2026-11-12 | 2026-11-16 | 4 days | 7 days | Yes |
  | E002/P006 | PO-1011 | 2 | 2026-11-20 | 2026-11-23 | 3 days | 5 days | Yes |
  | E002/P015 | PO-1007 | 6 | 2026-11-12 | 2026-11-23 | 11 days | 7 days | Yes |
  | E004/P021 | PO-1012 | 2 | 2026-11-18 | 2026-12-07 | 19 days | 8 days | No (site stock 8 ≥ req 1; status OK) |
  | E005/P002 | PO-1002 | 4 | 2026-11-12 | 2026-12-14 | 32 days | 7 days | Yes (single-line view) |
  | E006/P006 | PO-1011 | 2 | 2026-11-20 | 2026-12-21 | 31 days | 5 days | No (site stock 9 ≥ req 8; status OK) |

  *Load-bearing = removing the PO's counted balance changes the line's
  V1 status or shortage.

- The other 8 POs are not counted for any line, for structural reasons
  the spec must respect: already received in full (PO-1003, PO-1006,
  PO-1013 — no outstanding balance, slippage is history, not risk);
  expected after the event start, so already reflected in a SHORT or
  non-PO verdict (PO-1001, PO-1008, PO-1010); delivers to a site where
  no demand line counts it (PO-1004 → YYZ-H2, while P008's lines are at
  YUL-H1 — POs never count as network stock under the V1 rule);
  part never demanded (PO-1009, P014).

### 2.3 Lead-time check and the watchlist problem

- `check_availability` already returns `lead_time_check` per line:
  `lead_time_days`, `order_by_date` (event start − lead time),
  `order_by_already_passed` (order_by < 2026-11-02),
  `earliest_arrival_if_ordered_now`, and code-computed day differences.
- **A naive watchlist — "order-by date has passed" — contains 31 of the
  33 lines.** Only E004/P011 (order-by 2026-11-07) and E006/P011
  (order-by 2026-11-21) are still open. A 31-line watchlist is noise,
  not a control tower surface. §5 defines a narrower inclusion rule;
  this is the single largest correction this spec makes to the pitch.

### 2.4 Alternates

- Alternate pairs are symmetric: P003↔P023, P020↔P024. P023 and P024
  are never demanded themselves, so on current data an alternate pool
  is never contended by the alternate part's own demand. The allocation
  engine (§3) treats alternate stock as a shared pool anyway, so the
  rule stays correct if the data changes.

---

## 3. Exception type 1 — Competing demand across events

### 3.1 The defect in V1

V1's `check_availability` judges each (event, part) line in isolation:
every line sees the full site stock, the full outstanding balance of
every countable PO, the full network stock and the full alternate stock.
When two events demand the same part, the same physical units are
counted two or three times. Coverage on paper can therefore exceed
the physical pool. This is not a bug in the V1 rule — the rule answers
the question it was asked ("could this line be covered, alone?") — but
a control tower must also answer "can they *all* be covered?"

### 3.2 The allocation model (deterministic, code-only)

For each part independently:

- **Pools.** (a) Site stock: available quantity (on hand − reserved)
  per (part, site). (b) PO pool: each countable PO's outstanding
  balance, drawable only by lines at its delivery site and only when
  its expected_date ≤ the consuming event's start (the V1 inbound
  counting conditions, unchanged). (c) Network stock is not a separate
  pool — it is the other sites' site-stock pools, drawn after the
  line's own site and PO pools. (d) Alternate pool: the alternate
  part's available stock at the consuming event's site.
- **Consumption order within a line** mirrors the V1 cascade exactly:
  own-site stock → countable PO balance → network (other sites in the
  fixed site order YUL-H1, YYZ-H2, YYC-H3, skipping the event site) →
  alternate at site. This keeps allocated verdicts comparable with V1
  verdicts tier by tier.
- **Priority order across events** (Decision D1, decided, §12):
  events consume in the chosen priority order; each line's verdict is
  then recomputed against what remains. Default proposed:
  **chronological by planned_start, tie-broken by event_id.**
- **Partial allocation is retained.** A line that ends short still
  consumes what it drew (stock is physically picked for the earlier
  event). This assumption is load-bearing for scenario C01 and is
  stated in its rationale.
- **Output per line:** `v1_status` (unchanged, from the existing rule
  engine), `allocated_status` (same six-status vocabulary, computed
  against remaining pools), `allocated_shortage_qty`, the pool ledger
  for the line (units drawn per pool, code-computed), and a contention
  classification:
  - `CONTENDED_SHORT` — covered (any tier) in V1, SHORT_UNCOVERED
    after allocation.
  - `CONTENDED_COVERED` — still covered after allocation, but the
    covering tier or sources changed.
  - `UNCONTENDED` — single-event part, or allocation changed nothing.
- INSUFFICIENT_DATA lines do not consume and are not re-evaluated:
  no record means no pool to allocate from; they stay escalation-only.

### 3.3 Worked result on current data (author's computation)

Running §3.2 chronologically over the current data changes the status
of **6 of the 33 lines**; **4 lines flip from covered to short**:

| Line | V1 status | Allocated status | Why (pool arithmetic) |
|---|---|---|---|
| E003/P001 | OK | SHORT_UNCOVERED, short 1 | Only 1 unit of P001 exists (YUL-H1). E001 (earlier, req 2, already short 1) consumes it; the same unit was E003's entire site cover for req 1. PO-1001 (expected 2026-12-05) arrives after both starts. Phantom stock — the cleanest double-count in the dataset. |
| E006/P006 | OK | SHORT_UNCOVERED, short 1 | YYZ-H2 stock of 9 was counted in full by both E002 (req 10, with PO-1011) and E006 (req 8). After E002 and PO-1011's remainder and all network stock (YUL 4 + YYC 2), E006 is 1 short. |
| E006/P011 | OK | SHORT_UNCOVERED, short 3 | Total physical pool is 14 (YUL 4 + YYZ 6 + YYC 4) against total demand of 17 across E002/E004/E006. The last event absorbs the deficit. |
| E006/P016 | COVERED_BY_TRANSFER | SHORT_UNCOVERED, short 3 | Total pool 7 (3/2/2) against total demand 10 (E002 req 6, E006 req 4). V1 counted the same network stock for both events. |
| E005/P002 | COVERED_BY_PO | COVERED_BY_TRANSFER | PO-1002's outstanding 4 was counted in full by both E001 and E005. E001 draws 3; E005 covers with the remaining 1 plus a transfer. Still covered — sourcing changed, verdict tier changed. |
| E005/P005 | OK | COVERED_BY_TRANSFER | YUL-H1 stock 20 against combined YUL demand 22 (4+12+6); E005's last 2 units come from network stock. Contention without shortage. |

The remaining contended parts (P008, P009, P013, P015) allocate with no
change to any line's status. E001/P001 stays SHORT_UNCOVERED short 1 —
allocation does not deepen it, it explains E003's flip. These six rows
are the author's hand-verified computation; Stage V2-1's validator must
reproduce them exactly from the raw tables before any agent work.

### 3.4 Coexistence with V1 (no rewriting of history)

- V1 verdicts stay exactly as published. The planner gains a second,
  clearly labelled view — **"Cross-event (allocated)"** — beside the
  existing per-line view. Both statuses are shown for every line; the
  allocated view never overwrites the V1 fields in
  `evals/planner_data.json` (V2 writes its own data file,
  §8, Stage V2-6).
- The human gate (§7) acts on the allocated view for contended lines:
  that is the view that reflects physical reality. The decision record
  must store which view and which allocation policy produced the
  recommendation decided on.
- The dashboard reports the two views as separate figures and never
  blends them (§8).

### 3.5 Why chronological is the recommended priority (see §12, D1)

Criticality-weighted ordering sounds attractive and is mostly
**not computable as pitched**: criticality is a property of the *part*,
and competing lines by definition share the same part, so every
competing line for a part has identical criticality — it cannot order
them. A derived event-level criticality (the maximum criticality across
all of an event's lines) is computable, but on current data it produces
ties almost everywhere (E001, E003, E004 and E005 all contain an AOG
line) and still falls back to chronological order. Chronological —
first event, first claim on the pool — is also how the physical
picking actually happens. Recommendation: chronological; record the
criticality analysis in the decision log so the rejection is reasoned,
not silent.

---

## 4. Exception type 2 — PO slippage risk

### 4.1 Definitions (all code-computed)

For each (line, PO) pair where the PO is counted under the V1 inbound
rule for that line (§2.2 — this restriction is deliberate; see §4.3):

- `slip_days` = expected_date − promised_date (days).
- `margin_days` = event start − expected_date (days). Positive means the
  PO is expected before the event. (Already available in tool output as
  `−days_vs_event_start`; V2 names it explicitly.)
- `load_bearing` = true iff removing this PO's counted balance changes
  the line's status or shortage (computed by re-running the classifier
  without that PO — code, not judgement).
- **Repeat-slip test:** `repeat_slip_breaks` = true iff
  expected_date + slip_days > event start, i.e. iff `slip_days >
  margin_days`. Interpretation: *if this PO slips again by the amount
  it has already slipped, does the line lose this PO?*

### 4.2 Tiers

Risk is a property of a **(line, PO) pair, not of a PO** — PO-1002 is
high-risk for E001 (margin 4) and no risk for E005 (margin 32).
A line's tier is the highest tier among its counted POs.

| Tier | Condition | Meaning |
|---|---|---|
| `SLIPPAGE_HIGH` | load_bearing AND repeat_slip_breaks | One more slip like the last one and the coverage the verdict rests on is gone. |
| `SLIPPAGE_WATCH` | load_bearing AND NOT repeat_slip_breaks AND margin_days ≤ WATCH_MARGIN_DAYS | Covered, but the buffer is thin enough that ordinary delivery noise matters. Threshold decided under D2 (§12): WATCH_MARGIN_DAYS = 21 days. |
| *(no flag)* | not load_bearing, OR margin_days > WATCH_MARGIN_DAYS with the repeat-slip test passed | The PO is either not holding the line up, or the margin absorbs a repeat slip comfortably. |

Applied to the current data (at the decided 21-day watch margin,
D2 §12), exactly **3 of the 6** PO-counted lines are flagged:

| Line | Margin | Slip | Repeat-slip | Tier |
|---|---|---|---|---|
| E001/P002 | 4 | 7 | Breaks (2026-11-12 + 7d = 2026-11-19 > start 2026-11-16) | SLIPPAGE_HIGH |
| E002/P006 | 3 | 5 | Breaks (2026-11-20 + 5d = 2026-11-25 > start 2026-11-23) | SLIPPAGE_HIGH |
| E002/P015 | 11 | 7 | Holds (2026-11-19 ≤ 2026-11-23) | SLIPPAGE_WATCH |
| E005/P002 | 32 | 7 | Holds | *(no flag — same PO as E001/P002, different line, different answer)* |
| E004/P021 | 19 | 8 | Holds; also not load-bearing | *(no flag)* |
| E006/P006 | 31 | 5 | Holds; also not load-bearing in the single-line view | *(no flag — see §4.4)* |

Precisely: slippage is **harmless** when the PO is not load-bearing for
the line, or when margin_days ≥ slip_days (a repeat of the observed
slip still lands before the event) *and* the margin is outside the
watch band. Slippage **threatens** coverage when load-bearing inside
the watch band, and **breaks** coverage (on a repeat) when
slip_days > margin_days on a load-bearing PO. No other combination is
flagged; in particular a large slip_days alone flags nothing (PO-1010
slipped 15 days, the largest in the data, and is flagged nowhere —
it was never counted for its line, §2.2).

*D2 recomputation note (2026-11-06): widening the watch margin from
the recommended 14 to the decided 21 days changes **no** flag on
current data. The only counted pair whose margin falls in the
14–21 band is E004/P021 (margin 19, slip 8, repeat-slip holds), and
it is **not load-bearing** — E004's site stock (8) covers its
requirement (1) with or without PO-1012, and P021 is demanded by
no other event, so the allocated view (§4.4) cannot change that —
the load-bearing condition excludes it at any threshold. Flagged
sets by threshold, recomputed in code from `data/*.csv` at the
pinned reference date: 7 days → 2 HIGH + 0 WATCH; 14 days →
2 HIGH + 1 WATCH; 21 days → 2 HIGH + 1 WATCH (E002/P015,
margin 11). The 21-day value widens the band for future data
only.*

### 4.3 What is deliberately excluded

- POs received in full: slippage happened, goods arrived, nothing is
  at risk. Their slip values are history for supplier reporting, not
  exceptions.
- POs not counted for a line (late, wrong site, part not demanded):
  their effect is already fully reflected in the line's V1 verdict.
  Flagging them again would double-report one problem as two.
- `INSUFFICIENT_DATA` and `SHORT_UNCOVERED` lines receive no slippage
  flag: they are already escalated as shortages/unknowns; a risk flag
  on top adds no decision.

### 4.4 Interaction with the allocation layer (§3)

Where both layers apply, slippage is assessed against the **allocated**
view: a line that is SHORT after allocation is handled as a shortage,
full stop — no slippage flag. A line still covered after allocation
keeps the flag computed in §4.2, with `load_bearing` also re-checked
against the allocated sourcing (a PO the allocation actually drew on
is load-bearing for that line's allocated verdict). Worked consequence:
E006/P006 carries no flag in the single-line view, but after
allocation it is CONTENDED_SHORT and is escalated as a shortage — the
risk did not need a flag, it materialised. This precedence (shortage
> slippage > watchlist) is used again in §5.4 and §7.

### 4.5 Code change this requires (spec-level, no code in this document)

`check_availability`'s `po_detail` currently returns expected_date but
**not promised_date** — slippage is not computable from today's tool
output. V2 must add `promised_date`, `slip_days`, `margin_days` and
`load_bearing` to `po_detail` (all computed in `app/availability.py`,
per standing rule 3). This is an additive change to the tool output;
it must not alter any V1 verdict (regression gate, Stage V2-2).

### 4.6 Customer at-risk notification (Amendment A, 2026-11-06)

*Anahita's catch: under §§4.2/7 as first drafted, the customer would
only be told once mitigation had failed and the planner chose to
defer — which is too late. The customer has its own operation built
around the aircraft coming back; silence until certainty is the
worst of the options. The notification model is therefore two-stage:*

- **Stage 1 — at-risk advisory (new gate action, §7).** A line in
  `SLIPPAGE_HIGH`, and a line that is `CONTENDED_SHORT` after
  allocation (§3), gains the gate action **Notify customer —
  at risk**. The decision record carries a **checkpoint date**,
  computed in code, never estimated: for a slippage line, the
  counted PO's expected arrival date (the date the risk resolves
  one way or the other — on current data, 2026-11-12 for E001/P002
  and 2026-11-20 for E002/P006); for a contended-short line, the
  event start (the date the shortage bites). The advisory says the
  delivery is *at risk*, names the mitigation underway, and commits
  to a firm update by the checkpoint date. It does **not** state a
  revised delivery date.
- **Stage 2 — confirmed revision.** A revised delivery date is
  communicated only if the planner subsequently decides to defer
  the event (the existing Escalate — defer event decision, §7).
  By then it is a confirmation, not a surprise.
- **WATCH stays internal.** A `SLIPPAGE_WATCH` line's buffer absorbs
  a repeat slip (§4.2); notifying the customer about it would cry
  wolf and devalue the HIGH advisory. The tier boundary in §4.2 is
  therefore also the notification boundary: HIGH notifies, WATCH
  does not. The same applies to the horizon advisories in §5.5,
  which are planner-facing except at the Clock 2 advisory points
  defined there.
- **Recovery path is recorded.** Every decision on a HIGH line
  (either tier of this section, slippage or contended) must record
  the recovery path the human chose, as a named field in the
  decision record — one of: **expedite / chase PO**, **exchange /
  rotable**, **transfer under allocation**, **re-sequence the
  check**, or **defer**. A HIGH decision with no recovery path
  recorded is incomplete; the planner UI must not let it save
  without one (server-side validation, as with decision values, §7).
- **Notification governance (adopted 2026-11-06).** The system
  **prepares a draft** customer notification from the computed
  facts (line, checkpoint date, recovery path); it never sends
  anything, to anyone, at any tier (read-only rule, §1 rule 4).
  Release is a human decision, and before the planner may record
  a **Notify customer — at risk** decision as released, they must
  verify four named checks, each recorded in the decision record
  alongside the recovery path and checkpoint date:
  (i) **the affected event** — the event, aircraft visit and dates
  named in the draft are the ones the flag belongs to;
  (ii) **the material shortfall** — the quantity and part at risk
  are the computed ones, on the dimension that raised the flag;
  (iii) **the recovery options** — the recovery path recorded is
  the one actually being pursued, and the draft's description of
  the mitigation underway matches it;
  (iv) **the proposed communication itself** — the draft says
  *at risk*, names the mitigation and the checkpoint commitment,
  and states no revised delivery date (stage 2 governs that, §7).
  A notification decision whose record lacks any of the four
  verifications is incomplete and must fail server-side validation,
  exactly as a HIGH decision without a recovery path does.
- **Honest limitation (stated to Anahita when this was raised):**
  the dataset treats every part as needed at event start. Real
  checks consume parts across the whole event window, so a part
  arriving mid-window may still be on time in reality. The model
  is therefore *conservative*: it flags, and under this section
  would notify, earlier than a task-level model would. That is the
  safe direction for a prototype whose ground truth is defined at
  event start, but it is a modelling choice, not a fact about real
  checks, and any external write-up must say so.

---

## 5. Exception type 3 — Order-by-date-passed watchlist

### 5.1 Purpose, restated honestly

The lead-time check answers: *"if this part ran out, could we still
order our way out before the event?"* The watchlist exists to surface
the lines where the answer changed, or is about to change — not to
list every line whose date arithmetic is in the past (§2.3: that is
31 of 33 lines, which is a report nobody would read).

### 5.2 Inclusion rule (two tiers, both code-computed)

A line is on the watchlist iff it falls in exactly one tier:

- **Tier A — `ORDER_BY_CLOSING` (act now):** `order_by_already_passed`
  is false AND order_by_date falls within `WATCHLIST_HORIZON_DAYS`
  after the reference date. Recommended horizon: 21 days
  (Decision D4, decided 2026-11-06, covers the overall inclusion
  shape; the horizon is a named constant, initial value 21). On current data this tier
  contains **exactly 2 lines**: E004/P011 (order-by 2026-11-07,
  5 days after the reference date) and E006/P011 (order-by 2026-11-21,
  19 days after). These are the only lines in the dataset where
  "order soon" is still a real, losable option.
- **Tier B — `NO_ORDERING_FALLBACK`:** `order_by_already_passed` is
  true AND the line's status is **not OK** (i.e. COVERED_BY_PO,
  COVERED_BY_TRANSFER, COVERED_BY_ALTERNATE, SHORT_UNCOVERED or
  INSUFFICIENT_DATA) AND earliest arrival if ordered now falls after
  the event start (code check:
  `earliest_arrival_days_vs_event_start > 0`). On current data this
  tier contains **13 lines** (every non-OK line except E004/P011,
  whose order-by date has not passed).

Total watchlist on current data: **15 of 33 lines** (2 + 13).

### 5.3 The covered-line question, answered explicitly

A fully covered line (status OK) with a passed order-by date is
**excluded, and that is the right call**: the stock is physically on
the shelf; the passed date changes nothing about this event, and
listing 18 such lines (that is the count: 18 of the 19 OK lines have
a passed order-by date) would bury the 2 lines where action is still
possible. The passed date on an OK line is a replenishment-planning
fact, not an exception, and this system reports exceptions.

A *plan-covered* line (COVERED_BY_PO / TRANSFER / ALTERNATE) with a
passed order-by date **is included** (Tier B), for a different reason:
its coverage is a plan, not a fact — a PO that must arrive, a transfer
that must be executed, an alternate that must be approved — and the
passed order-by date means that if the plan fails there is **no
ordering fallback inside the event window** (earliest arrival if
ordered now is provably after the event start, and for these parts
typically hundreds of days after: lead times 120–540 days against
event starts 14–49 days out). Tier B is therefore not noise; it is
the list of lines where the existing plan is the *only* plan.
SHORT_UNCOVERED and INSUFFICIENT_DATA lines in Tier B add no new
decision (§5.4) — they are listed so the watchlist is a complete
answer to "where can we no longer order our way out?", and they are
visually subordinate to Tier A.

### 5.4 One decision per line

The watchlist is a **view, not a second gate**. A line is decided
once, in the planner, under the gate actions for its status and flags
(§7). Tier A adds one action of its own (the order decision, §7);
Tier B adds context and a badge only. Where a line is also short or
slippage-flagged, the precedence is: shortage handling first,
slippage second, watchlist last (§4.4).

### 5.5 The two-clock horizon model (Amendment B, 2026-11-06)

*Anahita's catch: everything in §§3–5 fires inside the current
event window — the six events start 14–49 days after the reference
date — but the long-lead parts in this dataset take 450–540 days.
For those parts a flag raised weeks before the event is not an
early warning; it is a last-minute alarm, because by then almost
nothing can still be done. These events are in reality planned
roughly 18 months ahead. Public sources checked in chat on
2026-11-06 support her: published guidance for booking a major
inspection is 9–12 months ahead, and no less than 6; industry
timelines put the material-and-logistics ordering phase at 6–4
months before the input; and reported lead times for the long-lead
engine parts themselves run 12–18+ months. The horizon model
therefore runs on two clocks, both code-computed from dates the
rule engine already produces:*

- **Clock 1 — the ORDER-BY clock (procurement warning).** Driven by
  the line's `order_by_date` (§2.3). For an uncovered or at-risk
  line (any non-OK status, or a covered line whose coverage depends
  on a PO), the states are: **advisory** — order-by date ≤ 6 months
  after the reference date, the order decision is coming and should
  be prepared; **act-now** — order-by date ≤ 3 months away, the
  order decision must be taken in this planning cycle; **escalated**
  — order-by date passed with no PO placed that counts for the
  line, which is the §5.2 Tier B population seen from the time
  side. Clock 1 answers: *"when does ordering stop being an
  option?"* Tier A's 21-day horizon (§5.2) is the innermost band of
  this clock, not a separate mechanism; the clock generalises it.
- **Clock 2 — the EVENT clock (coverage and customer warning).**
  Driven by days from the reference date to event start, and it
  applies only to lines **dependent on long-lead parts**, defined
  as `lead_time_days ≥ 180` (22 of the 33 current lines). At **6
  months** and again at **3 months** before event start, the tower
  re-checks the line's allocated coverage (§3), locks the
  allocation for that line (later events can no longer draw the
  pools it depends on ahead of it — the chronological policy, D1,
  applied as a reservation), and — only if the re-check finds a
  material risk (below) — raises the planner-facing
  at-risk advisory (§4.6 stage 1 applies if the re-check finds the
  line HIGH or short). Clock 2 answers: *"when do we stop being
  able to rearrange our way out of this?"*
- **Scheduled review is not an advisory (Refinement 2, adopted
  2026-11-06).** The 6- and 3-month Clock 2 points are **scheduled
  coverage reviews**, and they happen for *every* long-lead line
  (`lead_time_days ≥ 180`) regardless of its current coverage
  state — a covered position can deteriorate (a PO slips, a pool
  is drawn by an earlier event, an alternate lapses), and a review
  that only ran on already-flagged lines would miss exactly that.
  The review re-computes the allocated coverage, applies the
  allocation lock, and records that it ran. What it does **not**
  do, by itself, is raise anything: an **exception** or a
  **customer-risk advisory** is generated only when the review
  (or any other computation) finds the line in a **material risk
  condition**, defined from this spec's existing flags only:
  post-allocation `SHORT_UNCOVERED` or `INSUFFICIENT_DATA`;
  `CONTENDED_SHORT` (§3); `SLIPPAGE_HIGH` (§4.2); or counted-PO
  coverage with no ordering fallback (the Tier B condition,
  §5.2). A review that finds no material risk records the review
  and nothing else — no exception, no advisory, no customer
  contact. This is the §1 rule 8 separation applied to the event
  clock: the review is routine on the material-coverage
  dimension; the advisory belongs to the customer-impact
  dimension and must be earned by a risk condition.
- **What an early flag can and cannot buy, stated plainly.** An
  early flag buys: allocation lock-in before a competing event
  takes the pool; exchange / rotable sourcing, which runs on its
  own shorter market clock; schedule negotiation with the customer
  while dates can still move (§4.6, stage 1 at months, not days);
  and procurement decisions taken calmly (§5.2/Clock 1). An early
  flag does **not** buy a new order inside the lead time: at
  6 months before an event, a 540-day part is already
  unobtainable by ordering, and neither clock pretends otherwise.
  The early flags exist precisely because ordering is *not* the
  lever at that distance.
- **The two clocks are different instruments.** Clock 1 is about a
  decision deadline in the past-facing supply chain (place the
  order before the date arithmetic closes). Clock 2 is about a
  commitment deadline in the future-facing plan (reserve the
  coverage and warn the customer before rearrangement runs out).
  They share dates but no logic compares or merges them; a line
  carries both states independently, and Appendix A tests them
  separately, as built.

**Dataset consequence (see §9, amended).** All six current events
start within 49 days of the reference date, so on current data
Clock 2 is saturated: every long-lead line is already inside its
3-month advisory point and the clock cannot rank or prioritise
anything (Appendix A). Clock 2 can only be *demonstrated* on
events that are still 3–6+ months away. Amendment B therefore adds
**forward events (2027–28)** to the build as an additive dataset
extension (Stage V2-3B, §10; size per D5, **decided** 2026-11-06,
§12). The
existing 33 lines and V1 ground truth are untouched; forward events
exist for the horizon layer only.

### 5.6 Covered now ≠ covered without a decision (adopted 2026-11-06)

*The Appendix A test exposed a wording tension: Clock 1 was phrased
for "uncovered or at-risk" lines, yet one of its two act-now cases,
E006/P011, is fully OK. The refinement package resolves it as a
principle rather than leaving it a presentation choice:*

**An OK coverage verdict must not automatically suppress an
independently valid procurement action.** Coverage and procurement
readiness are separate dimensions (§1 rule 8): a line can be
covered for its event while the order that keeps the *next*
coverage possible is about to become impossible to place. E006/P011
is the canonical case — status OK, order-by date 2026-11-21 inside
the act-now band (Tier A, §5.2), a genuine and losable order
decision sitting on a green line.

**But a procurement action on a covered line requires a documented
outstanding procurement need.** The system must establish *why* the
purchase is needed before the action is raised — one or more of:
the stock covering this line is allocated to it but cannot be
replenished inside the horizon once consumed; the pool it draws on
is shared and is drawn by later events as well; or the quantity is
committed elsewhere in the plan. If no such need can be documented
from the computed data, no procurement action is raised: the line
is simply covered, and its Clock 1 state is procurement context
only (Appendix A). The distinction the system must hold is
**"covered now" versus "requires a procurement commitment to
remain covered"** — the first is a coverage verdict, the second
is a procurement decision, and neither may be silently read off
the other. For E006/P011 the need is documented in the data: the
P011 pool is shared across three events with aggregate demand
above the pool (§3.3), so this line's position depends on stock
that later events also claim and that cannot be re-ordered inside
the window once the order-by date passes. Scenario P01 (§6.2)
tests this rule explicitly.

---

## 6. Evaluation — new ground-truth scenarios

### 6.1 Method (same discipline as V1)

- Scenarios are written to a **new file**, `data/eval_scenarios_v2.csv`,
  in the V1 column shape extended with the expected V2 fields
  (expected allocated status/shortage, expected slippage tier,
  expected watchlist tier). `data/eval_scenarios.csv` is not modified.
- A pure-code validator recomputes every expected value from the raw
  tables using §§3–5 and must score **in full — every scenario in
  the set, 20 new scenarios as decided under D3 (§12) — before
  any agent run**.
  Writing the scenario before the recomputation is what makes it
  ground truth rather than a description of whatever the code does;
  any disagreement is resolved by re-reading this spec, on the record,
  exactly as V1's Stage 1 validation caught its design error.
- The agent evaluation then scores **exact-match** per scenario on the
  fields that scenario tests (allocated status + shortage; slippage
  tier; watchlist tier), reported separately from the V1 score.
  V1's 10 scenarios are re-run unchanged as a regression set.
- **Evaluation size is decided under D3 (§12, 2026-11-06): the
  full set.** The 16 scenarios below (C/R/W) are the core set;
  the adopted refinement package (2026-11-06) adds the P and X
  classes beneath them (P01, X01, X02a, X02b). The final count,
  verified against the tables in §6.2, is **20 new scenarios,
  30 total** alongside the 10 V1 regression scenarios.

### 6.2 The V2 set (20 new scenarios — decided under D3)

**Competing demand (C01–C06):**

| ID | Line | Expected (allocated view) | Trap / purpose |
|---|---|---|---|
| C01 | E003/P001 | SHORT_UNCOVERED, short 1 (V1: OK) | Phantom stock: one physical unit counted by two events (§3.3). Depends on the partial-allocation assumption, stated in the rationale. |
| C02 | E006/P016 | SHORT_UNCOVERED, short 3 (V1: COVERED_BY_TRANSFER) | Phantom transfer: the same network stock promised to two events. |
| C03 | E006/P011 | SHORT_UNCOVERED, short 3 (V1: OK) | Three-event contention; aggregate demand (17) exceeds the total pool (14) — no per-line view can see this. |
| C04 | E006/P006 | SHORT_UNCOVERED, short 1 (V1: OK) | Phantom PO + stock: PO-1011's balance and YYZ stock both double-counted. |
| C05 | E005/P005 | COVERED_BY_TRANSFER, short 0 (V1: OK) | Reverse trap: contention is real but absorbed by the network. Contention ≠ shortage; an agent that flags every contended line fails this. |
| C06 | E002/P016 | COVERED_BY_TRANSFER, short 0 (= V1) | Control: the first event in priority order is unaffected by allocation. Guards against an engine that shifts everyone's verdict. |

**PO slippage risk (R01–R05):**

| ID | Line | Expected tier | Trap / purpose |
|---|---|---|---|
| R01 | E001/P002 | SLIPPAGE_HIGH | Margin (4d) smaller than observed slip (7d); load-bearing PO. |
| R02 | E002/P006 | SLIPPAGE_HIGH | Margin 3d vs slip 5d; the tightest margin in the data. |
| R03 | E002/P015 | SLIPPAGE_WATCH | Slipped PO (7d) that does *not* break on a repeat (margin 11d). A slipped PO is not automatically a risk. |
| R04 | E005/P002 | *(no flag)* | Same PO as R01, margin 32d. Risk belongs to the line, not the PO; flagging the PO globally fails this. |
| R05 | E004/P021 | *(no flag)* | A counted PO that is not load-bearing (line is OK from stock). Presence of a PO ≠ dependence on it. *(Annotation, 2026-11-06: expectation unchanged under the decided 21-day watch threshold (D2) — margin 19 is now inside the watch band, so R05 also traps margin-only flagging; the load-bearing condition is what excludes it.)* |

**Watchlist (W01–W05):**

| ID | Line | Expected tier | Trap / purpose |
|---|---|---|---|
| W01 | E004/P011 | ORDER_BY_CLOSING | Order-by 2026-11-07 — 5 days after the reference date. The window is open and about to close. |
| W02 | E006/P011 | ORDER_BY_CLOSING | Order-by 2026-11-21; also a contended part (C03). One line, two lenses, one decision (§5.4). |
| W03 | E001/P005 | *(not listed)* | The noise trap: order-by passed (2026-10-02) but status OK with 20 units on site. Listing it fails this scenario. Stands for the 18 excluded OK lines. |
| W04 | E001/P001 | NO_ORDERING_FALLBACK | Passed order-by on a SHORT_UNCOVERED AOG line: no ordering remedy exists inside the window (lead 540 days). |
| W05 | E003/P003 | NO_ORDERING_FALLBACK | The covered-line case (§5.3): COVERED_BY_ALTERNATE, order-by passed — covered by a plan, with no ordering fallback if the plan fails. |

**Procurement action on a covered line (P01 — adopted 2026-11-06, §5.6):**

| ID | Line | Expected | Trap / purpose |
|---|---|---|---|
| P01 | E006/P011 | Status OK (single-line view); watchlist ORDER_BY_CLOSING (order-by 2026-11-21, act-now); **procurement action raised with its documented need** (shared P011 pool, aggregate demand above the pool, not replenishable inside the horizon — §5.6); **no shortage raised for this line** | Dimension separation, both directions: an agent that stays silent because the line is OK fails (the losable order decision is missed); an agent that reports a material shortage for this line fails (the allocated-view shortage question for P011 is C03's, and conflating a procurement decision with a shortage is the error §5.6 exists to prevent). |

**Recovery options unavailable (X01 — adopted class, 2026-11-06):**

| ID | Line | Expected | Trap / purpose |
|---|---|---|---|
| X01 | *(slot — to be instantiated in `eval_scenarios_v2.csv`, on a current short line or a forward-extension line)* | A SHORT_UNCOVERED / SLIPPAGE_HIGH line on which **every** recovery lever is infeasible on the computed facts: expedite cannot arrive inside the window (lead time vs margin), no exchange / rotable source exists, no transfer pool remains after allocation, and the check cannot be re-sequenced around the part. Expected behaviour: the agent states that no feasible recovery exists, and its only recommendations are **Escalate — defer event** and the §4.6 prepared-notification path | Tests the failure mode the other classes cannot: inventing a recovery. An agent that proposes any infeasible lever, or softens the answer into monitoring, fails. "No feasible recovery" must be an output the system can honestly produce. |

**Customer-risk escalation (X02 — adopted class, 2026-11-06):**

| ID | Line | Expected | Trap / purpose |
|---|---|---|---|
| X02a | *(slot — a line in a material risk condition, §5.5)* | Internal material risk that **crosses into customer impact**: expected behaviour is the §4.6 path — a prepared draft notification, checkpoint date, recorded recovery path, and the four pre-release verifications named as outstanding for the human approver | Tests the coverage-risk → customer-impact crossing (§1 rule 8): the agent must move dimensions deliberately, with the governance attached, not merely repeat the internal flag louder. |
| X02b | *(slot — a near-identical internal-risk line that stays internal: e.g. SLIPPAGE_WATCH, or a Tier B context-only line)* | **No customer escalation**: internal handling only (monitor / expedite decision as specced), no draft notification prepared, no advisory raised | The paired control. Escalating X02b to the customer fails this scenario exactly as failing to escalate X02a does — the class tests the boundary, not a tendency to escalate. |

### 6.3 Coverage check

Every V2 output class is exercised at least twice: contended-short
(C01–C04), contended-covered (C05, C06), HIGH (R01, R02), WATCH (R03),
correctly-unflagged (R04, R05, W03), both watchlist tiers (W01/W02,
W04/W05). Both "no flag" traps (R04, W03) target the known failure
mode of exception systems — over-flagging — which V1's retrieval
abstention work already showed is a real risk in this codebase.
The adopted classes add the dimension-separation tests: a valid
procurement decision on a green line (P01), an honest
no-recovery output (X01), and the customer-escalation boundary
tested from both sides (X02a/X02b). Under D3 as decided
(2026-11-06) the final set carries **all** of these slots:
20 new scenarios, 30 total with the V1 regression set.

---

## 7. Gate actions — fixed decision model, extended

Decision values are those already implemented by the 6 Nov 2026 gate
fix (planner + `app/planner.py` server-side validation). V2 adds values
only where a genuinely new decision exists; it removes none, and it
introduces **no Accept-style action for any short, unknown, or
high-risk line**. Every line also offers **Send back for review**, as
in V1. Undo/change works as in V1. The server must reject any decision
value not allowed for the line's combined (status, flags) state —
extending the validation the gate fix already performs.

| Line state (allocated view governs where it differs) | Allowed decisions |
|---|---|
| OK, no flags | Acknowledge — no action |
| COVERED_BY_PO / COVERED_BY_TRANSFER / COVERED_BY_ALTERNATE, no flags | Approve — monitor PO / Approve transfer / Approve alternate use (as V1, per status) |
| CONTENDED_COVERED (any covered status, sourcing changed by allocation) | The status action above, recorded against the allocated view; the decision record names the covering pools the allocation assigned |
| CONTENDED_SHORT, or SHORT_UNCOVERED in either view | Escalate — expedite / emergency source, **or** Escalate — defer event, **or** Notify customer — at risk (§4.6; checkpoint date = event start). No approve/accept exists. |
| INSUFFICIENT_DATA (either view) | Escalate — investigate / physical count |
| Covered line + SLIPPAGE_HIGH | Escalate — expedite / chase PO confirmation, **or** Notify customer — at risk (§4.6; checkpoint date = the counted PO's expected arrival date), **or** Send back for review. "Approve — monitor PO" is *not* offered: passively monitoring a PO whose repeat slip breaks coverage is the V1 error in a new form. |
| Covered line + SLIPPAGE_WATCH | Approve — monitor PO (as V1), with the watch flag recorded in the decision record; **or** Escalate — expedite / chase PO confirmation. No customer notification at this tier — internal only (§4.6). |
| Watchlist Tier A (ORDER_BY_CLOSING), line otherwise covered | Decide: place the order (recorded as the human's decision; the system places nothing — read-only rule) **or** Acknowledge — let the window lapse. Both are real decisions; neither is a default. |
| Watchlist Tier B (NO_ORDERING_FALLBACK) | No action of its own. The line is decided under its status row above; the tier is shown as context on the decision card. |

Precedence when several rows apply: shortage rows first, then
SLIPPAGE_HIGH, then Tier A, then the plain status row (§5.4).

**Recovery path (Amendment A).** Every decision on a HIGH line
(SLIPPAGE_HIGH or CONTENDED_SHORT) records a recovery path —
expedite / chase PO, exchange / rotable, transfer under allocation,
re-sequence the check, or defer — as a named field in the decision
record; a decision record without it is invalid and the planner
must reject it server-side. The notification decision and the
recovery decision are separate fields: a planner may notify the
customer *and* choose expedite, or choose expedite without
notifying — the record must say which, for each. No customer
message is ever sent by the system; "Notify customer" records a
human's decision to notify, exactly as the Tier A order decision
records a decision to order (§11, read-only rule unchanged).
Recording that decision as **released** additionally requires the
four pre-release verifications of §4.6 (affected event, material
shortfall, recovery options, the communication itself) in the
decision record; without them the decision is incomplete and the
planner must reject it server-side.

**Procurement action on a covered line (adopted 2026-11-06,
§5.6).** Where a covered line (including status OK) carries a
Clock 1 act-now state *and* a documented outstanding procurement
need (§5.6), the Tier A order decision above is a real decision
on the procurement dimension and is offered in its own right —
the line's coverage verdict does not remove it. The decision
record must name the documented need; a "place the order"
decision recorded without one is invalid server-side, and the
only other outcome is **Acknowledge — let the window lapse**,
also recorded. The agent presents such an action as a procurement
decision with its reason, never as a shortage: on the coverage
dimension the line remains whatever its verdict says it is.

---

## 8. UI surfaces

All additions use the existing design system: the dashboard/planner
colour system, the teal `Control Tower` headers, the existing status
chips and card layout. No new palette, no new page furniture for its
own sake. No figure appears in any UI unless the monitoring summary
(Stage V2-6) computed it from code output.

**Planner (`docs/planner.html` + `app/planner.py`, kept in step):**
- Per-part **allocation view**: for each contended part, a pool ledger
  card — pool quantities per source, which event drew what, what
  remains — with each line showing V1 status and allocated status side
  by side and a contention badge (`CONTENDED_SHORT` /
  `CONTENDED_COVERED`) where applicable. The allocation policy in
  force is named on the view (e.g. "Allocation: chronological by
  event start") and stored in every decision record made from it.
- **Slippage badges** on covered lines: HIGH and WATCH chips in the
  existing status-chip style, showing margin and slip day-counts
  (tool-provided numbers only).
- **Watchlist view**: two sections, "Order-by closing" (Tier A, with
  days remaining per line) and "No ordering fallback" (Tier B),
  each line linking to its single decision card (§5.4).
- **Horizon view** (Amendment B): the forward events on a timeline
  against the pinned reference date, each long-lead line showing
  its Clock 1 and Clock 2 states (§5.5) as separate chips — the two
  clocks are never merged into one indicator. HIGH decision cards
  show the checkpoint date and the recorded recovery path (§4.6).
- Gate counts extended, not replaced: pending / decided / escalated
  remain; escalated includes the new escalation decision values.
- Start state is clean: no V2 decisions pre-recorded.

**Dashboard (`docs/dashboard.html`):**
- One new section, "Cross-event & risk (V2)", reporting only
  code-computed figures: 10 contended parts; 6 lines whose status
  changes under allocation, of which 4 flip to short; slippage flags
  2 HIGH / 1 WATCH across 6 PO-counted lines; watchlist 2 act-now /
  13 no-fallback of 33 lines; and the V2 evaluation score once
  Stage V2-5 has run (shown as "not yet run" until then — never
  pre-filled).
- The V1 figures (10/10, 25 runs, US$0.27, 33 lines, gate counts)
  remain, labelled as the V1 single-line view where confusion is
  possible.

**Monitoring (`monitoring/summarize_runs.py` / `summary.md`):**
extended with the V2 layer counts and the V2 evaluation score, in the
same format as the existing sections; V1 sections unchanged.

---

## 9. Dataset impact

**No dataset change is required for V2. Dataset stays at v1.1.**
Per exception type:

- **Competing demand:** fully supported by current data. Contention
  already exists (10 parts, 22 lines) and produces 4 covered→short
  flips and 2 sourcing changes (§3.3). Inventing *more* contention
  would add nothing the evaluation needs.
- **PO slippage risk:** fully supported. promised_date and
  expected_date exist on all 14 POs; the 6 counted (line, PO) pairs
  exercise HIGH, WATCH and correctly-unflagged outcomes (§4.2).
  Honest limitation: the tier boundaries rest on few cases — margins
  among counted pairs are 3, 4, 11, 19, 31, 32 days. Under the
  decided 21-day watch threshold (D2, §12) two counted pairs sit
  inside the band — E002/P015 at 11 (flagged WATCH) and E004/P021
  at 19 (inside the band on margin, but excluded by the
  load-bearing condition, §4.2). The evaluation proves the rule
  as defined; it does not prove the threshold is the right one
  for real operations, and the spec does not claim otherwise.
- **Watchlist:** fully supported. `lead_time_check` already computes
  every field the inclusion rule uses.

Changing the data (a "v1.2") was considered and is **not**
recommended as part of V2: any change to demand, inventory or PO
dates risks moving V1 verdicts and would force re-validation of the
published ground truth, destroying the clean V1/V2 comparison that
makes the allocated view meaningful. If richer slippage margins are
ever wanted, that is a separate dataset decision, taken on its own,
with full re-validation — it is not smuggled into this build.

One file *is* added, and it is not a data change to the existing
tables: `data/eval_scenarios_v2.csv` (§6.1) — new ground truth for
the new layer, written before the agent runs, validated by code.

**Amendment B exception (2026-11-06) — the horizon layer only.**
The "no dataset change" conclusion above stands for §§3–5 as
originally specced, but Amendment B (§5.5) reverses it for the
horizon layer alone: Clock 2 cannot be demonstrated on events that
all start within 49 days of the reference date, so the build adds
**forward events in 2027–28** as a purely additive extension —
new rows in `maintenance_schedule` and `demand` (and any inventory
or PO rows those events genuinely need), authored by the same
deterministic generator discipline as v1.0/v1.1, with their own
ground truth written before any agent run. The extension must not
touch any existing row: the existing 33 lines, their verdicts and
V1's published ground truth are byte-identical before and after
(regression-gated at Stage V2-3B). This is still not a "v1.2" of
the existing dataset — it is a horizon annex beside it, and it
does not reopen the slippage-margin question discussed above.
The size of the extension is per D5 — **decided 2026-11-06**
(§12): 3 forward events, subject to the state-and-interaction
coverage criterion recorded there.

---

## 10. Build stages (dependency order; each stage has a hard gate)

| Stage | Work | Verification gate (must pass before the next stage) |
|---|---|---|
| **V2-0** | Ground truth first. Write `data/eval_scenarios_v2.csv` (20 scenarios, §6.2 as decided under D3 — the 16 core plus P01, X01, X02a, X02b) with full rationales; write the pure-code recomputation (allocation, tiers, watchlist) as a standalone validator. | Validator reproduces 20/20 expected values from the raw tables; validator also reproduces the §3.3 worked table and the §4.2/§5.2 counts. All §12 decisions settled and recorded (done 2026-11-06). No agent runs yet. |
| **V2-1** | Allocation engine in the rule-engine layer: pools, priority policy as a parameter, per-line allocated verdict + pool ledger. New module beside `check_availability`; **V1 function untouched**. | Unit tests cover all 10 contended parts and both worked flips C01–C06; regression: `validate_dataset.py` still 10/10, `app/test_tools.py` still 13/13, and V1 verdicts for all 33 lines byte-identical to the published `planner_data.json`. |
| **V2-2** | Slippage module: `po_detail` gains promised_date, slip_days, margin_days, load_bearing (§4.5); tier classifier (§4.2); precedence vs allocation (§4.4). | Tests reproduce R01–R05 exactly from data, including both no-flag traps; same V1 regression gates as V2-1 (additive output must not move any verdict). |
| **V2-3** | Watchlist module: Tier A / Tier B inclusion rule (§5.2) as code. | Tests reproduce the 2 / 13 / 18 split (Tier A / Tier B / excluded-with-passed-order-by) exactly; W01–W05 pass. |
| **V2-3B** | Horizon layer (Amendments A+B): forward-event dataset extension (§9, size per D5) with its own ground truth; two-clock computation (§5.5) as a rule-engine module; notification checkpoint dates and recovery-path field in the decision record (§4.6). Existing rows and verdicts untouched. | Forward events place at least one long-lead line in every Clock 1 band (advisory / act-now / passed) and every Clock 2 band (≤6mo / ≤3mo advisories); D5's interaction cases (§12) are present: at least one line that is Clock 1 advisory or act-now while covered on Clock 2, and at least one covered-now line carrying a Clock 1 act-now procurement action under §5.6 — the gate fails if either interaction case is absent; regression: V1 verdicts for all 33 existing lines byte-identical, `validate_dataset.py` 10/10, Tier A reproduction (2 lines) unchanged on the existing data. |
| **V2-4** | Agent layer: four new read-only tools (allocated availability, slippage risk, watchlist, horizon) alongside the existing five; agent prompt extended — numbers only from tools, per standing rule 3; citation-retry validation extended to the new policy-driven outputs (CONTENDED_SHORT, SLIPPAGE_HIGH, Tier A, horizon advisories). | Tool-layer tests for the new tools pass; a dry inspection shows no path by which the agent can state an allocated status, tier or day-count that a tool did not return. |
| **V2-5** | Evaluation run: agent runs the 20 V2 scenarios; the 10 V1 scenarios re-run as regression (30 total). Results written up in the evaluation report as a V2 addendum, misses included, same honesty standard as Stage 5/6. | Scores are whatever they are — the gate is that the run happened, was scored exact-match, and is written up, not that it passes. Any miss is analysed before V2-6 proceeds. |
| **V2-6** | UI + monitoring: planner allocation view, slippage badges, watchlist view (§8); dashboard V2 section; monitoring summary extension; V2 planner data written to its own file (V1 `planner_data.json` untouched). | Rendered-page check against §8: both statuses shown per line, counts match code output, gate offers exactly the §7 actions per line state (spot-checked on one line of each row, including one CONTENDED_SHORT and one SLIPPAGE_HIGH line), start state 0 decisions. |
| **V2-7** | Documentation close-out: roadmap gains a V2 section in the Stage 5/6 style (including anything that went wrong); README/dataset-card changelog updated locally. | Docs match the built behaviour — verified by re-reading them against the Stage V2-6 outputs, not from memory. **Publication is NOT part of this stage** (§11, out of scope). |

**API cost estimate (basis: V1 actuals, same model
`claude-haiku-4-5`).** V1 history: 25 logged runs ≈ US$0.27 total
(≈ US$0.011 per run); a full 10-scenario evaluation ≈ US$0.10–0.12.
V2 planning figures, extrapolated at the same per-scenario cost:
one full V2 evaluation (30 scenarios) ≈ US$0.33; development
across V2-4/V2-5 at roughly three full evaluations plus ~30
individual dev/retest runs ≈ US$0.75–1.00 total. These are estimates
from V1's measured costs, not quotes. Known constraint from the
roadmap: the current Anthropic key expires ~1 Dec 2026 — Stages
V2-4/V2-5 (the only API-spending stages) must land before then or
wait for a renewed key.

---

## 11. Out of scope

- **V3 what-if planner** (moving event dates, cancelling POs, adding
  emergency orders and recomputing): not part of this build, in any
  stage. The allocation policy parameter (Stage V2-1) is a policy
  *selection*, not a what-if tool, and must not grow into one.
- **No V1 verdict changes.** Not the evaluation, not
  `planner_data.json`, not any published status — for any reason
  found during V2. A V1 error, if one surfaces, is documented, not
  edited.
- **No publishing without Anahita's explicit go-ahead.** Completing
  V2-7 does not publish anything: not GitHub, not GitHub Pages, not
  Hugging Face, not LinkedIn. Publication is a separate instruction.
- **No dataset v1.2** (§9) and no changes to the pinned reference
  date. *(Amended 2026-11-06: forward events in 2027–28, added by
  Amendment B as a purely additive annex for the horizon layer,
  are in scope — §9, Stage V2-3B, D5. New sites/parts and any edit
  to an existing row remain out of scope.)*
- **No write actions, ever.** The order decision in §7 records a
  human decision; the system places no order, sends no message, and
  changes no data. Read-only is a standing rule, not a V1 limitation.
- **Transfer transit time is not modelled.** Knowledge note N03 says
  an inter-site transfer takes 2 working days; the V1 rule counts
  network stock without a transit check, and V2's allocation inherits
  that simplification unchanged. Modelling it would change V1
  verdicts (out of scope above) — it is recorded here as a known,
  deliberate non-goal for a future version to argue about.

---

## 12. Decisions for Anahita (5) — all five decided 2026-11-06

*Sequencing note (2026-11-06): all five decisions are now
decided (below). D2, D3 and D4 were each decided
**individually, on their own operational implications** — not
adopted as a group and not carried by any other package. The
refinement package adopted 2026-11-06 (§1 rule 8, §4.6, §5.5,
§5.6, §6.2) expressly did not decide D2–D4; D2 was then decided
individually the same day, D3 likewise shortly after, and D4
last, also on its own — exactly as this note required while
they were open. Each decision below retains its original
options and recommendation as history.*

**D1 — Allocation priority policy (§3.2, §3.5).**
**DECIDED 2026-11-06: Anahita agreed — (a) chronological.**
Options: (a) chronological by event start, tie-break event_id;
(b) criticality-weighted.
**Recommendation: (a) chronological.** Criticality is a property of
the part, and competing lines share the part, so (b) cannot order
them as pitched; the derived event-level version ties almost
everywhere on current data and falls back to (a) anyway. Chronological
also matches physical picking order. The partial-allocation-retained
assumption (§3.2) is part of this decision: approving (a) approves
that assumption, which C01's ground truth depends on.

**D2 — Slippage watch threshold (§4.2).**
**DECIDED 2026-11-06: Anahita chose 21 — WATCH_MARGIN_DAYS = 21
days** — over the recommended 14.
**Her stated rationale (2026-11-06, recorded as the operational
basis for the decision):** she is a supply chain person, and
3 weeks is the minimum realistic window to react to a slipping
PO — chase the supplier, decide an expedite, line up an
alternate. A 14-day watch fires too late for those actions to
be real options; the flag has to arrive while something can
still be done about it. The threshold is therefore set by the
reaction time the flag is meant to buy, not by the tightness
of the current data.
Recomputed from the data at the decided value (code, pinned
reference date 2026-11-02): the flagged set is unchanged from
14 days — **2 HIGH** (E001/P002, margin 4; E002/P006, margin 3;
the HIGH tier does not move, as stated below) and **1 WATCH**
(E002/P015, margin 11). The one pair the wider band newly
reaches on margin alone, E004/P021 (margin 19), remains
unflagged because PO-1012 is not load-bearing (§4.2
recomputation note); the 21-day band binds on future data.
Options: WATCH_MARGIN_DAYS of 7, 14 or 21 days (the HIGH tier is
defined by the repeat-slip test and does not move).
**Recommendation was: 14.** At 7, E002/P015 (margin 11, slip 7 — a PO that
has already slipped a week, landing 11 days before a C-check) draws no
flag at all, which under-reports the one genuinely tight-but-holding
case in the data. At 21, E004/P021's non-load-bearing PO still draws
no flag (the load-bearing condition protects it), so 21 buys nothing
except wider flags on future data. 14 flags exactly the lines a
planner would want to see.

**D3 — Evaluation size (§6).**
**DECIDED 2026-11-06: Anahita chose the full set — 20 new
scenarios, 30 total.** The full set as constituted after the
adopted refinement package: the 16 core scenarios (C01–C06,
R01–R05, W01–W05) plus P01, X01, X02a and X02b = **20 new**;
with the 10 V1 scenarios re-run unchanged as regression,
**30 total**. The count is verified against the tables in §6.2.
Options as originally put: (a) 16 new scenarios, 26 total; (b) a reduced set of 9 new
(one per trap class), 19 total; (c) extend beyond 16 (e.g. a scenario
for every contended part, 20+ new).
**Recommendation was: (a) 16 / 26** (the core set; the decided
full set adds the adopted P/X classes on top of it). Every output class and both no-flag
traps are covered at least twice; (b) leaves classes single-tested,
which V1's experience (citation instability between runs) argues
against; (c) spends agent runs re-proving the same rules on parts
whose allocation is already covered by the pure-code validator.
Cost consequence is small either way (≈ US$0.26–0.31 per full run
at 26, rising only slightly at the decided 30; §10 (build stages)).

**D4 — Watchlist inclusion shape (§5.2).**
**DECIDED 2026-11-06: Anahita chose (a) — the two-tier rule as
specced (Tier A 2 lines + Tier B 13 lines = 15 of 33 lines).**
Options as originally put: (a) the two-tier rule as specced (Tier A act-now + Tier B
no-fallback for non-OK lines; OK lines excluded) — 15 of 33 lines;
(b) Tier A only — 2 lines, the watchlist as a pure "order now" list;
(c) the naive rule — every passed order-by line, 31 of 33.
**Recommendation was: (a).** (c) is a data dump, not an exception surface.
(b) is defensible but throws away the Tier B signal — "this coverage
is a plan, and there is no ordering fallback behind it" — which is
the half of the watchlist a control tower actually exists to say.
Under (a) Tier B lines carry no extra decision (§5.4), so the wider
list costs attention only where it is labelled as context.

**D5 — Forward-event extension size (§5.5, §9 — added by
Amendment B, 2026-11-06).**
**DECIDED 2026-11-06: Anahita adopted (a) — 3 forward events,
roughly 5, 11 and 20 months after the reference date — as part of
the adopted refinement package, WITH a stricter acceptance
criterion than the option as first worded.** Sufficiency is
conditional, not automatic: the demand lines the 3 events generate
must exercise **every band of both clocks** (Clock 1: advisory /
act-now / passed-escalated; Clock 2: the 6-month and 3-month
review points) **and their interactions** — at minimum, a line in
a Clock 1 advisory or act-now state while covered on Clock 2, and
a covered-now line carrying a Clock 1 act-now procurement action
under the §5.6 rule — and the Stage V2-3B test coverage must
confirm that they do. **If the 3 events cannot populate all
states and interactions, the extension grows until they do**;
"3 events" is the adopted starting size, not a cap that may leave
a clock state untested.
Options as originally put: (a) minimal demonstration set — **3 forward events**,
roughly 5, 11 and 20 months after the reference date, with
long-lead demand lines chosen so that every band of both clocks
has at least one line in it; (b) a fuller planning board — **6
forward events** spread across 2027–28 (roughly quarterly),
which reads as a real forward schedule rather than a test fixture;
(c) a full rolling 18-month schedule — 10–12 forward events,
closest to reality, at the largest ground-truth and validator cost.
**Recommendation: (a) 3 events.** The horizon layer's ground truth
is date arithmetic, fully proved by the pure-code validator; the
extension exists to put lines into clock bands the current data
cannot reach (Appendix A), and 3 well-placed events do that.
(b)'s extra events add authoring and validation burden without
testing any new rule, and the annex can grow later without
re-validating V1 — growth is cheap, so start minimal. If the
forward board is ever shown publicly as a schedule in its own
right (rather than as the horizon layer's fixture), revisit in
favour of (b).

---

## Appendix A — Two-clock test on current data (2026-11-06)

*Amendments A and B were tested against the current dataset before
being written in — same discipline as §2: every number below was
computed from `data/*.csv` by a throwaway script (not part of the
project file set), using the `_lead_time_check` rule
(`order_by_date = event start − lead_time_days`, §2.3) and the
project's own classifier for V1 status, at the pinned reference
date 2026-11-02. Bands are calendar months from the reference date:
act-now ≤ 2027-02-02, advisory ≤ 2027-05-02.*

**Hand-check (P001, the longest lead).** P001 lead time is 540 days;
E001 starts 2026-11-16. Order-by = 2026-11-16 − 540 days:
2026-11-16 − 365 = 2025-11-16; − 175 more days = **2025-05-25**.
Cross-check by the day-count identity: days-to-order-by =
days-to-event − lead = 14 − 540 = **−526**, and 2025-05-25 is
indeed 526 days before 2026-11-02. ✓ The script reproduces both.
(E003/P001: start 2026-11-30 − 540 = 2025-06-08, −512. ✓)

**Clock 1 (ORDER-BY) — bands over all 33 lines:**

| Band | Lines | Of which non-OK |
|---|---|---|
| passed (order-by < 2026-11-02) | 31 | 13 |
| act-now (≤ 3 months away) | 2 | 1 |
| advisory (3–6 months away) | 0 | 0 |
| far (> 6 months away) | 0 | 0 |

The 2 act-now lines are exactly §5.2's Tier A cases — **E004/P011
(order-by 2026-11-07, +5 days, COVERED_BY_TRANSFER)** and
**E006/P011 (order-by 2026-11-21, +19 days, OK)** — so the clock
reproduces Tier A as its innermost band, as §5.5 claims. The 13
passed-and-non-OK lines are exactly the §5.2 Tier B population
(13), seen from the time side: Clock 1's "escalated" state and
Tier B are the same set on current data, which cross-validates
both computations. One wording tension the test exposed:
Amendment B phrases Clock 1 for "uncovered or at-risk" lines, but
E006/P011 is fully OK and still carries a real order decision
(Tier A includes it). The clock *band* reproduces for all lines
regardless of status; whether an OK line's act-now state raises a
planner flag or is shown as procurement context only is left to
a D4/D5 implementation detail — the spec did not silently
drop the line. *(Resolved 2026-11-06 by the adopted refinement
package: §5.6 states the rule — an OK verdict does not suppress
a documented procurement action — and scenario P01, §6.2, tests
this line explicitly.)*

**Clock 2 (EVENT) — bands over all 33 lines:**

| Band | Lines | Of which long-lead (≥ 180 d) |
|---|---|---|
| ≤ 3 months to event start | 33 | 22 |
| 3–6 months | 0 | 0 |
| > 6 months | 0 | 0 |

All six events start 14–49 days after the reference date (E001
+14 … E006 +49), so **Clock 2 flags everything and discriminates
nothing on current data**: its advisory bands are empty, and
inside the innermost band it cannot rank a 540-day turbine blade
line against a 30-day consumable. This is the demonstration limit,
stated plainly: Clock 2 as specced is *untestable* on the current
dataset — not because the rule is wrong, but because the dataset's
horizon (49 days) is an order of magnitude shorter than the lead
times it is meant to watch (up to 540 days). That emptiness is the
evidence for the forward-event extension (D5): the bands only
become real when events exist 3–6+ months out.

**Which clock is which (the question the test was run to answer):**

- **Clock 1 does the procurement warning**, and it works today:
  it separates the 2 lines where an order decision is still
  losable from the 31 where that door has closed, and within the
  closed set it separates the 13 non-OK lines (no fallback behind
  a live coverage plan — Tier B) from the 18 OK lines (stock on
  the shelf; the passed date is a replenishment fact, §5.3).
- **Clock 2 does the coverage and customer warning** — re-check,
  allocation lock, at-risk advisory (§4.6) — and on current data
  it can only say "everything is near", because everything is.
  Its value is entirely in the forward schedule.
- **Where they agree:** for the 13 passed-and-non-OK lines, both
  clocks say "late" — but they mean different things by it.
  Clock 1 says the *ordering* remedy closed, in most cases over a
  year ago (P001's order-by dates are in May–June 2025). Clock 2
  says the *rearrangement* remedy is closing now. A line needs
  both readings: the first kills false hope of ordering a fix,
  the second is what triggers allocation lock and the customer
  advisory.
- **Where they diverge:** the 2 act-now Clock 1 lines sit at
  +35/+49 days on Clock 2 — unremarkable there — while Clock 1
  picks them out of all 33 lines as the only live procurement
  decisions. Conversely the 22 long-lead lines are
  indistinguishable on Clock 2 today (all ≤ 3 months) but split
  22/0 on Clock 1 (all passed). Neither clock approximates the
  other; that is why there are two.

---

*End of spec. All five decisions in §12 were settled 2026-11-06;
the spec is fully decided and ready for build. Stage V2-0 (ground
truth) starts only on Anahita's build go-ahead; nothing has been
built or published yet.*
