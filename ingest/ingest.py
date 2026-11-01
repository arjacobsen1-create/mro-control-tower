#!/usr/bin/env python3
"""
Stage 2 ingestion — MRO Control Tower.

Loads the 8 synthetic dataset CSVs (data/) into a local SQLite store
(data/mro.db), builds an FTS5 (BM25) full-text index over the knowledge
notes for retrieval, and runs integrity checks:
  - expected row counts per table
  - referential integrity (demand -> parts/events, inventory/PO -> parts,
    eval scenarios -> existing demand lines)
  - no negative stock, received <= ordered

Run:  python3 ingest/ingest.py        (from the project root)
Reference date pinned by the dataset: 2026-11-02 (see config.py).
"""
import csv, os, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DATA_DIR, DB_PATH, REFERENCE_DATE

TABLES = {  # table -> (csv file, expected rows)
    "parts": ("parts.csv", 24),
    "inventory": ("inventory.csv", 69),
    "purchase_orders": ("purchase_orders.csv", 14),
    "maintenance_schedule": ("maintenance_schedule.csv", 6),
    "demand": ("demand.csv", 33),
    "maintenance_logs": ("maintenance_logs.csv", 48),
    "knowledge_notes": ("knowledge_notes.csv", 12),
    "eval_scenarios": ("eval_scenarios.csv", 10),
}
INT_COLS = {"qty_on_hand", "qty_reserved", "reorder_point", "qty_ordered",
            "qty_received", "qty_required", "expected_shortage_qty",
            "lead_time_days", "unit_cost_usd", "cost_usd"}


def main():
    if os.path.exists(DB_PATH):
        os.remove(DB_PATH)
    con = sqlite3.connect(DB_PATH)
    cur = con.cursor()

    for table, (fname, expected) in TABLES.items():
        with open(os.path.join(DATA_DIR, fname)) as f:
            rows = list(csv.DictReader(f))
        cols = list(rows[0].keys())
        defs = ", ".join(f'"{c}" {"INTEGER" if c in INT_COLS else "TEXT"}' for c in cols)
        cur.execute(f'CREATE TABLE "{table}" ({defs})')
        ph = ", ".join("?" * len(cols))
        for r in rows:
            cur.execute(f'INSERT INTO "{table}" VALUES ({ph})',
                        [int(r[c]) if c in INT_COLS and r[c] != "" else (r[c] or None) for c in cols])
        n = cur.execute(f'SELECT COUNT(*) FROM "{table}"').fetchone()[0]
        assert n == expected, f"{table}: {n} rows, expected {expected}"
        print(f"{table}: {n} rows loaded")

    # --- FTS5 retrieval index over knowledge notes (title weighted above text)
    cur.execute("CREATE VIRTUAL TABLE notes_fts USING fts5(note_id UNINDEXED, title, text, category UNINDEXED)")
    cur.execute("INSERT INTO notes_fts SELECT note_id, title, text, category FROM knowledge_notes")
    n = cur.execute("SELECT COUNT(*) FROM notes_fts").fetchone()[0]
    print(f"notes_fts: {n} notes indexed")

    # --- integrity checks
    checks = []
    def check(name, sql):
        bad = cur.execute(sql).fetchone()[0]
        checks.append((name, bad))
        print(f"check {name}: {'OK' if bad == 0 else f'{bad} VIOLATIONS'}")

    check("demand_parts_exist",
          "SELECT COUNT(*) FROM demand d LEFT JOIN parts p ON d.part_id=p.part_id WHERE p.part_id IS NULL")
    check("demand_events_exist",
          "SELECT COUNT(*) FROM demand d LEFT JOIN maintenance_schedule e ON d.event_id=e.event_id WHERE e.event_id IS NULL")
    check("inventory_parts_exist",
          "SELECT COUNT(*) FROM inventory i LEFT JOIN parts p ON i.part_id=p.part_id WHERE p.part_id IS NULL")
    check("po_parts_exist",
          "SELECT COUNT(*) FROM purchase_orders o LEFT JOIN parts p ON o.part_id=p.part_id WHERE p.part_id IS NULL")
    check("eval_lines_exist",
          "SELECT COUNT(*) FROM eval_scenarios s LEFT JOIN demand d ON s.event_id=d.event_id AND s.part_id=d.part_id WHERE d.part_id IS NULL")
    check("no_negative_stock",
          "SELECT COUNT(*) FROM inventory WHERE qty_on_hand < 0 OR qty_reserved < 0 OR qty_reserved > qty_on_hand")
    check("po_received_le_ordered",
          "SELECT COUNT(*) FROM purchase_orders WHERE qty_received > qty_ordered")
    con.commit(); con.close()
    bad = [c for c in checks if c[1] != 0]
    print(f"\nIngestion complete -> {DB_PATH} (reference date {REFERENCE_DATE})")
    if bad:
        print("FAILED checks:", bad); sys.exit(1)
    print("All integrity checks passed.")


if __name__ == "__main__":
    main()
