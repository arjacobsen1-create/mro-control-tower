#!/usr/bin/env python3
"""
Synthetic MRO dataset generator — Project 55, MRO Supply Chain Control Tower.

100% synthetic and hypothetical. No client, employer, or real operational data.
Deterministic: hand-specified core data (so the eval scenarios are exact) plus
seeded filler (seed = 55). Run: python3 generate_dataset.py
Writes CSVs into ./data/
Reference date ("as of") for the whole dataset: 2026-11-02.
"""
import csv, os, random

OUT = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data")
os.makedirs(OUT, exist_ok=True)
rng = random.Random(55)

SITES = ["YUL-H1", "YYZ-H2", "YYC-H3"]  # fictional hangars: Montreal, Toronto, Calgary

# ---------------------------------------------------------------- parts
# part_id, part_number, description, ata, criticality, lead_days, unit_cost, alternate, supplier
PARTS = [
    ("P001","MRO-72-1001","Turbine blade set, stage 1","72","AOG",540,18400,"","AeroForge Ltd"),
    ("P002","MRO-72-1002","HPT seal kit","72","HIGH",450,3200,"","AeroForge Ltd"),
    ("P003","MRO-73-1003","Fuel nozzle set","73","HIGH",540,5600,"P023","NordJet Components"),
    ("P004","MRO-72-1004","Main shaft bearing set","72","AOG",540,9100,"","Precision Bearings Co"),
    ("P005","MRO-79-1005","Oil filter element","79","ROUTINE",45,180,"","FilterWorks"),
    ("P006","MRO-74-1006","Igniter plug","74","HIGH",270,640,"","SparkLine Aviation"),
    ("P007","MRO-73-1007","Engine fuel pump","73","AOG",365,12750,"","NordJet Components"),
    ("P008","MRO-77-1008","EGT temperature sensor","77","HIGH",240,890,"","ThermoSense Inc"),
    ("P009","MRO-72-1009","Compressor gasket kit","72","ROUTINE",180,420,"","SealRight"),
    ("P010","MRO-36-1010","Bleed valve actuator","36","HIGH",270,4700,"","PneuDyne"),
    ("P011","MRO-29-1011","Hydraulic filter element","29","ROUTINE",30,240,"","FilterWorks"),
    ("P012","MRO-80-1012","Starter motor","80","HIGH",300,6800,"","StartGen"),
    ("P013","MRO-24-1013","Generator drive seal","24","ROUTINE",90,310,"","SealRight"),
    ("P014","MRO-49-1014","APU fuel control unit","49","HIGH",365,9900,"","NordJet Components"),
    ("P015","MRO-32-1015","Landing gear seal kit","32","ROUTINE",120,1150,"","SealRight"),
    ("P016","MRO-32-1016","Steel brake unit","32","HIGH",210,7300,"","BrakeSystems Intl"),
    ("P017","MRO-21-1017","Cabin pressure sensor","21","ROUTINE",120,760,"","ThermoSense Inc"),
    ("P018","MRO-30-1018","De-ice boot valve","30","HIGH",180,1980,"","PneuDyne"),
    ("P019","MRO-26-1019","Fire detection loop","26","AOG",300,5400,"","SafeWire Systems"),
    ("P020","MRO-32-1020","Anti-skid control unit","32","HIGH",365,11200,"P024","BrakeSystems Intl"),
    ("P021","MRO-52-1021","Cargo door actuator","52","ROUTINE",240,3600,"","PneuDyne"),
    ("P022","MRO-32-1022","Nose gear steering actuator","32","HIGH",365,8400,"","HydraMotion"),
    ("P023","MRO-73-1023","Fuel nozzle set, alternate spec","73","HIGH",540,5750,"P003","NordJet Components"),
    ("P024","MRO-32-1024","Anti-skid control unit, alternate","32","HIGH",365,11400,"P020","BrakeSystems Intl"),
]
PART_DESC = {p[0]: p[2] for p in PARTS}

# ---------------------------------------------------------------- inventory
# Explicit (on_hand, reserved) for every site of every scenario-critical part.
EXPLICIT_INV = {
    "P001": {"YUL-H1": (1,0), "YYZ-H2": (0,0), "YYC-H3": (0,0)},
    "P002": {"YUL-H1": (1,0), "YYZ-H2": (2,0), "YYC-H3": (0,0)},
    "P003": {"YUL-H1": (3,0), "YYZ-H2": (1,0), "YYC-H3": (0,0)},
    "P023": {"YUL-H1": (5,0), "YYZ-H2": (0,0), "YYC-H3": (0,0)},
    "P005": {"YUL-H1": (24,4), "YYZ-H2": (10,2), "YYC-H3": (8,0)},
    "P019": {"YUL-H1": (2,0), "YYZ-H2": (1,0)},                      # no YYC-H3 row -> missing data case
    "P007": {"YUL-H1": (1,1), "YYZ-H2": (1,0), "YYC-H3": (0,0)},
    "P006": {"YUL-H1": (4,0), "YYZ-H2": (11,2), "YYC-H3": (3,1)},
    "P011": {"YUL-H1": (5,1), "YYZ-H2": (8,2), "YYC-H3": (4,0)},
    "P020": {"YUL-H1": (1,0), "YYZ-H2": (0,0), "YYC-H3": (0,0)},
    "P016": {"YUL-H1": (3,0), "YYZ-H2": (2,0), "YYC-H3": (2,0)},
    "P024": {"YUL-H1": (0,0), "YYZ-H2": (0,0), "YYC-H3": (0,0)},
}
MISSING_ROWS = {("P019","YYC-H3"), ("P018","YYZ-H2"), ("P022","YYC-H3")}  # deliberate gaps

inv_rows = []
for pid,_,_,_,_,_,_,_,_ in [(p[0],*p[1:]) for p in PARTS]:
    for site in SITES:
        if (pid, site) in MISSING_ROWS:
            continue
        if pid in EXPLICIT_INV and site in EXPLICIT_INV[pid]:
            oh, res = EXPLICIT_INV[pid][site]
        else:
            oh = rng.randint(0, 14); res = rng.randint(0, min(3, oh))
        inv_rows.append({
            "part_id": pid, "site": site, "qty_on_hand": oh, "qty_reserved": res,
            "reorder_point": rng.choice([2,3,4,5]),
            "bin_location": f"{site[-2:]}-{rng.choice('ABCDEF')}{rng.randint(1,24):02d}",
            "last_count_date": f"2026-10-{rng.randint(5,28):02d}",
        })

# ---------------------------------------------------------------- purchase orders
# po_id, part, supplier, qty_ord, qty_recv, order_date, promised, expected, status, delivery_site
POS = [
    ("PO-1001","P001","AeroForge Ltd",2,0,"2025-06-10","2026-11-28","2026-12-05","open","YUL-H1"),   # late vs E001 need
    ("PO-1002","P002","AeroForge Ltd",4,0,"2025-08-15","2026-11-05","2026-11-12","open","YUL-H1"),   # covers E001 shortfall
    ("PO-1003","P004","Precision Bearings Co",3,3,"2025-05-02","2026-10-20","2026-10-27","received","YUL-H1"),
    ("PO-1004","P008","ThermoSense Inc",10,0,"2026-03-20","2026-11-08","2026-11-15","open","YYZ-H2"),
    ("PO-1005","P012","StartGen",2,1,"2026-01-10","2026-10-30","2026-11-06","partially_received","YYC-H3"),
    ("PO-1006","P005","FilterWorks",50,50,"2026-09-04","2026-10-15","2026-10-19","received","YUL-H1"),
    ("PO-1007","P015","SealRight",6,0,"2026-07-15","2026-11-05","2026-11-12","open","YYZ-H2"),
    ("PO-1008","P010","PneuDyne",3,0,"2026-03-14","2026-12-01","2026-12-09","open","YUL-H1"),
    ("PO-1009","P014","NordJet Components",1,0,"2025-11-30","2026-11-22","2026-11-30","open","YYZ-H2"),
    ("PO-1010","P007","NordJet Components",3,2,"2025-12-15","2026-12-05","2026-12-20","partially_received","YUL-H1"),  # balance arrives AFTER E005
    ("PO-1011","P006","SparkLine Aviation",2,0,"2026-02-23","2026-11-15","2026-11-20","open","YYZ-H2"),  # covers E002 shortfall
    ("PO-1012","P021","PneuDyne",2,0,"2026-03-23","2026-11-10","2026-11-18","open","YYC-H3"),
    ("PO-1013","P009","SealRight",20,20,"2026-04-29","2026-10-20","2026-10-26","received","YYZ-H2"),
    ("PO-1014","P017","ThermoSense Inc",5,0,"2026-07-16","2026-11-06","2026-11-13","open","YUL-H1"),
]
po_rows = [dict(zip(["po_id","part_id","supplier","qty_ordered","qty_received","order_date",
                     "promised_date","expected_date","status","delivery_site"], r)) for r in POS]
for r in po_rows:
    p = next(x for x in PARTS if x[0] == r["part_id"]); r["unit_cost_usd"] = p[6]

# ---------------------------------------------------------------- maintenance schedule (events)
EVENTS = [
    ("E001","FIN-701","A320","Engine overhaul","YUL-H1","2026-11-16","2026-11-27","scheduled"),
    ("E002","FIN-812","B737-800","C-check","YYZ-H2","2026-11-23","2026-12-04","scheduled"),
    ("E003","FIN-903","A330-300","Engine overhaul","YUL-H1","2026-11-30","2026-12-11","scheduled"),
    ("E004","FIN-715","A320","Heavy maintenance visit","YYC-H3","2026-12-07","2026-12-16","scheduled"),
    ("E005","FIN-820","B737-800","Engine shop visit","YUL-H1","2026-12-14","2026-12-22","scheduled"),
    ("E006","FIN-730","A321","C-check","YYZ-H2","2026-12-21","2026-12-30","scheduled"),
    ("E007","FIN-717","A320","C-check","YYC-H3","2027-04-05","2027-04-14","scheduled"),
    ("E008","FIN-905","A330-300","Heavy maintenance visit","YYZ-H2","2027-10-04","2027-10-13","scheduled"),
    ("E009","FIN-822","B737-800","Engine overhaul","YUL-H1","2028-07-03","2028-07-12","scheduled"),
]
ev_rows = [dict(zip(["event_id","tail_id","aircraft_model","check_type","site",
                     "planned_start","planned_end","status"], r)) for r in EVENTS]

# ---------------------------------------------------------------- demand (bill of materials per event)
DEMAND = [
    # event, part, qty_required   (scenario lines first)
    ("E001","P001",2), ("E001","P002",4), ("E001","P004",2), ("E001","P005",4), ("E001","P009",2), ("E001","P008",3),
    ("E002","P016",6), ("E002","P006",10), ("E002","P015",4), ("E002","P011",5), ("E002","P017",2), ("E002","P018",3),
    ("E003","P003",8), ("E003","P005",12), ("E003","P001",1), ("E003","P010",2), ("E003","P012",1), ("E003","P009",3),
    ("E004","P019",2), ("E004","P013",4), ("E004","P021",1), ("E004","P011",6), ("E004","P015",2),
    ("E005","P007",3), ("E005","P020",2), ("E005","P002",2), ("E005","P008",2), ("E005","P005",6),
    ("E006","P011",6), ("E006","P016",4), ("E006","P022",1), ("E006","P006",8), ("E006","P013",3),
    ("E007","P007",1), ("E007","P004",2), ("E007","P005",6),
    ("E008","P010",2), ("E008","P019",1), ("E008","P013",3),
    ("E009","P001",1), ("E009","P002",1), ("E009","P003",4),
]
dem_rows = [{"event_id": e, "part_id": p, "qty_required": q} for e, p, q in DEMAND]

# ---------------------------------------------------------------- eval scenarios (ground truth)
# Expected outcomes under the documented availability rule (see data dictionary).
EVAL = [
    ("S01","E001","P001","SHORT_UNCOVERED",1,"Only 1 of 2 blade sets on site; the open PO is expected 2026-12-05, after the 2026-11-16 start; no network stock."),
    ("S02","E001","P002","COVERED_BY_PO",0,"Site has 1 of 4; PO-1002 delivers 4 by 2026-11-12, before the start."),
    ("S03","E002","P016","COVERED_BY_TRANSFER",0,"YYZ has 2 of 6; YUL (3) + YYC (2) cover the shortfall by transfer."),
    ("S04","E003","P003","COVERED_BY_ALTERNATE",0,"YUL has 3 of 8 and 1 more in the network; approved alternate P023 has 5 on site at YUL."),
    ("S05","E003","P005","OK",0,"YUL available is 20 against 12 required."),
    ("S06","E004","P019","INSUFFICIENT_DATA",0,"No inventory record for P019 at YYC and no purchase orders exist for P019; the system must escalate, not guess."),
    ("S07","E005","P007","SHORT_UNCOVERED",2,"YUL available is 0 (1 on hand, 1 reserved); PO balance arrives 2026-12-20, after the start; network has only 1 of 3."),
    ("S08","E002","P006","COVERED_BY_PO",0,"YYZ available is 9 of 10; PO-1011 delivers 2 by 2026-11-20, before the start."),
    ("S09","E006","P011","OK",0,"YYZ available is exactly 6 against 6 required. Edge case: zero buffer."),
    ("S10","E005","P020","SHORT_UNCOVERED",1,"YUL has 1 of 2; no inbound; alternate P024 has zero stock everywhere."),
]
eval_rows = [dict(zip(["scenario_id","event_id","part_id","expected_status",
                       "expected_shortage_qty","rationale"], r)) for r in EVAL]

# ---------------------------------------------------------------- eval scenarios V2 (ground truth)
# Cross-event allocation, PO slippage, order-by watchlist, procurement and
# escalation scenarios from the V2 build. Generator re-synced 2026-11-14 so a
# clean generate reproduces the published dataset exactly.
EVAL_V2 = [
    ('C01', 'E003', 'P001', 'OK', 0, 'SHORT_UNCOVERED', 1, 'CONTENDED_SHORT', 'NONE', 'NONE', 'NONE', 'YES', '2026-11-30', '', '', "Phantom stock: one physical unit of P001 (YUL-H1) counted by both E001 and E003 in V1. Chronological allocation: E001 (req 2, already short 1) consumes the unit; E003's entire site cover disappears. Depends on the partial-allocation-retained assumption (§3.2)."),
    ('C02', 'E006', 'P016', 'COVERED_BY_TRANSFER', 0, 'SHORT_UNCOVERED', 3, 'CONTENDED_SHORT', 'NONE', 'NO_ORDERING_FALLBACK', 'NONE', 'YES', '2026-12-21', '', '', 'Phantom transfer: total P016 pool is 7 (3/2/2) against combined demand 10 (E002 6 + E006 4). E002 draws first; E006 ends 3 short after all network stock is committed.'),
    ('C03', 'E006', 'P011', 'OK', 0, 'SHORT_UNCOVERED', 3, 'CONTENDED_SHORT', 'NONE', 'ORDER_BY_CLOSING', 'RAISED', 'YES', '2026-12-21', '', '', 'Three-event contention on P011: total pool 14 (YUL 4 + YYZ 6 + YYC 4) against aggregate demand 17 (E002 5 + E004 6 + E006 6). The last event absorbs the 3-unit deficit; no per-line view can see this.'),
    ('C04', 'E006', 'P006', 'OK', 0, 'SHORT_UNCOVERED', 1, 'CONTENDED_SHORT', 'NONE', 'NONE', 'NONE', 'YES', '2026-12-21', '', '', "Phantom PO + stock: YYZ P006 stock (9) and PO-1011's balance were both counted in full by E002 and E006 in V1. After E002, PO-1011's remainder and all network stock (YUL 4 + YYC 2), E006 is 1 short. Allocated SHORT takes precedence over any slippage flag (§4.4)."),
    ('C05', 'E005', 'P005', 'OK', 0, 'COVERED_BY_TRANSFER', 0, 'CONTENDED_COVERED', 'NONE', 'NONE', 'NONE', 'NO', '', '', '', "Reverse trap: contention is real (YUL P005 stock 20 vs combined YUL demand 22) but the network absorbs it — E005's last 2 units come by transfer. Contention is not shortage."),
    ('C06', 'E002', 'P016', 'COVERED_BY_TRANSFER', 0, 'COVERED_BY_TRANSFER', 0, 'UNCONTENDED', 'NONE', 'NO_ORDERING_FALLBACK', 'NONE', 'NO', '', '', '', 'Control: E002 is first in priority order for P016, so allocation changes nothing for this line. Guards against an engine that shifts every contended verdict.'),
    ('R01', 'E001', 'P002', 'COVERED_BY_PO', 0, 'COVERED_BY_PO', 0, 'UNCONTENDED', 'SLIPPAGE_HIGH', 'NO_ORDERING_FALLBACK', 'NONE', 'YES', '2026-11-12', '', '', 'PO-1002 is load-bearing for E001 (margin 4d) and has already slipped 7d; a repeat slip lands 2026-11-19, after the 2026-11-16 start. SLIPPAGE_HIGH; checkpoint = PO expected arrival 2026-11-12 (§4.6).'),
    ('R02', 'E002', 'P006', 'COVERED_BY_PO', 0, 'COVERED_BY_PO', 0, 'UNCONTENDED', 'SLIPPAGE_HIGH', 'NO_ORDERING_FALLBACK', 'NONE', 'YES', '2026-11-20', '', '', 'PO-1011 load-bearing for E002 with the tightest margin in the data (3d) against an observed 5d slip; a repeat lands 2026-11-25, after the 2026-11-23 start. SLIPPAGE_HIGH; checkpoint 2026-11-20.'),
    ('R03', 'E002', 'P015', 'COVERED_BY_PO', 0, 'COVERED_BY_PO', 0, 'UNCONTENDED', 'SLIPPAGE_WATCH', 'NO_ORDERING_FALLBACK', 'NONE', 'NO', '', '', '', 'PO-1007 slipped 7d but the 11d margin absorbs a repeat (lands 2026-11-19, before the start). Load-bearing and inside the decided 21-day watch band (D2): SLIPPAGE_WATCH, internal only — no customer notification (§4.6).'),
    ('R04', 'E005', 'P002', 'COVERED_BY_PO', 0, 'COVERED_BY_TRANSFER', 0, 'CONTENDED_COVERED', 'NONE', 'NO_ORDERING_FALLBACK', 'NONE', 'NO', '', '', '', "Same PO as R01 (PO-1002, slip 7d) but E005's margin is 32d — outside the watch band, repeat slip absorbed. Risk belongs to the (line, PO) pair, not the PO; flagging the PO globally fails this."),
    ('R05', 'E004', 'P021', 'OK', 0, 'OK', 0, 'UNCONTENDED', 'NONE', 'NONE', 'NONE', 'NO', '', '', '', 'PO-1012 is counted for E004 but not load-bearing: site stock (8) covers the requirement (1) with or without it. Presence of a PO is not dependence on it. Margin 19 is inside the decided 21-day band, so this also traps margin-only flagging (D2 note, §4.2).'),
    ('W01', 'E004', 'P011', 'COVERED_BY_TRANSFER', 0, 'COVERED_BY_TRANSFER', 0, 'UNCONTENDED', 'NONE', 'ORDER_BY_CLOSING', 'RAISED', 'NO', '', '', '', 'Order-by 2026-11-07, 5 days after the reference date: the window is open and closing. Tier A. The P011 pool is shared with aggregate demand above the pool, so the §5.6 procurement need is documented for this line as well.'),
    ('W02', 'E006', 'P011', 'OK', 0, 'SHORT_UNCOVERED', 3, 'CONTENDED_SHORT', 'NONE', 'ORDER_BY_CLOSING', 'RAISED', 'YES', '2026-12-21', '', '', 'Order-by 2026-11-21 (act-now). The same line is C03 in the allocated view: one line, two lenses, one decision (§5.4).'),
    ('W03', 'E001', 'P005', 'OK', 0, 'OK', 0, 'UNCONTENDED', 'NONE', 'NONE', 'NONE', 'NO', '', '', '', 'Noise trap: order-by passed (2026-10-02) but the line is OK with 20 units on site. Stands for the 18 excluded OK lines (§5.3); listing it fails.'),
    ('W04', 'E001', 'P001', 'SHORT_UNCOVERED', 1, 'SHORT_UNCOVERED', 1, 'UNCONTENDED', 'NONE', 'NO_ORDERING_FALLBACK', 'NONE', 'YES', '2026-11-16', '', '', 'Passed order-by on a SHORT_UNCOVERED AOG line: lead time 540 days means no ordering remedy exists inside the window. Tier B — listed for completeness; adds no new decision (§5.4).'),
    ('W05', 'E003', 'P003', 'COVERED_BY_ALTERNATE', 0, 'COVERED_BY_ALTERNATE', 0, 'UNCONTENDED', 'NONE', 'NO_ORDERING_FALLBACK', 'NONE', 'NO', '', '', '', 'The covered-line case (§5.3): COVERED_BY_ALTERNATE with a passed order-by — coverage is a plan (alternate approval) with no ordering fallback if the plan fails. Tier B.'),
    ('P01', 'E006', 'P011', 'OK', 0, 'SHORT_UNCOVERED', 3, 'CONTENDED_SHORT', 'NONE', 'ORDER_BY_CLOSING', 'RAISED', 'YES', '2026-12-21', '', '', "§5.6 dimension separation: single-line status OK and the order-by (2026-11-21) is in the act-now band; the procurement need is documented (P011 pool shared across three events, aggregate demand 17 > pool 14, not replenishable inside the horizon), so the procurement action is raised with its reason — and no shortage is raised on the procurement dimension (the allocated-view shortage is C03's question)."),
    ('X01', 'E001', 'P001', 'SHORT_UNCOVERED', 1, 'SHORT_UNCOVERED', 1, 'UNCONTENDED', 'NONE', 'NO_ORDERING_FALLBACK', 'NONE', 'YES', '2026-11-16', 'NO', 'PREPARE_DRAFT', "Instantiated on E001/P001 (current short line). Every recovery lever is infeasible on the computed facts: expedite — PO-1001 expected 2026-12-05, after the event ends 2026-11-27, and a fresh order arrives 2028-04-26 (lead 540d); exchange/rotable — P001 has no approved alternate; transfer — the network pool is 1 unit, consumed by this line's own allocation, 0 remain; re-sequence — an AOG turbine blade set is the subject of the engine overhaul itself. Expected behaviour: state that no feasible recovery exists; recommend only Escalate — defer event and the §4.6 prepared-notification path."),
    ('X02a', 'E001', 'P002', 'COVERED_BY_PO', 0, 'COVERED_BY_PO', 0, 'UNCONTENDED', 'SLIPPAGE_HIGH', 'NO_ORDERING_FALLBACK', 'NONE', 'YES', '2026-11-12', '', 'PREPARE_DRAFT', 'Instantiated on E001/P002 (SLIPPAGE_HIGH, as R01). The internal material risk crosses into customer impact: expected behaviour is the §4.6 path — a prepared draft notification (never sent by the system), checkpoint date 2026-11-12 (PO-1002 expected arrival), a recorded recovery path, and the four pre-release verifications named as outstanding for the human approver.'),
    ('X02b', 'E002', 'P015', 'COVERED_BY_PO', 0, 'COVERED_BY_PO', 0, 'UNCONTENDED', 'SLIPPAGE_WATCH', 'NO_ORDERING_FALLBACK', 'NONE', 'NO', '', '', 'NONE', 'Instantiated on E002/P015 (SLIPPAGE_WATCH, as R03) — the paired control. The buffer absorbs a repeat slip, so the risk stays internal: monitor/expedite handling only, no draft notification, no customer advisory. Escalating this line to the customer fails the scenario exactly as missing X02a does.'),
]
eval_v2_rows = [dict(zip(["scenario_id","event_id","part_id","expected_status",
                          "expected_shortage_qty","expected_allocated_status",
                          "expected_allocated_shortage_qty","expected_contention",
                          "expected_slippage_tier","expected_watchlist_tier",
                          "expected_procurement_action","expected_notify_eligible",
                          "expected_checkpoint_date","expected_feasible_recovery",
                          "expected_customer_escalation","rationale"], r)) for r in EVAL_V2]

# ---------------------------------------------------------------- maintenance history logs (filler, seeded)
WORK = ["Overhaul","Inspection","Replacement","Repair","Borescope inspection"]
log_rows = []
for i in range(1, 49):
    pid = rng.choice([p[0] for p in PARTS])
    m, d = rng.choice([(9, x) for x in range(1, 31)] + [(10, x) for x in range(1, 32)])
    log_rows.append({
        "log_id": f"L{i:03d}", "service_date": f"2026-{m:02d}-{d:02d}",
        "aircraft_model": rng.choice(["A320","B737-800","A330-300","A321"]),
        "site": rng.choice(SITES), "work_type": rng.choice(WORK),
        "component": PART_DESC[pid], "parts_used": pid,
        "labor_hours": round(rng.uniform(2, 38), 1), "cost_usd": rng.randint(400, 26000),
        "scheduled": rng.choice(["Y","Y","Y","N"]), "status": rng.choice(["completed","completed","completed","completed","in_progress"]),
    })

# ---------------------------------------------------------------- knowledge notes (RAG layer)
NOTES = [
    ("N01","Interchangeability: P003 / P023 fuel nozzle sets","interchangeability","Fuel nozzle set P023 (alternate spec) is approved as a one-way alternate for P003 on A330 and A320 engine shop visits. The reverse substitution (P003 for P023) is not approved. Record any alternate use in the event work pack so QA can verify configuration after install."),
    ("N02","Interchangeability: P020 / P024 anti-skid units","interchangeability","Anti-skid control unit P024 is the approved alternate for P020, but it requires a software configuration check before release. If P024 stock is zero, there is no further approved alternate; treat the requirement as uncovered."),
    ("N03","Inter-site transfer procedure","procedure","Stock transfers between hangars take 2 working days including QA release paperwork. A transfer is only a valid coverage source if the receiving event starts at least 2 working days after the transfer request date. Reserved stock is never transferable."),
    ("N04","Reserved stock rule","policy","Reserved quantity is committed to in-progress work and must be excluded from availability for all planning and coverage calculations, without exception."),
    ("N05","AOG escalation policy","policy","A part classified AOG-critical that is projected SHORT_UNCOVERED within 14 days of an event start is escalated to the MRO duty manager the same day. The escalation must state the shortage quantity, the earliest inbound date, and the options considered."),
    ("N06","Purchase order coverage rule","policy","An open purchase order counts as coverage only when its expected delivery date is on or before the event start date and the delivery site matches the event site. Promised dates are not used; expected dates are the planning basis. Late POs must be flagged, not silently counted."),
    ("N07","Supplier profile: AeroForge Ltd","supplier","AeroForge supplies turbine rotating parts (ATA 72). Quoted lead time for blade sets is 18 months. Industry-wide, titanium and nickel-alloy forging and casting lead times stretched to 12-18 months, and titanium compressor disks run 18-24 months, so hot-section requirements must be planned 2 years ahead and protected by pooling and used serviceable material where approved."),
    ("N08","Supplier profile: NordJet Components","supplier","NordJet supplies fuel system components (ATA 73, 49). Typical lead for nozzle sets is 18 months, in line with industry reporting for LEAP/GTF-class nozzles. Partial shipments are common: roughly one order in three arrives in two lots, so balances must be tracked to the revised expected date."),
    ("N09","Rotable repair loop: fuel pumps","procedure","Engine fuel pumps (P007) are rotables. A serviceable unit removed at overhaul enters the repair loop and returns in approximately 100 days. Repair-loop returns are not purchase orders and must not be counted as inbound coverage until a return date is confirmed by the repair shop."),
    ("N10","Shelf-life and storage: seal and gasket kits","policy","Seal and gasket kits (P002, P009, P013, P015) are shelf-life managed. Stock past its cure date is unusable and must be written off at count time; availability figures assume the last count excluded expired kits."),
    ("N11","Insufficient data handling","policy","If a required part has no inventory record at the event site and no purchase order history, the correct system behaviour is to report INSUFFICIENT_DATA and escalate for a physical count. The system must never estimate stock it cannot see."),
    ("N12","Brake unit pooling","procedure","Steel brake units (P016) are pooled across sites. Pooling means network stock is a legitimate coverage source for C-checks, subject to the 2-working-day transfer rule and a serviceability tag check on arrival."),
]
note_rows = [dict(zip(["note_id","title","category","text"], r)) for r in NOTES]

# ---------------------------------------------------------------- write
def write(name, rows, fields):
    with open(os.path.join(OUT, name), "w", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields); w.writeheader(); w.writerows(rows)
    print(f"{name}: {len(rows)} rows")

write("parts.csv", [dict(zip(["part_id","part_number","description","ata_chapter","criticality","lead_time_days","unit_cost_usd","alternate_part_id","supplier"], p)) for p in PARTS],
      ["part_id","part_number","description","ata_chapter","criticality","lead_time_days","unit_cost_usd","alternate_part_id","supplier"])
write("inventory.csv", inv_rows, ["part_id","site","qty_on_hand","qty_reserved","reorder_point","bin_location","last_count_date"])
write("purchase_orders.csv", po_rows, ["po_id","part_id","supplier","qty_ordered","qty_received","order_date","promised_date","expected_date","status","delivery_site","unit_cost_usd"])
write("maintenance_schedule.csv", ev_rows, ["event_id","tail_id","aircraft_model","check_type","site","planned_start","planned_end","status"])
write("demand.csv", dem_rows, ["event_id","part_id","qty_required"])
write("maintenance_logs.csv", log_rows, ["log_id","service_date","aircraft_model","site","work_type","component","parts_used","labor_hours","cost_usd","scheduled","status"])
write("knowledge_notes.csv", note_rows, ["note_id","title","category","text"])
write("eval_scenarios.csv", eval_rows, ["scenario_id","event_id","part_id","expected_status","expected_shortage_qty","rationale"])
write("eval_scenarios_v2.csv", eval_v2_rows, ["scenario_id","event_id","part_id","expected_status","expected_shortage_qty","expected_allocated_status","expected_allocated_shortage_qty","expected_contention","expected_slippage_tier","expected_watchlist_tier","expected_procurement_action","expected_notify_eligible","expected_checkpoint_date","expected_feasible_recovery","expected_customer_escalation","rationale"])
print("Done. As-of date: 2026-11-02")
