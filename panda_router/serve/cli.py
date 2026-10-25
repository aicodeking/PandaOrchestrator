"""python -m panda_router.serve.cli route --task 'text' [--artifacts DIR] [--context JSON] [--mode M] [--pool a,b]"""

from __future__ import annotations

import argparse
import json
import sys

from .router import RequestError, Router, load_profiler


def main(argv: list[str] | None = None) -> int:
    ap = argparse.ArgumentParser(prog="python -m panda_router.serve.cli")
    sub = ap.add_subparsers(dest="cmd", required=True)
    r = sub.add_parser("route", help="route one task and print the RouteResponse JSON")
    r.add_argument("--task", required=True, help="task text")
    r.add_argument("--context", default=None, help="task.context as JSON")
    r.add_argument("--kind-hint", default=None)
    r.add_argument("--pool", default=None, help="comma-separated card ids (default: all cards)")
    r.add_argument("--mode", default=None, choices=["cheapest_above_threshold", "max_utility", "max_quality"])
    r.add_argument("--min-p", type=float, default=None)
    r.add_argument("--max-cost", type=float, default=None)
    r.add_argument("--local-only", action="store_true")
    r.add_argument("--top-k", type=int, default=3)
    r.add_argument("--profile", action="store_true", help="include the TaskProfile in the output")
    r.add_argument("--artifacts", default=None, help="ONNX profiler artifacts dir (default: heuristic)")
    r.add_argument("--cards", default=None)
    r.add_argument("--db", default=None)
    r.add_argument("--no-log", action="store_true", help="do not write the route to SQLite")
    args = ap.parse_args(argv)

    task = {"text": args.task}
    if args.context:
        task["context"] = json.loads(args.context)
    if args.kind_hint:
        task["kind_hint"] = args.kind_hint
    req: dict = {"task": task, "return_top_k": args.top_k}
    if args.pool:
        req["pool"] = [p.strip() for p in args.pool.split(",") if p.strip()]
    prefs = {k: v for k, v in {"mode": args.mode, "min_p_success": args.min_p}.items() if v is not None}
    if prefs:
        req["preferences"] = prefs
    cons = {k: v for k, v in {"max_cost_usd": args.max_cost, "local_only": args.local_only or None}.items() if v is not None}
    if cons:
        req["constraints"] = cons
    if args.profile:
        req["questions"] = ["choice", "difficulty", "flags", "profile"]

    router = Router(profiler=load_profiler(args.artifacts), db_path=args.db, cards_dir=args.cards,
                    log_routes=not args.no_log)
    try:
        print(json.dumps(router.route(req), indent=2))
    except RequestError as e:
        print(json.dumps({"error": str(e)}), file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
