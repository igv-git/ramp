"""Connection and schema bootstrap. The only module family that imports sqlite3."""

import sqlite3
from pathlib import Path

from ramp.store.schema import DDL, SCHEMA_VERSION


def connect(path: Path) -> sqlite3.Connection:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys=ON")
    conn.executescript(DDL)
    row = conn.execute("SELECT value FROM meta WHERE key='schema_version'").fetchone()
    if row is None:
        conn.execute("INSERT INTO meta(key, value) VALUES ('schema_version', ?)", (str(SCHEMA_VERSION),))
        conn.commit()
    elif int(row["value"]) != SCHEMA_VERSION:
        conn.close()
        raise RuntimeError(f"unsupported schema_version {row['value']} (expected {SCHEMA_VERSION})")
    return conn
