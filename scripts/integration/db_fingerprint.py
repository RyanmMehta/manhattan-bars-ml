"""Per-table row count + content hash (ordered SELECT *) for a SQLite DB, as a markdown table.

Usage: python -I scripts/integration/db_fingerprint.py [data/live_sim.db]
"""
import hashlib
import sqlite3
import sys
from pathlib import Path

db = Path(sys.argv[1] if len(sys.argv) > 1 else "data/live_sim.db")
con = sqlite3.connect(f"file:{db}?mode=ro", uri=True)
print("| table | rows | sha256 (first 12) |\n|---|---|---|")
for (t,) in con.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    cols = [r[1] for r in con.execute(f'PRAGMA table_info("{t}")')]
    h = hashlib.sha256()
    n = 0
    for row in con.execute(f'SELECT * FROM "{t}" ORDER BY {", ".join(chr(34)+c+chr(34) for c in cols)}'):
        h.update(repr(row).encode())
        n += 1
    print(f"| {t} | {n} | {h.hexdigest()[:12]} |")
