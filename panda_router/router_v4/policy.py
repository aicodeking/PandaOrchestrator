"""v4 decision rules (pure numpy; shared by matcher.Matcher and the train/val tuning simulator).

Expected cost including failure:  E_m = c_m + (1 - P_m) * F_m,  F_m = c_next(m) + L
where c_next(m) is the cost of the escalation step after m fails (the most-likely-to-pass other candidate) and L is
a retry/latency penalty in $ (tuned on train/val). Decisions use the LOWER bound of the calibrated P (head:
Platt(mean - z sd); uncovered cards: conservative card prior), so the policy over-estimates difficulty modestly;
the calibrated P itself is what the response displays.

Modes (see choose): an anchor (best-evidence card) unless cheaper cards are clearly safe (lower bound >= min_p);
  cheapest_above_threshold  min E among the safe cheaper cards; E within the tie tolerance -> stronger model
  max_utility               max P - w_cost * E / max(E) - w_lat * lat / max(lat) over safe + anchor
  max_quality               max P over safe + anchor; ties -> stronger model
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


def anchored_card_p(p_card_q: np.ndarray, ref_card_q: np.ndarray, ref_p: np.ndarray, penalty: np.ndarray) -> np.ndarray:
    """Uncovered cards on the success head's scale for this task: monotone interpolation of the covered cards'
    (card P, head P) pairs in logit space, clamped to their range (an unproven card never exceeds the best
    evidence-backed one), minus the prior penalty."""
    order = np.argsort(ref_card_q)
    xs = logit(ref_card_q[order])
    ys = np.maximum.accumulate(logit(ref_p[order]))
    return sigmoid(np.interp(logit(p_card_q), xs, ys) - penalty)


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


P_TIE = 0.005  # P within this of the best counts as a tie (-> stronger card)


def _stronger(idx, p, strength, cost):
    top = max(p[i] for i in idx)
    return max((i for i in idx if p[i] >= top - P_TIE), key=lambda i: (strength[i], p[i], cost[i], -i))


def choose(mode: str, p: np.ndarray, cost: np.ndarray, latency: np.ndarray, strength: np.ndarray,
           min_p: float, penalty_usd: float, w_cost: float = 0.3, w_lat: float = 0.1,
           w_quality: float = 1.0, prior: np.ndarray | None = None,
           eq_margin: float = 0.0, p_mean: np.ndarray | None = None) -> tuple[int, str, np.ndarray, np.ndarray]:
    """-> (index, decided_by, utility, expected_cost) over the given candidate arrays. p = decision (lower) bound.

    Anchor = best-evidence card: max `prior` (the success head's population base rate; -inf for cards it was not
    trained on) or, with no prior, max p. Cards cheaper than the anchor compete only when p >= min_p ("clearly
    safe") or its calibrated P (p_mean, default p) is within eq_margin of the anchor's (roughly equal P -> the
    cheaper card): cheapest_above_threshold takes the min expected cost among them, max_utility the max utility over
    them + the anchor, max_quality the max p over them + the anchor. Otherwise the anchor is picked."""
    E = expected_cost(p, cost, strength, penalty_usd)
    util = (w_quality * p - w_cost * E / max(float(E.max()), 1e-12)
            - w_lat * latency / max(float(latency.max()), 1e-12))
    ok = list(np.flatnonzero(free_guard(p, cost)))
    if prior is not None and np.isfinite(prior[ok]).any():
        anchor = _stronger(ok, np.where(np.isfinite(prior), prior, -1.0), strength, cost)
    else:
        anchor = _stronger(ok, p, strength, cost)
    pm = p if p_mean is None else p_mean
    safe = [i for i in ok if cost[i] < cost[anchor] and (p[i] >= min_p or pm[i] >= pm[anchor] - eq_margin)]
    if mode not in MODE_NAMES:
        raise ValueError(f"unknown mode {mode!r}")
    if not safe:
        k, by = anchor, f"policy:{mode}:anchor"
    elif mode == "cheapest_above_threshold":
        pool = safe + [anchor]
        e_min = min(E[i] for i in pool)
        k, by = _stronger([i for i in pool if E[i] <= e_min * (1 + TIE_REL) + TIE_ABS], p, strength, cost), \
            "policy:cheapest_above_threshold"
    elif mode == "max_utility":
        pool = safe + [anchor]
        u_max = max(util[i] for i in pool)
        k, by = _stronger([i for i in pool if util[i] >= u_max - 1e-9], p, strength, cost), "policy:max_utility"
    else:
        k, by = _stronger(safe + [anchor], p, strength, cost), "policy:max_quality"
    # roughly equal calibrated P -> never the pricier card (all modes)
    eq = [i for i in ok if cost[i] < cost[k] * (1 - TIE_REL) - TIE_ABS and pm[i] >= pm[k] - eq_margin]
    if eq:
        e_min = min(E[i] for i in eq)
        k = _stronger([i for i in eq if E[i] <= e_min * (1 + TIE_REL) + TIE_ABS], p, strength, cost)
        by += ":equal_p_cheaper"
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
