import json
import sqlite3
import subprocess
import sys
import threading
import urllib.error
import urllib.request
from pathlib import Path

import pytest

from panda_router.heuristic import HeuristicProfiler
from panda_router.matcher import schema_errors
from panda_router.serve import Router, load_profiler, make_server

ROOT = Path(__file__).resolve().parents[1]
TASK = {"text": "Fix the failing unit test in parser.py: IndexError on empty input",
        "context": {"repo_languages": ["python"], "files_in_scope": 1, "estimated_input_tokens": 3000,
                    "requires_tools": True}}


@pytest.fixture()
def server(tmp_path):
    router = Router(db_path=tmp_path / "log.sqlite")
    srv = make_server(router, "127.0.0.1", 0)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield f"http://127.0.0.1:{srv.server_port}", router
    srv.shutdown()
    srv.server_close()


def call(url, path, body=None):
    data = None if body is None else json.dumps(body).encode()
    rq = urllib.request.Request(url + path, data=data, headers={"Content-Type": "application/json"},
                                method="GET" if body is None else "POST")
    try:
        with urllib.request.urlopen(rq, timeout=10) as r:
            return r.status, json.loads(r.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read())


def test_http_roundtrip(server):
    url, router = server
    code, health = call(url, "/health")
    assert code == 200 and health["ok"] and health["cards"] >= 17 and health["profiler"] == "heuristic"

    code, resp = call(url, "/route", {"task": TASK, "return_top_k": 3})
    assert code == 200, resp
    assert schema_errors(resp, "route_response") == []
    assert resp["choice"]["model_id"] in router.matcher.cards
    assert resp["trace_id"].startswith("r_")

    outcome = {"trace_id": resp["trace_id"], "model_id": resp["choice"]["model_id"],
               "propensity": resp["choice"]["propensity"], "success": False,
               "signals": {"tests_passed": False, "retries": 0}, "actual_cost_usd": 0.01}
    code, ack = call(url, "/outcome", outcome)
    assert code == 200 and ack["ok"]

    code, esc = call(url, "/escalate", {"request": {"task": TASK}, "response": resp,
                                        "failed_model_id": resp["choice"]["model_id"]})
    assert code == 200, esc
    assert esc["choice"]["model_id"] != resp["choice"]["model_id"]

    with sqlite3.connect(router.store.path) as c:
        assert c.execute("SELECT COUNT(*) FROM routes").fetchone()[0] == 2
        row = c.execute("SELECT trace_id, model_id, success FROM outcomes").fetchone()
    assert row == (resp["trace_id"], resp["choice"]["model_id"], 0)
    assert router.store.outcomes(resp["trace_id"])[0]["signals"]["tests_passed"] is False


def test_http_errors(server):
    url, _ = server
    assert call(url, "/route", {"pool": []})[0] == 400  # missing task
    assert call(url, "/outcome", {"trace_id": "x"})[0] == 400
    assert call(url, "/route", {"task": TASK, "preferences": {"mode": "bogus"}})[0] == 400
    assert call(url, "/nope", {})[0] == 404
    assert call(url, "/escalate", {"request": {"task": TASK}, "response": {}, "failed_model_id": "nope"})[0] == 400


def test_load_profiler_falls_back(tmp_path):
    assert isinstance(load_profiler(None), HeuristicProfiler)
    assert isinstance(load_profiler(tmp_path / "does-not-exist"), HeuristicProfiler)


def test_router_direct(tmp_path):
    r = Router(db_path=tmp_path / "x.sqlite", log_routes=False)
    resp = r.route({"task": TASK, "constraints": {"local_only": True}})
    assert resp["choice"]["model_id"] == "ollama-gemma4-26b"
    assert r.record_outcome({"trace_id": resp["trace_id"], "model_id": "ollama-gemma4-26b", "success": True})["ok"]


def test_cli_route(tmp_path):
    out = subprocess.run([sys.executable, "-m", "panda_router.serve.cli", "route", "--task", "Fix the typo in README",
                          "--no-log", "--db", str(tmp_path / "c.sqlite")],
                         cwd=ROOT, capture_output=True, text=True, timeout=60)
    assert out.returncode == 0, out.stderr
    resp = json.loads(out.stdout)
    assert schema_errors(resp, "route_response") == []
    assert resp["router"]["profiler"] == "heuristic"
