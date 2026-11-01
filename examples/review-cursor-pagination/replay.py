"""Synthetic semantic replay in memory; no production database or performance claim."""
from pathlib import Path
import json
import sqlite3

root = Path(__file__).resolve().parent
fixture = json.loads((root / "fixture.json").read_text())
with sqlite3.connect(":memory:") as db:
    db.execute("CREATE TABLE bookmarks (id INTEGER PRIMARY KEY, owner_id TEXT, saved_seq INTEGER)")
    db.executemany("INSERT INTO bookmarks VALUES (?, ?, ?)", fixture["rows"])
    before = [r[0] for r in db.execute((root / "before.sql").read_text(), fixture["params"])]
    after = [r[0] for r in db.execute((root / "after.sql").read_text(), fixture["params"])]
    if before != [4] or after != fixture["expected_next"]:
        raise SystemExit("FAIL: unexpected synthetic query result")
print("PASS: before=[4], after=[1, 4]; synthetic SQLite semantics only")
