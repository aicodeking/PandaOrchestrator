"""Append-only SQLite log of routes and outcomes (joined by trace_id)."""

from __future__ import annotations

import json
import os
import sqlite3
import time
from pathlib import Path

DEFAULT_DB = Path(__file__).resolve().parents[2] / "data" / "cache" / "router_log.sqlite"

_SCHEMA = """
CREATE TABLE IF NOT EXISTS routes (
  trace_id TEXT PRIMARY KEY, ts REAL NOT NULL, model_id TEXT, propensity REAL,
  decided_by TEXT, pool_hash TEXT, request_json TEXT NOT NULL, response_json TEXT NOT NULL);
CREATE TABLE IF NOT EXISTS outcomes (
  id INTEGER PRIMARY KEY AUTOINCREMENT, trace_id TEXT NOT NULL, ts REAL NOT NULL, model_id TEXT NOT NULL,
  success INTEGER NOT NULL, propensity REAL, outcome_json TEXT NOT NULL);
CREATE INDEX IF NOT EXISTS outcomes_trace ON outcomes(trace_id);
"""


def default_db_path() -> Path:
    return Path(os.environ.get("PANDA_ROUTER_DB") or DEFAULT_DB)


class Store:
    def __init__(self, path: str | Path | None = None):
        self.path = Path(path) if path else default_db_path()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with self._conn() as c:
            c.executescript(_SCHEMA)

    def _conn(self) -> sqlite3.Connection:
        return sqlite3.connect(self.path, timeout=10)

    def log_route(self, request: dict, response: dict) -> None:
        ch = response["choice"]
        with self._conn() as c:
            c.execute("INSERT OR REPLACE INTO routes VALUES (?,?,?,?,?,?,?,?)",
                      (response["trace_id"], time.time(), ch["model_id"], ch.get("propensity"), ch["decided_by"],
                       response["router"]["pool_hash"], json.dumps(request), json.dumps(response)))

    def log_outcome(self, outcome: dict) -> int:
        with self._conn() as c:
            cur = c.execute("INSERT INTO outcomes (trace_id, ts, model_id, success, propensity, outcome_json) "
                            "VALUES (?,?,?,?,?,?)",
                            (outcome["trace_id"], time.time(), outcome["model_id"], int(bool(outcome["success"])),
                             outcome.get("propensity"), json.dumps(outcome)))
            return int(cur.lastrowid)

    def outcomes(self, trace_id: str | None = None) -> list[dict]:
        q, args = "SELECT outcome_json FROM outcomes", ()
        if trace_id:
            q, args = q + " WHERE trace_id = ?", (trace_id,)
        with self._conn() as c:
            return [json.loads(r[0]) for r in c.execute(q + " ORDER BY id", args)]

    def route_record(self, trace_id: str) -> dict | None:
        with self._conn() as c:
            r = c.execute("SELECT request_json, response_json FROM routes WHERE trace_id = ?", (trace_id,)).fetchone()
        return {"request": json.loads(r[0]), "response": json.loads(r[1])} if r else None
