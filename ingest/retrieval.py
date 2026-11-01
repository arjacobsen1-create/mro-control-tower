#!/usr/bin/env python3
"""
Retrieval over the knowledge notes (FTS5 / BM25).

search_notes(query, k) -> list of {note_id, title, category, score}
  - Title matches are weighted above body matches.
  - A query sharing no terms with any note returns [] (abstention):
    the agent layer treats 'no grounding found' as escalate, never guess.

CLI:  python3 ingest/retrieval.py "can I use the alternate fuel nozzle?"
"""
import os, re, sqlite3, sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from config import DB_PATH

STOP = set("can i the a an is it to of for and or do does what how when if we use used using".split())

# BM25 relevance threshold (FTS5 scores: more negative = stronger match).
# Calibrated on the test queries: genuine top-1 matches score -4.7 to -15.4,
# while an off-topic query's best accidental match scores only -1.05.
# Hits weaker than this are treated as 'no grounding found'.
RELEVANCE_THRESHOLD = -2.5


def _terms(query: str):
    toks = re.findall(r"[a-z0-9]+", query.lower())
    return [t for t in toks if t not in STOP and len(t) > 1] or toks


def search_notes(query: str, k: int = 3, db_path: str = DB_PATH):
    terms = _terms(query)
    if not terms:
        return []
    match = " OR ".join(f'"{t}"' for t in terms)
    con = sqlite3.connect(db_path)
    try:
        rows = con.execute(
            "SELECT note_id, title, category, bm25(notes_fts, 0, 10.0, 1.0, 0) AS score "
            "FROM notes_fts WHERE notes_fts MATCH ? ORDER BY score LIMIT ?",
            (match, k)).fetchall()
    finally:
        con.close()
    return [{"note_id": r[0], "title": r[1], "category": r[2], "score": round(r[3], 3)}
            for r in rows if r[3] <= RELEVANCE_THRESHOLD]


if __name__ == "__main__":
    q = " ".join(sys.argv[1:]) or "fuel nozzle alternate"
    for hit in search_notes(q):
        print(f"{hit['note_id']}  [{hit['category']}]  {hit['title']}  (score {hit['score']})")
    if not search_notes(q):
        print("No grounding found — escalate (do not guess).")
