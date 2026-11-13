"""Locate the source checkout's SQL, config and data directories centrally."""

from pathlib import Path


PROJECT_DIR = Path(__file__).resolve().parents[2]
SQL_DIR = PROJECT_DIR / "sql"
DATA_DIR = PROJECT_DIR / "data"
