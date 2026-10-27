"""Router: Profiler + Matcher + outcome log."""

from __future__ import annotations

import os
import sys
import time
from collections import OrderedDict
from pathlib import Path

from ..heuristic import HeuristicProfiler
from ..matcher import Matcher, new_trace_id, schema_errors
from ..profile import Profiler, TaskProfile
from .store import Store


ROOT = Path(__file__).resolve().parents[2]
DEFAULT_ARTIFACTS = ROOT / "artifacts" / "panda-router-v4"
ARTIFACTS_ENV = "PANDA_ROUTER_ARTIFACTS"


def default_artifacts() -> str | None:
    """$PANDA_ROUTER_ARTIFACTS, else the shipped v4 profiler if present (else None -> heuristic)."""
    return os.environ.get(ARTIFACTS_ENV) or (str(DEFAULT_ARTIFACTS) if DEFAULT_ARTIFACTS.exists() else None)


class RequestError(ValueError):
    """Invalid client input (maps to HTTP 400)."""


def load_profiler(path_or_none: str | Path | None, fallback: bool = False) -> Profiler:
    """ONNX profiler from an artifacts dir if given; the heuristic profiler if no dir is given.

    An explicitly requested artifacts dir that fails to load raises, unless ``fallback=True``.
    """
    if path_or_none:
        try:
            from ..model.onnx_profiler import OnnxProfiler  # lazy: optional dependency

            return OnnxProfiler(str(path_or_none))
        except Exception as e:  # noqa: BLE001
            if not fallback:
                raise RuntimeError(f"cannot load ONNX profiler from {path_or_none}: {type(e).__name__}: {e}") from e
            print(f"[panda-router] ONNX profiler unavailable ({type(e).__name__}: {e}); using heuristic",
                  file=sys.stderr)
    return HeuristicProfiler()


def profiler_name(profiler: Profiler) -> str:
    return getattr(profiler, "name", None) or type(profiler).__name__


class Router:
    def __init__(self, profiler: Profiler | None = None, matcher: Matcher | None = None,
                 db_path: str | Path | None = None, cards_dir: str | Path | None = None, log_routes: bool = True):
        self.profiler = profiler or HeuristicProfiler()
        self.matcher = matcher or Matcher(cards_dir)
        self.store = Store(db_path)
        self.log_routes = log_routes
        self._profiles: OrderedDict[str, TaskProfile] = OrderedDict()

    def _remember(self, trace_id: str, profile: TaskProfile) -> None:
        self._profiles[trace_id] = profile
        if len(self._profiles) > 1024:
            self._profiles.popitem(last=False)

    def _check(self, obj: dict, schema: str) -> None:
        if not isinstance(obj, dict):
            raise RequestError(f"{schema} must be a JSON object")
        if errs := schema_errors(obj, schema):
            raise RequestError(f"invalid {schema}: {'; '.join(errs[:5])}")

    def route(self, request: dict) -> dict:
        self._check(request, "route_request")
        t0 = time.perf_counter()
        trace_id = new_trace_id()
        profile = self.profiler.profile(request["task"])
        try:
            resp = self.matcher.route(request, profile, trace_id=trace_id, profiler_name=profiler_name(self.profiler))
        except ValueError as e:
            raise RequestError(str(e)) from e
        resp["router"]["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        self._remember(trace_id, profile)
        if self.log_routes:
            self.store.log_route(request, resp)
        return resp

    def escalate(self, request: dict, response: dict, failed_model_id: str) -> dict:
        self._check(request, "route_request")
        t0 = time.perf_counter()
        profile = self._profiles.get(response.get("trace_id", "")) or self.profiler.profile(request["task"])
        trace_id = new_trace_id()
        try:
            resp = self.matcher.escalate(request, profile, response, failed_model_id, trace_id=trace_id,
                                         profiler_name=profiler_name(self.profiler))
        except ValueError as e:
            raise RequestError(str(e)) from e
        resp["router"]["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        self._remember(trace_id, profile)
        if self.log_routes:
            self.store.log_route(request, resp)
        return resp

    def record_outcome(self, outcome: dict) -> dict:
        self._check(outcome, "route_outcome")
        row = self.store.log_outcome(outcome)
        return {"ok": True, "id": row, "trace_id": outcome["trace_id"]}

    def health(self) -> dict:
        cards = self.matcher.cards
        return {"ok": True, "version": self.matcher.version, "profiler": profiler_name(self.profiler),
                "cards": len(cards), "db": str(self.store.path), "policy": self.matcher.policy,
                "success_head": self.matcher.success_head.name if self.matcher.success_head else None}
