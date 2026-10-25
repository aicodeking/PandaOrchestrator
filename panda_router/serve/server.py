"""Stdlib HTTP server: POST /route, POST /escalate, POST /outcome, GET /health."""

from __future__ import annotations

import json
import sys
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

from .router import RequestError, Router

MAX_BODY = 4 * 1024 * 1024


def make_server(router: Router, host: str = "127.0.0.1", port: int = 8765) -> ThreadingHTTPServer:
    class Handler(BaseHTTPRequestHandler):
        server_version = "PandaRouter/0.1"

        def log_message(self, fmt, *args):  # keep stdout quiet; errors still go to stderr
            pass

        def _send(self, code: int, body: dict) -> None:
            data = json.dumps(body).encode()
            self.send_response(code)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(data)))
            self.end_headers()
            self.wfile.write(data)

        def do_GET(self):
            if self.path.rstrip("/") == "/health":
                return self._send(200, router.health())
            self._send(404, {"error": "not found"})

        def do_POST(self):
            routes = {"/route": lambda b: router.route(b),
                      "/outcome": lambda b: router.record_outcome(b),
                      "/escalate": lambda b: router.escalate(b.get("request"), b.get("response") or {},
                                                             b.get("failed_model_id"))}
            handler = routes.get(self.path.rstrip("/"))
            if handler is None:
                return self._send(404, {"error": "not found"})
            length = int(self.headers.get("Content-Length") or 0)
            if length > MAX_BODY:
                return self._send(413, {"error": "body too large"})
            try:
                body = json.loads(self.rfile.read(length) or b"null")
                if not isinstance(body, dict):
                    raise RequestError("body must be a JSON object")
                self._send(200, handler(body))
            except (json.JSONDecodeError, RequestError) as e:
                self._send(400, {"error": str(e)})
            except Exception as e:  # noqa: BLE001 - never crash the server thread
                print(f"[panda-router] internal error: {type(e).__name__}: {e}", file=sys.stderr)
                self._send(500, {"error": "internal error"})

    return ThreadingHTTPServer((host, port), Handler)
