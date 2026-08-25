import json
import sqlite3
from datetime import datetime, timezone

from . import config

_SCHEMA = """
CREATE TABLE IF NOT EXISTS jobs (
    id TEXT PRIMARY KEY,
    kind TEXT NOT NULL,
    status TEXT NOT NULL,
    params TEXT NOT NULL,
    result TEXT,
    error TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);
"""


def _connect() -> sqlite3.Connection:
    conn = sqlite3.connect(config.DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def init_db() -> None:
    with _connect() as conn:
        conn.executescript(_SCHEMA)


def _now() -> str:
    return datetime.now(timezone.utc).isoformat()


def upsert_job(job_id: str, kind: str, status: str, params: dict,
               result: dict | None = None, error: str | None = None) -> None:
    with _connect() as conn:
        row = conn.execute("SELECT id FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            conn.execute(
                "INSERT INTO jobs (id, kind, status, params, result, error, created_at, updated_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (job_id, kind, status, json.dumps(params), json.dumps(result), error, _now(), _now()),
            )
        else:
            conn.execute(
                "UPDATE jobs SET status = ?, result = ?, error = ?, updated_at = ? WHERE id = ?",
                (status, json.dumps(result), error, _now(), job_id),
            )


def get_job_row(job_id: str) -> dict | None:
    with _connect() as conn:
        row = conn.execute("SELECT * FROM jobs WHERE id = ?", (job_id,)).fetchone()
        if row is None:
            return None
        return dict(row)


def list_job_rows(limit: int = 100) -> list[dict]:
    with _connect() as conn:
        rows = conn.execute(
            "SELECT * FROM jobs ORDER BY created_at DESC LIMIT ?", (limit,)
        ).fetchall()
        return [dict(r) for r in rows]
