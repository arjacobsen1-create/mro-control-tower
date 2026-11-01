#!/usr/bin/env python3
"""
Retrieval tests — pinned queries with expected top-1 notes, plus an
abstention case. Reference date for the project: 2026-11-02 (config.py).
Run after ingest.py:  python3 ingest/test_retrieval.py
"""
import os, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from retrieval import search_notes

CASES = [  # (query, expected top-1 note)
    ("can I use the alternate fuel nozzle set for this engine?", "N01"),
    ("how long does a stock transfer between sites take?", "N03"),
    ("is reserved stock available for planning?", "N04"),
    ("AOG part short before the event, who do I escalate to?", "N05"),
    ("does a late purchase order with an expected date after the start count as coverage?", "N06"),
    ("fuel pump removed at overhaul, when does the rotable come back?", "N09"),
    ("the part has no inventory record at this site, what should happen?", "N11"),
    ("are brake units pooled across sites for a C-check?", "N12"),
    ("anti-skid alternate unit needs what check before release?", "N02"),
]
ABSTAIN = "what is on the catering menu for lunch today"

fails = 0
for q, want in CASES:
    hits = search_notes(q, k=3)
    top = hits[0]["note_id"] if hits else "NONE"
    ok = top == want
    fails += (not ok)
    print(f"{'PASS' if ok else 'FAIL'}  top={top} (want {want})  <- {q}")

hits = search_notes(ABSTAIN, k=3)
ok = len(hits) == 0
fails += (not ok)
print(f"{'PASS' if ok else 'FAIL'}  abstention: off-topic query returned {len(hits)} hits (want 0)")

print(f"\n{len(CASES)+1-fails}/{len(CASES)+1} retrieval tests passed.")
sys.exit(1 if fails else 0)
