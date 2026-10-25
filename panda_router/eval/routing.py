"""Routing metrics: route every task with the label profile (oracle) and with a predicted profile
through the real matcher (panda_router.matcher) over random card pools, then score the predicted
pick under the oracle's view of the world.

For each (task, pool, mode):
- oracle pick o = matcher(label profile), predicted pick q = matcher(predicted profile);
- oracle-side values for every card in the pool come from the oracle route with top_k = |pool|
  (utility U, p_success P, quality Q, est cost C); cards the oracle filters out (e.g. no tools when
  the task needs tools) are infeasible: P = Q = 0, U = min feasible U - 1;
- agreement = [q == o]; utility regret = U[o] - U[q] (can be < 0 in cheapest_above_threshold,
  whose objective is cost-to-success, not U); cost ratio = sum C[q] / sum C[o];
  P(success)-weighted quality = mean P[q]·Q[q]; also mean P[q], the infeasible-pick rate and the
  rate of picks whose oracle P(success) is below min_p_success (0.75).
Fixed-pick baselines (always-strongest, always-cheapest) are scored the same way.
"""

from __future__ import annotations

import json
import random
import tempfile
from pathlib import Path

import numpy as np

from ..profile import TaskProfile
from ..taxonomy import SKILL_AXES

ROOT = Path(__file__).resolve().parent.parent.parent
CARDS_DIR = ROOT / "cards"
MIN_P = 0.75  # matcher default min_p_success: oracle P(success) of the pick below this counts as a miss


def synthetic_cards(n: int = 16, seed: int = 0) -> list[dict]:
    """Synthetic but schema-valid cards: a quality ladder with price roughly exponential in ability."""
    rng = random.Random(seed)
    cards = []
    for i in range(n):
        base = 3.0 + 6.0 * i / max(1, n - 1) + rng.uniform(-0.5, 0.5)
        price_out = round(0.2 * 2.2 ** ((base - 3.0) / 1.0) * rng.uniform(0.7, 1.3), 4)
        cards.append({
            "id": f"syn-{i:02d}", "description": f"synthetic card {i}",
            "skills": {ax: {"theta": round(min(10.0, max(0.0, base + rng.gauss(0, 0.7))), 2), "se": round(rng.uniform(0.3, 1.2), 2)}
                       for ax in SKILL_AXES},
            "discrimination": round(rng.uniform(0.9, 1.6), 2),
            "modalities": {"input": ["text", "image"] if rng.random() < 0.6 else ["text"], "output": ["text"]},
            "features": {"tools": rng.random() < 0.85, "json_mode": True},
            "limits": {"context_tokens": rng.choice([32000, 128000, 200000, 1000000]), "max_output_tokens": 32000},
            "cost": {"input_per_mtok": round(price_out / 4, 4), "output_per_mtok": price_out, "currency": "USD"},
            "latency": {"ttft_ms_p50": rng.randint(300, 3000), "tokens_per_sec": rng.randint(20, 200)},
            "local": False,
        })
    return cards


def card_strength(card: dict) -> float:
    sk = card.get("skills") or {}
    return float(np.mean([sk[a]["theta"] for a in sk])) if sk else 5.0


def card_price(card: dict) -> float:
    c = card["cost"]
    return float(c["input_per_mtok"]) + float(c["output_per_mtok"])


class RoutingEvaluator:
    def __init__(self, cards_dir: str | Path | None = None, n_pools: int = 500, pools_per_task: int | None = 50,
                 min_cards: int = 2, max_cards: int = 12, modes: tuple[str, ...] | None = None, seed: int = 0):
        from ..matcher import MODES, Matcher, load_cards

        self.modes = tuple(modes or MODES)
        cards_dir = Path(cards_dir) if cards_dir else CARDS_DIR
        self._tmp = None
        if cards_dir.exists() and any(cards_dir.glob("*.json")):
            self.card_source = str(cards_dir)
        else:
            self._tmp = tempfile.TemporaryDirectory(prefix="panda-eval-cards-")
            for c in synthetic_cards(seed=seed):
                (Path(self._tmp.name) / f"{c['id']}.json").write_text(json.dumps(c))
            cards_dir = Path(self._tmp.name)
            self.card_source = "synthetic"
        self.matcher = Matcher(cards_dir=cards_dir)
        self.cards = load_cards(cards_dir)
        ids = sorted(self.cards)
        rng = random.Random(seed)
        hi = min(max_cards, len(ids))
        lo = min(min_cards, hi)
        self.pools = [sorted(rng.sample(ids, rng.randint(lo, hi))) for _ in range(n_pools)]
        self.pools_per_task = pools_per_task
        self.seed = seed

    def assignments(self, n_tasks: int) -> list[list[int]]:
        """pool index -> task indices routed on it."""
        rng = random.Random(self.seed + 1)
        by_pool: list[list[int]] = [[] for _ in self.pools]
        k = len(self.pools) if self.pools_per_task is None else min(self.pools_per_task, len(self.pools))
        for t in range(n_tasks):
            for j in rng.sample(range(len(self.pools)), k):
                by_pool[j].append(t)
        return by_pool

    def _request(self, task: dict, pool: list[str], mode: str) -> dict:
        return {"task": task, "pool": pool, "preferences": {"mode": mode}, "return_top_k": len(pool)}

    def evaluate(self, tasks: list[dict], oracle: list[TaskProfile], predicted: dict[str, list[TaskProfile]],
                 include_fixed_baselines: bool = True) -> dict:
        """predicted: name -> per-task TaskProfiles. Returns metrics[name][mode] (+ 'all')."""
        names = list(predicted)
        fixed = ["always_strongest", "always_cheapest"] if include_fixed_baselines else []
        acc = {n: {m: _Acc() for m in self.modes} for n in names + fixed}
        for j, tidx in enumerate(self.assignments(len(tasks))):
            if not tidx:
                continue
            pool = self.pools[j]
            strongest = max(pool, key=lambda i: (card_strength(self.cards[i]), i))
            cheapest = min(pool, key=lambda i: (card_price(self.cards[i]), i))
            for t in tidx:
                for mode in self.modes:
                    req = self._request(tasks[t], pool, mode)
                    o = self.matcher.route(req, oracle[t], trace_id="eval")
                    o_pick = o["choice"]["model_id"]
                    if o_pick is None:
                        continue
                    vals = {r["model_id"]: r for r in o["ranking"]}
                    u_floor = min(r["utility"] for r in vals.values()) - 1.0
                    picks = {n: self.matcher.route(req, predicted[n][t], trace_id="eval")["choice"]["model_id"] for n in names}
                    picks.update({"always_strongest": strongest, "always_cheapest": cheapest} if fixed else {})
                    for n, q in picks.items():
                        acc[n][mode].add(o_pick, q, vals, u_floor, tasks[t], self.cards)
        out = {}
        for n in acc:
            out[n] = {m: acc[n][m].summary() for m in self.modes}
            merged = _Acc.merge(list(acc[n].values()))
            out[n]["all"] = merged.summary()
        return {"card_source": self.card_source, "n_pools": len(self.pools), "pools_per_task": self.pools_per_task,
                "modes": list(self.modes), "metrics": out}


class _Acc:
    def __init__(self):
        self.agree, self.regret, self.p, self.pq, self.infeasible = [], [], [], [], []
        self.cost_q, self.cost_o, self.p_oracle, self.pq_oracle = [], [], [], []
        self.below = []

    def add(self, o_pick, q_pick, vals, u_floor, task, cards):
        from ..matcher import estimate_input_tokens

        ro = vals[o_pick]
        rq = vals.get(q_pick) if q_pick is not None else None
        self.agree.append(float(q_pick == o_pick))
        self.p_oracle.append(ro["p_success"])
        self.pq_oracle.append(ro["p_success"] * ro["quality"])
        self.cost_o.append(ro["est_cost_usd"])
        self.below.append(float(rq is None or rq["p_success"] < MIN_P))
        if rq is None:
            self.infeasible.append(1.0)
            self.regret.append(ro["utility"] - u_floor)
            self.p.append(0.0)
            self.pq.append(0.0)
            # Infeasible pick: price it with the oracle's token estimate.
            self.cost_q.append(_cost_like(ro, cards, o_pick, q_pick, estimate_input_tokens(task)) if q_pick else 0.0)
            return
        self.infeasible.append(0.0)
        self.regret.append(ro["utility"] - rq["utility"])
        self.p.append(rq["p_success"])
        self.pq.append(rq["p_success"] * rq["quality"])
        self.cost_q.append(rq["est_cost_usd"])

    @staticmethod
    def merge(accs: list["_Acc"]) -> "_Acc":
        m = _Acc()
        for a in accs:
            for k, v in a.__dict__.items():
                getattr(m, k).extend(v)
        return m

    def summary(self) -> dict:
        if not self.agree:
            return {"n": 0}
        f = lambda xs: round(float(np.mean(xs)), 5)  # noqa: E731
        so = float(np.sum(self.cost_o))
        return {
            "n": len(self.agree),
            "pick_agreement": f(self.agree),
            "utility_regret": f(self.regret),
            "cost_ratio": round(float(np.sum(self.cost_q)) / so, 4) if so > 0 else None,
            "p_success": f(self.p), "p_success_oracle": f(self.p_oracle),
            "pq_quality": f(self.pq), "pq_quality_oracle": f(self.pq_oracle),
            "infeasible_rate": f(self.infeasible),
            "below_min_p_rate": f(self.below),
        }


def _cost_like(ro: dict, cards: dict, o_pick: str, q_pick: str, in_tok: int) -> float:
    """Price q_pick for the same token budget the oracle row implies for o_pick."""
    co, cq = cards[o_pick]["cost"], cards[q_pick]["cost"]
    cin_o, cout_o = co["input_per_mtok"], co["output_per_mtok"]
    out_tok = max(0.0, (ro["est_cost_usd"] * 1e6 - in_tok * cin_o) / cout_o) if cout_o > 0 else 0.0
    return (in_tok * cq["input_per_mtok"] + out_tok * cq["output_per_mtok"]) / 1e6
