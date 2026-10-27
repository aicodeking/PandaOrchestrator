"""Minimal stdlib MCP server (stdio, newline-delimited JSON-RPC 2.0, protocol 2025-06-18).

python -m panda_router.mcp [--artifacts DIR] [--cards DIR] [--db PATH]
Env: PANDA_ROUTER_ARTIFACTS / PANDA_ROUTER_CARDS / PANDA_ROUTER_DB. Logs go to stderr only.
"""

from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

from ..serve.router import RequestError, Router, load_profiler, profiler_name

ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS = ROOT / "artifacts" / "panda-router-v3"
PROTOCOL = "2025-06-18"

_STR_LIST = {"type": "array", "items": {"type": "string"}}
TOOLS = [
    {"name": "route_task",
     "description": "Pick the best LLM for a task. Returns the chosen model, P(success), difficulty, category and a "
                    "trace_id to pass to record_outcome / escalate_task.",
     "inputSchema": {"type": "object", "required": ["task_text"], "properties": {
         "task_text": {"type": "string", "description": "The task to route, in plain text."},
         "context": {"type": "object", "description": "Optional: repo_languages[], files_in_scope, "
                     "estimated_input_tokens, has_images, requires_tools."},
         "pool": {**_STR_LIST, "description": "Candidate model names (aliases/typos ok). Default: all cards."},
         "mode": {"enum": ["cheapest_above_threshold", "max_utility", "max_quality"]},
         "min_p_success": {"type": "number", "minimum": 0, "maximum": 1},
         "max_cost_usd": {"type": "number", "minimum": 0},
         "local_only": {"type": "boolean"},
         "require": {"type": "array", "items": {"enum": ["tools", "vision", "json_mode", "web"]}},
         "exclude": _STR_LIST,
         "top_k": {"type": "integer", "minimum": 1, "maximum": 50}}}},
    {"name": "escalate_task",
     "description": "A routed model failed: get the next pick, using the failure as evidence the task is harder.",
     "inputSchema": {"type": "object", "required": ["trace_id", "failed_model_id"], "properties": {
         "trace_id": {"type": "string"}, "failed_model_id": {"type": "string"}}}},
    {"name": "record_outcome",
     "description": "Report whether the chosen model succeeded, so routing can be calibrated.",
     "inputSchema": {"type": "object", "required": ["trace_id", "model_id", "success"], "properties": {
         "trace_id": {"type": "string"}, "model_id": {"type": "string"}, "success": {"type": "boolean"},
         "cost_usd": {"type": "number", "minimum": 0}, "latency_ms": {"type": "number", "minimum": 0},
         "notes": {"type": "string"}}}},
    {"name": "list_models",
     "description": "List the model cards in the pool: id, provider, model, cost, local, description.",
     "inputSchema": {"type": "object", "properties": {}}},
]


def _summary(r: dict) -> str:
    top = next((x for x in r["ranking"] if x["model_id"] == r["choice"]["model_id"]), r["ranking"][0])
    return (f"model={r['choice']['model_id']} P(success)={top['p_success']:.3f} "
            f"difficulty={r['difficulty']['level']} category={r['category']['label']} trace_id={r['trace_id']}")


def _route_request(a: dict) -> dict:
    if not isinstance(a.get("task_text"), str):
        raise RequestError("task_text (string) is required")
    task = {"text": a["task_text"], **({"context": a["context"]} if a.get("context") else {})}
    req: dict = {"task": task, "return_top_k": a.get("top_k", 3)}
    if a.get("pool"):
        req["pool"] = a["pool"]
    prefs = {k: a[x] for k, x in (("mode", "mode"), ("min_p_success", "min_p_success")) if x in a}
    cons = {k: a[k] for k in ("max_cost_usd", "local_only", "require", "exclude") if k in a}
    return {**req, **({"preferences": prefs} if prefs else {}), **({"constraints": cons} if cons else {})}


def call_tool(router: Router, name: str, a: dict) -> tuple[str, dict]:
    if name == "route_task":
        r = router.route(_route_request(a))
        return _summary(r), r
    if name == "escalate_task":
        rec = router.store.route_record(a.get("trace_id", ""))
        if not rec or not a.get("failed_model_id"):
            raise RequestError("unknown trace_id (routes must be logged) or missing failed_model_id")
        r = router.escalate(rec["request"], rec["response"], a["failed_model_id"])
        return _summary(r), r
    if name == "record_outcome":
        out = {k: a[k] for k in ("trace_id", "model_id", "success") if k in a}
        for src, dst in (("cost_usd", "actual_cost_usd"), ("latency_ms", "actual_latency_ms")):
            if src in a:
                out[dst] = a[src]
        if a.get("notes"):
            out["signals"] = {"review_verdict": str(a["notes"])[:500]}
        r = router.record_outcome(out)
        return f"recorded outcome for {out['trace_id']} (id={r['id']})", r
    if name == "list_models":
        cards = [{"id": c["id"], "provider": c.get("provider"), "model": c.get("model"),
                  "cost": c.get("cost"), "local": bool(c.get("local")), "description": c.get("description")}
                 for c in router.matcher.cards.values()]
        return "\n".join(f"{c['id']} ({c['provider']})" for c in cards), {"models": cards}
    raise KeyError(name)


def handle(router: Router, msg: dict) -> dict | None:
    """One JSON-RPC message -> reply (None for notifications)."""
    mid, method, params = msg.get("id"), msg.get("method"), msg.get("params") or {}
    if mid is None:
        return None  # notifications/initialized etc.

    def ok(result): return {"jsonrpc": "2.0", "id": mid, "result": result}
    def err(code, m): return {"jsonrpc": "2.0", "id": mid, "error": {"code": code, "message": m}}

    if method == "initialize":
        return ok({"protocolVersion": PROTOCOL, "capabilities": {"tools": {}},
                   "serverInfo": {"name": "panda-router", "version": "0.1.0"}})
    if method == "ping":
        return ok({})
    if method == "tools/list":
        return ok({"tools": TOOLS})
    if method == "tools/call":
        try:
            text, data = call_tool(router, params.get("name"), params.get("arguments") or {})
            return ok({"content": [{"type": "text", "text": text}], "structuredContent": data})
        except KeyError:
            return err(-32602, f"unknown tool {params.get('name')!r}")
        except RequestError as e:  # tool-level failure: visible to the model, not a protocol error
            return ok({"content": [{"type": "text", "text": f"error: {e}"}], "isError": True})
        except Exception as e:  # noqa: BLE001
            print(f"[panda-router-mcp] {type(e).__name__}: {e}", file=sys.stderr)
            return ok({"content": [{"type": "text", "text": f"internal error: {type(e).__name__}"}], "isError": True})
    return err(-32601, f"method not found: {method}")


def build_router(argv: list[str] | None = None) -> Router:
    ap = argparse.ArgumentParser(prog="python -m panda_router.mcp", description="Panda Router MCP server (stdio)")
    ap.add_argument("--artifacts", default=os.environ.get("PANDA_ROUTER_ARTIFACTS"))
    ap.add_argument("--cards", default=os.environ.get("PANDA_ROUTER_CARDS"))
    ap.add_argument("--db", default=os.environ.get("PANDA_ROUTER_DB"))
    args = ap.parse_args(argv)
    art = args.artifacts or (DEFAULT_ARTIFACTS if DEFAULT_ARTIFACTS.exists() else None)
    if art is None:
        print(f"[panda-router-mcp] WARNING: {DEFAULT_ARTIFACTS} not found; using the weaker heuristic profiler",
              file=sys.stderr)
    router = Router(profiler=load_profiler(art), db_path=args.db, cards_dir=args.cards)
    print(f"[panda-router-mcp] ready (profiler={profiler_name(router.profiler)})", file=sys.stderr, flush=True)
    return router


def main(argv: list[str] | None = None) -> None:
    router = build_router(argv)
    for line in sys.stdin:
        if not line.strip():
            continue
        try:
            msg = json.loads(line)
            reply = handle(router, msg) if isinstance(msg, dict) else \
                {"jsonrpc": "2.0", "id": None, "error": {"code": -32600, "message": "invalid request"}}
        except json.JSONDecodeError:
            reply = {"jsonrpc": "2.0", "id": None, "error": {"code": -32700, "message": "parse error"}}
        if reply is not None:
            sys.stdout.write(json.dumps(reply) + "\n")
            sys.stdout.flush()
