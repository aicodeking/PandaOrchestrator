"""python -m panda_router.serve --port 8765 [--artifacts DIR] [--db PATH] [--cards DIR]"""

from __future__ import annotations

import argparse
import sys

from .router import Router, load_profiler, profiler_name
from .server import make_server


def main(argv: list[str] | None = None) -> None:
    ap = argparse.ArgumentParser(prog="python -m panda_router.serve", description="Panda Router HTTP server")
    ap.add_argument("--host", default="127.0.0.1")
    ap.add_argument("--port", type=int, default=8765)
    ap.add_argument("--artifacts", default=None, help="ONNX profiler artifacts dir (default: heuristic profiler)")
    ap.add_argument("--db", default=None, help="SQLite log path (default: $PANDA_ROUTER_DB or data/cache/router_log.sqlite)")
    ap.add_argument("--cards", default=None, help="cards directory (default: cards/)")
    args = ap.parse_args(argv)
    router = Router(profiler=load_profiler(args.artifacts), db_path=args.db, cards_dir=args.cards)
    srv = make_server(router, args.host, args.port)
    print(f"[panda-router] listening on http://{args.host}:{srv.server_port} "
          f"(profiler={profiler_name(router.profiler)}, db={router.store.path})", file=sys.stderr, flush=True)
    try:
        srv.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        srv.server_close()


if __name__ == "__main__":
    main()
