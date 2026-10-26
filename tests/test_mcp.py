import json
import subprocess
import sys

import pytest


@pytest.fixture()
def server(tmp_path):
    p = subprocess.Popen([sys.executable, "-m", "panda_router.mcp", "--db", str(tmp_path / "log.sqlite")],
                         stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL, text=True)

    def rpc(method, params=None, id=1):
        p.stdin.write(json.dumps({"jsonrpc": "2.0", "id": id, "method": method, "params": params or {}}) + "\n")
        p.stdin.flush()
        r = json.loads(p.stdout.readline())
        assert r["jsonrpc"] == "2.0" and r["id"] == id
        return r

    yield rpc, p
    p.stdin.close()
    p.wait(timeout=10)


def test_mcp_flow(server):
    rpc, p = server
    init = rpc("initialize", {"protocolVersion": "2025-06-18", "capabilities": {}, "clientInfo": {"name": "t"}})
    assert init["result"]["protocolVersion"] == "2025-06-18"
    p.stdin.write(json.dumps({"jsonrpc": "2.0", "method": "notifications/initialized"}) + "\n")
    assert rpc("ping", id=2)["result"] == {}
    names = {t["name"] for t in rpc("tools/list", id=3)["result"]["tools"]}
    assert names == {"route_task", "escalate_task", "record_outcome", "list_models"}

    models = rpc("tools/call", {"name": "list_models"}, id=4)["result"]["structuredContent"]["models"]
    assert models and {"id", "provider", "cost", "local"} <= models[0].keys()

    res = rpc("tools/call", {"name": "route_task", "arguments": {"task_text": "fix a typo in README"}}, id=5)["result"]
    assert not res.get("isError")
    out = res["structuredContent"]
    trace = out["trace_id"]
    assert trace in res["content"][0]["text"]
    model = out["choice"]["model_id"]

    esc = rpc("tools/call", {"name": "escalate_task", "arguments": {"trace_id": trace, "failed_model_id": model}},
              id=6)["result"]
    assert not esc.get("isError") and esc["structuredContent"]["choice"]["model_id"] != model

    rec = rpc("tools/call", {"name": "record_outcome", "arguments": {
        "trace_id": trace, "model_id": model, "success": True, "cost_usd": 0.01}}, id=7)["result"]
    assert rec["structuredContent"]["ok"] is True

    bad = rpc("tools/call", {"name": "route_task", "arguments": {}}, id=8)["result"]
    assert bad["isError"] is True
    assert rpc("nope", id=9)["error"]["code"] == -32601
