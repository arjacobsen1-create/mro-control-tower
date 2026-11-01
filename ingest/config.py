"""Project configuration for the MRO Control Tower prototype.

REFERENCE_DATE is the dataset's simulated as-of date (2026-11-02).
Every test and evaluation pins this date as 'today' so results are
reproducible regardless of when they run. Never substitute the run date.
"""
import os

REFERENCE_DATE = "2026-11-02"

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA_DIR = os.path.join(ROOT, "data")
DB_PATH = os.path.join(DATA_DIR, "mro.db")
