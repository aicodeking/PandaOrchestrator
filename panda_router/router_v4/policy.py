"""v4 decision rules (pure numpy; shared by matcher.Matcher and the train/val tuning simulator).

Expected cost including failure:  E_m = c_m + (1 - P_m) * F_m,  F_m = c_next(m) + L
where c_next(m) is the cost of the escalation step after m fails (the most-likely-to-pass other candidate) and L is
a retry/latency penalty in $ (tuned on train/val). Decisions use the LOWER bound of the calibrated P (head:
Platt(mean - z sd); uncovered cards: shrunk card prior, see shrunk_card_p), so the policy over-estimates difficulty modestly;
the calibrated P itself is what the response displays.

Modes (see choose; v4.2: every mode searches all eligible cards, no anchor restriction):
  cheapest_above_threshold  min E among lower bound >= min_p; none -> max_quality pick (decided_by ':relaxed')
  max_utility               max P - w_cost * E / max(E) - w_lat * lat / max(lat)
  max_quality               max lower bound; within Q_TIE -> cheaper
A $0 candidate may only win if its P is within FREE_MARGIN of the best paid candidate's P.
"""

from __future__ import annotations

import numpy as np

FREE_MARGIN = 0.05
TIE_REL = 0.02  # E within 2% (or TIE_ABS $) of the minimum counts as a tie
TIE_ABS = 1e-5
PROVENANCE_PENALTY = {"verified": 0.0, "benchmark-informed": 0.5, "estimated": 1.0}  # logits, uncovered cards
FREE_PENALTY = 0.5  # extra logits for $0 / local uncovered cards


def logit(p):
    p = np.clip(np.asarray(p, float), 1e-6, 1 - 1e-6)
    return np.log(p / (1 - p))


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, float)))


def p_at_level(p_levels: np.ndarray, level: float) -> np.ndarray:
    """(N, 10) P(success | b = level) -> P at a fractional level (linear interpolation)."""
    lv = float(np.clip(level, 1.0, 10.0))
    lo = int(np.floor(lv)) - 1
    hi = min(lo + 1, 9)
    f = lv - (lo + 1)
    return (1 - f) * p_levels[:, lo] + f * p_levels[:, hi]


def card_prior_penalty(card: dict, free: bool) -> float:
    prov = (card.get("field_provenance") or {}).get("skills") or card.get("provenance") or "estimated"
    pen = PROVENANCE_PENALTY.get(prov, PROVENANCE_PENALTY["estimated"])
    return pen + (FREE_PENALTY if free or card.get("local") else 0.0)


def conservative_card_p(p_card_q: np.ndarray, alpha: float, beta: float, penalty: np.ndarray) -> np.ndarray:
    """Card P at the upper difficulty quantile, mapped onto the success head's outcome scale, minus a prior penalty."""
    return sigmoid(alpha + beta * logit(p_card_q) - penalty)


UNCOVERED_SHRINK = 0.5  # weight on the card/IRT estimate vs the task's covered-card median (not tuned: no outcomes)


def shrunk_card_p(p_card_q: np.ndarray, ref_card_q: np.ndarray, ref_p: np.ndarray, penalty: np.ndarray,
                  alpha: float, beta: float, shrink: float = UNCOVERED_SHRINK) -> np.ndarray:
    """Uncovered cards on the success head's scale for this task: card/IRT P mapped by the global card calibration
    (alpha + beta * logit), recentred on this task's covered cards (mean head logit - mean mapped card logit),
    shrunk toward the covered cards' median head logit (a conservative prior), minus the prior penalty and capped
    at the best covered card (an unproven card never exceeds the best evidence-backed one). Task- and card-dependent,
    so cards above the covered range no longer collapse to one flat number."""
    z, z_ref, y_ref = alpha + beta * logit(p_card_q), alpha + beta * logit(ref_card_q), logit(ref_p)
    est = z + (y_ref.mean() - z_ref.mean())
    return np.minimum(sigmoid(shrink * est + (1 - shrink) * np.median(y_ref) - penalty), ref_p.max())


def next_step_cost(p: np.ndarray, cost: np.ndarray, strength: np.ndarray) -> np.ndarray:
    """Cost of the escalation target if candidate i fails: the best other candidate by (P, strength)."""
    n = len(p)
    if n == 1:
        return cost.copy()
    order = sorted(range(n), key=lambda i: (-p[i], -strength[i], cost[i]))
    first, second = order[0], order[1]
    return np.array([cost[second] if i == first else cost[first] for i in range(n)])


def expected_cost(p: np.ndarray, cost: np.ndarray, strength: np.ndarray, penalty_usd: float) -> np.ndarray:
    return cost + (1.0 - p) * (next_step_cost(p, cost, strength) + penalty_usd)


def free_guard(p: np.ndarray, cost: np.ndarray, margin: float = FREE_MARGIN) -> np.ndarray:
    """Mask of candidates allowed to win: $0 ones only if within `margin` of the best paid P."""
    free = cost <= 0.0
    if free.all() or not free.any():
        return np.ones(len(p), bool)
    return ~free | (p >= p[~free].max() - margin)


P_TIE = 0.005  # P within this of the best counts as a tie (-> stronger card) for exact-cost / utility ties
Q_TIE = 0.01  # max_quality / relaxed threshold: lower bound within this of the best -> the cheaper card


def _stronger(idx, p, strength, cost):
    top = max(p[i] for i in idx)
    return max((i for i in idx if p[i] >= top - P_TIE), key=lambda i: (strength[i], p[i], cost[i], -i))


def _best_p_cheaper(idx, p, cost, strength):
    """Highest p over idx; p within Q_TIE of the best -> the cheaper card (then stronger)."""
    top = max(p[i] for i in idx)
    return min((i for i in idx if p[i] >= top - Q_TIE), key=lambda i: (cost[i], -strength[i], -p[i], i))


def _min_e(idx, E, p, strength, cost):
    e_min = min(E[i] for i in idx)
    return _stronger([i for i in idx if E[i] <= e_min * (1 + TIE_REL) + TIE_ABS], p, strength, cost)


def choose(mode: str, p: np.ndarray, cost: np.ndarray, latency: np.ndarray, strength: np.ndarray,
           min_p: float, penalty_usd: float, w_cost: float = 0.3, w_lat: float = 0.1,
           w_quality: float = 1.0, eq_margin: float = 0.0,
           p_mean: np.ndarray | None = None) -> tuple[int, str, np.ndarray, np.ndarray]:
    """-> (index, decided_by, utility, expected_cost) over the given candidate arrays. p = decision (lower) bound.

    All modes consider every candidate that passes the $0 guard:
      max_quality               max p; p within Q_TIE -> the cheaper card
      cheapest_above_threshold  min expected cost among p >= min_p (never a pick below min_p when one meets it);
                                none meets it -> the max_quality pick, decided_by '...:relaxed'
      max_utility               max utility
    Then (cheapest / max_utility) roughly equal calibrated P (p_mean within eq_margin) -> the cheaper card, among
    the threshold candidates for cheapest, and never more than eq_margin below the pick's lower bound."""
    if mode not in MODE_NAMES:
        raise ValueError(f"unknown mode {mode!r}")
    E = expected_cost(p, cost, strength, penalty_usd)
    util = (w_quality * p - w_cost * E / max(float(E.max()), 1e-12)
            - w_lat * latency / max(float(latency.max()), 1e-12))
    ok = list(np.flatnonzero(free_guard(p, cost)))
    pm = p if p_mean is None else p_mean
    if mode == "max_quality":
        return _best_p_cheaper(ok, p, cost, strength), "policy:max_quality", util, E
    if mode == "cheapest_above_threshold":
        pool = [i for i in ok if p[i] >= min_p]
        if not pool:
            return _best_p_cheaper(ok, p, cost, strength), "policy:cheapest_above_threshold:relaxed", util, E
        k, by = _min_e(pool, E, p, strength, cost), "policy:cheapest_above_threshold"
    else:
        pool = ok
        u_max = max(util[i] for i in pool)
        k, by = _stronger([i for i in pool if util[i] >= u_max - 1e-9], p, strength, cost), "policy:max_utility"
    eq = [i for i in pool if cost[i] < cost[k] * (1 - TIE_REL) - TIE_ABS and pm[i] >= pm[k] - eq_margin
          and p[i] >= p[k] - eq_margin]
    if eq:
        k, by = _min_e(eq, E, p, strength, cost), by + ":equal_p_cheaper"
    return k, by, util, E


MODE_NAMES = ("cheapest_above_threshold", "max_utility", "max_quality")


def ladder(p: np.ndarray, cost: np.ndarray, strength: np.ndarray, off: np.ndarray, lam: float,
           allowed: np.ndarray | None = None, length: int = 3) -> list[int]:
    """Cascade recommendation: the ordered pair (a, b) maximising
        S2 - lam * C2,  S2 = p_a + (1 - p_a) * p(b | a failed),  C2 = c_a + (1 - p_a) * c_b
    (p(b | a failed) = sigmoid(logit p_b + off[a, b]); lam in success per $), then the most likely remaining
    card given both failed. `allowed` masks cards that may open the ladder (the $0 guard); ties -> stronger."""
    n = len(p)
    if n == 1:
        return [0]
    lp = logit(p)
    pb = sigmoid(lp[None, :] + off)  # (a, b)
    S2 = p[:, None] + (1 - p[:, None]) * pb
    C2 = cost[:, None] + (1 - p[:, None]) * cost[None, :]
    obj = S2 - lam * C2
    np.fill_diagonal(obj, -np.inf)
    if allowed is not None:
        obj[~allowed, :] = -np.inf
    best = obj.max()
    cand = np.argwhere(obj >= best - 1e-9)
    a, b = max(map(tuple, cand), key=lambda ab: (strength[ab[1]], strength[ab[0]]))
    out = [int(a), int(b)]
    while len(out) < min(length, n):
        rest = [i for i in range(n) if i not in out]
        q = sigmoid(lp[rest] + off[out][:, rest].sum(axis=0))
        out.append(rest[max(range(len(rest)), key=lambda j: (round(float(q[j]), 3), strength[rest[j]]))])
    return out
