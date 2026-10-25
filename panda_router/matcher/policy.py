"""Deterministic routing policy: filter -> P(success) -> utility -> mode -> floor/fallback (PLAN.md section 4)."""

from __future__ import annotations

import hashlib
import json
import random
import time
import uuid
from pathlib import Path

import numpy as np

from .. import __version__
from ..profile import TaskProfile
from .cards import PoolCache, load_cards, validate_card
from .core import (ability_moments, axis_weights, difficulty_posterior_after_failure, expected_skills,
                   p_by_level)

MODES = ("cheapest_above_threshold", "max_utility", "max_quality")
DEFAULTS = {
    "mode": "cheapest_above_threshold",
    "min_p_success": 0.75,
    "floor": 0.55,
    "weights": {"quality": 1.0, "cost": 0.3, "latency": 0.1},
    "explore_epsilon": 0.0,
    "explore_temperature": 0.1,
}
DEFAULT_MODEL = "claude-opus-5.5"
CONTEXT_MARGIN = 1.2
DEFAULT_TOP_K = 3
INPUT_OVERHEAD_TOKENS = 500


def new_trace_id() -> str:
    return "r_" + uuid.uuid4().hex[:24]


def estimate_input_tokens(task: dict) -> int:
    ctx = task.get("context") or {}
    if ctx.get("estimated_input_tokens") is not None:
        return int(ctx["estimated_input_tokens"])
    return len(task.get("text") or "") // 4 + INPUT_OVERHEAD_TOKENS


def _norm(x: np.ndarray) -> np.ndarray:
    m = float(x.max()) if x.size else 0.0
    return x / m if m > 0 else np.zeros_like(x)


class Matcher:
    def __init__(self, cards_dir: str | Path | None = None, default_model: str = DEFAULT_MODEL,
                 floor: float = DEFAULTS["floor"], version: str | None = None):
        self.cards_dir = cards_dir
        self.default_model = default_model
        self.floor = floor
        self.version = version or f"panda-router-{__version__}"
        self._pools = PoolCache()
        self._resolved: dict[tuple, tuple] = {}

    @property
    def cards(self) -> dict[str, dict]:
        return load_cards(self.cards_dir)

    def resolve_pool(self, pool_spec: list | None):
        """Returns (Pool, unknown_ids). Inline cards are validated; ids are looked up in cards_dir."""
        known = self.cards
        key = tuple(i if isinstance(i, str) else json.dumps(i, sort_keys=True) for i in pool_spec or ())
        if (hit := self._resolved.get(key)) is not None and hit[0] is known:
            return hit[1], hit[2]
        if not pool_spec:
            self._resolved[key] = (known, self._pools.get(list(known.values())), [])
            return self._resolved[key][1:]
        cards, unknown, seen = [], [], set()
        for item in pool_spec:
            if isinstance(item, dict):
                validate_card(item)
                card = item
            elif item in known:
                card = known[item]
            else:
                unknown.append(item)
                continue
            if card["id"] not in seen:
                seen.add(card["id"])
                cards.append(card)
        if not cards:
            raise ValueError(f"empty pool after resolution (unknown ids: {unknown})")
        if len(self._resolved) >= 256:
            self._resolved.clear()
        self._resolved[key] = (known, self._pools.get(cards), unknown)
        return self._resolved[key][1:]

    # ------------------------------------------------------------------ routing
    def route(self, request: dict, profile: TaskProfile, trace_id: str | None = None,
              profiler_name: str | None = None) -> dict:
        return self._route(request, profile, trace_id=trace_id, profiler_name=profiler_name)

    def escalate(self, request: dict, profile: TaskProfile, response: dict, failed_model_id: str,
                 trace_id: str | None = None, profiler_name: str | None = None) -> dict:
        """Cascade with a difficulty posterior: the failure is evidence that b exceeds the failed model's
        ability. post(b) ∝ prior(b) · P_fail(b), then re-route without the failed model(s)."""
        pool, _ = self.resolve_pool(request.get("pool"))
        if failed_model_id not in pool.ids:
            raise ValueError(f"failed model {failed_model_id!r} is not in the pool")
        prior = np.asarray((response.get("difficulty") or {}).get("distribution") or profile.difficulty, float)
        prior = prior / prior.sum()
        exp = expected_skills(profile.skills)
        w = axis_weights(exp)
        i = pool.index(failed_model_id)
        mu, sd = ability_moments(w, exp, pool.theta[i:i + 1], pool.se[i:i + 1])
        post = difficulty_posterior_after_failure(prior, p_by_level(mu, sd, pool.a[i:i + 1])[0])
        failed = list((response.get("escalation") or {}).get("failed_models", [])) + [failed_model_id]
        escalation = {"parent_trace_id": response.get("trace_id"), "failed_models": failed,
                      "prior_difficulty": [round(float(p), 6) for p in prior],
                      "posterior_difficulty": [round(float(p), 6) for p in post]}
        return self._route(request, profile, difficulty=post, failed=failed, escalation=escalation,
                           trace_id=trace_id, profiler_name=profiler_name)

    def _route(self, request: dict, profile: TaskProfile, difficulty=None, failed=(), escalation=None,
               trace_id: str | None = None, profiler_name: str | None = None) -> dict:
        t0 = time.perf_counter()
        trace_id = trace_id or new_trace_id()
        task = request.get("task") or {}
        ctx = task.get("context") or {}
        cons = request.get("constraints") or {}
        prefs = {**DEFAULTS, "floor": self.floor, **(request.get("preferences") or {})}
        weights = {**DEFAULTS["weights"], **(prefs.get("weights") or {})}
        mode = prefs["mode"]
        if mode not in MODES:
            raise ValueError(f"unknown mode {mode!r}")
        floor, min_p = float(prefs["floor"]), float(prefs["min_p_success"])
        default_model = prefs.get("default_model") or self.default_model

        pool, unknown = self.resolve_pool(request.get("pool"))
        n = len(pool.ids)

        # --- P(success) for every card (vectorised).
        diff = np.asarray(profile.difficulty if difficulty is None else difficulty, dtype=float)
        diff = diff / diff.sum()
        exp = expected_skills(profile.skills)
        w = axis_weights(exp)
        mu, sd = ability_moments(w, exp, pool.theta, pool.se)
        p = np.clip(p_by_level(mu, sd, pool.a) @ diff, 0.0, 1.0)
        quality = np.clip(mu / 10.0, 0.0, 1.0)

        # --- cost / latency.
        in_tok = estimate_input_tokens(task)
        out_tok = 10.0 ** float(profile.out_tokens_log10.get("p50", 3.0))
        cost = (in_tok * pool.cost_in + out_tok * pool.cost_out) / 1e6
        latency = pool.ttft_ms + out_tok / pool.tps * 1000.0

        # --- hard filters.
        flags = profile.flags
        needs_tools = max(flags.get("needs_tools", 0.0), 1.0 if ctx.get("requires_tools") else 0.0) > 0.5
        needs_vision = max(flags.get("needs_vision", 0.0), 1.0 if ctx.get("has_images") else 0.0) > 0.5
        require = set(cons.get("require") or [])
        exclude = set(cons.get("exclude") or [])
        max_cost, max_lat = cons.get("max_cost_usd"), cons.get("max_latency_ms")
        feature = {"tools": pool.tools, "vision": pool.vision, "json_mode": pool.json_mode, "web": pool.web}
        filtered_out = [{"model_id": m, "reason": "unknown_model"} for m in unknown]
        cand = []
        for i, mid in enumerate(pool.ids):
            r = []
            if mid in failed:
                r.append("escalation:failed")
            if mid in exclude:
                r.append("constraint:exclude")
            if cons.get("local_only") and not pool.local[i]:
                r.append("constraint:local_only")
            r += [f"constraint:require={f}" for f in sorted(require) if f in feature and not feature[f][i]]
            if needs_tools and not pool.tools[i] and "tools" not in require:
                r.append("profile:needs_tools")
            if needs_vision and not pool.vision[i] and "vision" not in require:
                r.append("profile:needs_vision")
            if in_tok * CONTEXT_MARGIN > pool.context[i]:
                r.append("limit:context")
            if max_cost is not None and cost[i] > max_cost:
                r.append("constraint:max_cost_usd")
            if max_lat is not None and latency[i] > max_lat:
                r.append("constraint:max_latency_ms")
            if r:
                filtered_out.append({"model_id": mid, "reason": ";".join(r)})
            else:
                cand.append(i)
        cand_idx = np.array(cand, dtype=int)

        # --- utility over candidates.
        util = np.full(n, -np.inf)
        if cand:
            util[cand_idx] = (weights["quality"] * quality[cand_idx] * p[cand_idx]
                              - weights["cost"] * _norm(cost[cand_idx])
                              - weights["latency"] * _norm(latency[cand_idx]))
        cts = cost / np.maximum(p, 1e-6)

        # --- mode, floor, fallback.
        fb = {"triggered": False, "floor": floor, "default_model": default_model if default_model in pool.ids else None}
        greedy, decided_by, eligible = None, None, []
        if not cand:
            decided_by = "none:all_filtered"
            fb.update(triggered=True, reason="all_candidates_filtered")
        else:
            eligible = [i for i in cand if p[i] >= floor]
            if not eligible:
                fb["triggered"] = True
                if default_model in pool.ids and pool.index(default_model) in cand:
                    greedy, decided_by = pool.index(default_model), "fallback:default_model"
                    fb["reason"] = "no_candidate_above_floor"
                else:
                    greedy = max(cand, key=lambda i: (p[i], -i))
                    decided_by = "fallback:best_available"
                    fb["reason"] = "no_candidate_above_floor;default_model_unavailable"
            elif mode == "cheapest_above_threshold":
                above = [i for i in eligible if p[i] >= min_p]
                if above:
                    greedy = min(above, key=lambda i: (cts[i], cost[i], -p[i], i))
                    decided_by = "policy:cheapest_above_threshold"
                else:
                    greedy = max(eligible, key=lambda i: (p[i], -cost[i], -i))
                    decided_by = "policy:cheapest_above_threshold:relaxed_to_max_quality"
            elif mode == "max_utility":
                greedy = max(eligible, key=lambda i: (util[i], -i))
                decided_by = "policy:max_utility"
            else:
                greedy = max(eligible, key=lambda i: (p[i], -cost[i], -i))
                decided_by = "policy:max_quality"

        # --- optional exploration (softmax over utility among floor-clearing candidates).
        chosen, propensity, explored = greedy, 1.0, False
        eps = float(prefs.get("explore_epsilon") or 0.0)
        if greedy is not None and not fb["triggered"] and eps > 0 and len(eligible) > 1:
            temp = float(prefs["explore_temperature"])
            u = np.array([util[i] for i in eligible]) / temp
            soft = np.exp(u - u.max())
            soft /= soft.sum()
            seed = prefs.get("seed")
            if seed is None:
                seed = int(hashlib.sha256(trace_id.encode()).hexdigest()[:12], 16)
            rng = random.Random(seed)
            if rng.random() < eps:
                explored = True
                chosen = eligible[min(int(np.searchsorted(np.cumsum(soft), rng.random())), len(eligible) - 1)]
            j = eligible.index(chosen)
            propensity = (1.0 - eps) * (chosen == greedy) + eps * float(soft[j])
            if explored:
                decided_by = f"explore:softmax(eps={eps:g})"

        # --- ranking (chosen first, then the escalation ladder by p_success).
        top_k = int(request.get("return_top_k") or DEFAULT_TOP_K)
        order = sorted(cand, key=lambda i: (-p[i], cost[i], i))
        if chosen is not None:
            order = [chosen] + [i for i in order if i != chosen]

        def row(i):
            return {"model_id": pool.ids[i], "p_success": round(float(p[i]), 4),
                    "quality": round(float(quality[i]), 4), "utility": round(float(util[i]), 4),
                    "est_cost_usd": round(float(cost[i]), 6), "est_cost_to_success_usd": round(float(cts[i]), 6),
                    "est_latency_ms": round(float(latency[i]), 1)}

        level = int(np.argmax(diff)) + 1
        cat_label, cat_p = profile.top_category()
        resp = {
            "choice": {"model_id": pool.ids[chosen] if chosen is not None else None,
                       "confidence": round(float(p[chosen]), 4) if chosen is not None else 0.0,
                       "decided_by": decided_by, "propensity": round(float(propensity), 6), "explored": explored},
            "ranking": [row(i) for i in order[:top_k]],
            "filtered_out": filtered_out,
            "difficulty": {"level": level, "expected": round(float(diff @ np.arange(1, 11)), 3),
                           "distribution": [round(float(x), 6) for x in diff]},
            "category": {"label": cat_label, "p": round(float(cat_p), 4)},
            "flags": {k: round(float(v), 4) for k, v in flags.items()},
            "fallback": fb,
            "router": {"version": self.version, "profiler": profiler_name or "external",
                       "latency_ms": 0.0, "pool_hash": pool.hash},
            "trace_id": trace_id,
        }
        if escalation is not None:
            resp["escalation"] = escalation
        if "profile" in (request.get("questions") or []):
            resp["profile"] = profile.to_dict()
        resp["router"]["latency_ms"] = round((time.perf_counter() - t0) * 1000.0, 3)
        return resp


_DEFAULT: Matcher | None = None


def default_matcher() -> Matcher:
    global _DEFAULT
    if _DEFAULT is None:
        _DEFAULT = Matcher()
    return _DEFAULT


def route(request: dict, profile: TaskProfile, **kw) -> dict:
    return default_matcher().route(request, profile, **kw)


def escalate(request: dict, profile: TaskProfile, response: dict, failed_model_id: str,
             matcher: Matcher | None = None, **kw) -> dict:
    return (matcher or default_matcher()).escalate(request, profile, response, failed_model_id, **kw)


__all__ = ["Matcher", "route", "escalate", "default_matcher", "new_trace_id", "estimate_input_tokens"]
