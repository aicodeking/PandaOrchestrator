"""Soft-label merge per schemas/CONTRACTS.md.

Teachers give point answers. For ordinal fields (difficulty 1..10, skills 0..10) each point is
turned into a discretised Gaussian (sigma=0.6 levels); the teachers' smoothed distributions are
averaged. This equals averaging the teachers' one-hot point answers and then convolving with the
sigma=0.6 kernel, so disagreement survives as a bimodal soft label. Category: each teacher puts
1.0 on its primary (0.75/0.25 when it names a secondary); teachers are averaged. Flags and
checklist: mean of the teachers' 0/1 answers. out_tokens_log10: mean of log10(out_tokens).
"""

import math

from .common import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES

SIGMA = 0.6
SECONDARY_WEIGHT = 0.25


def gaussian_dist(center: float, lo: int, hi: int, sigma: float = SIGMA) -> list[float]:
    w = [math.exp(-0.5 * ((k - center) / sigma) ** 2) for k in range(lo, hi + 1)]
    s = sum(w)
    return [x / s for x in w]


def smooth_points(points: list[float], lo: int, hi: int, sigma: float = SIGMA,
                  weights: list[float] | None = None) -> list[float]:
    weights = weights or [1.0] * len(points)
    tot = sum(weights)
    out = [0.0] * (hi - lo + 1)
    for p, w in zip(points, weights):
        for i, v in enumerate(gaussian_dist(p, lo, hi, sigma)):
            out[i] += v * w / tot
    return out


def category_dist(answers: list[dict]) -> dict[str, float]:
    acc = {c: 0.0 for c in CATEGORIES}
    for a in answers:
        if a.get("cat2"):
            acc[a["cat"]] += 1 - SECONDARY_WEIGHT
            acc[a["cat2"]] += SECONDARY_WEIGHT
        else:
            acc[a["cat"]] += 1.0
    n = len(answers)
    return {c: round(v / n, 6) for c, v in acc.items() if v > 0}


def agreement(answers: list[dict]) -> float:
    """Mean pairwise agreement in [0,1]: average of primary-category match, 1-|Δdiff|/9,
    1-mean|Δskill|/10 and the fraction of matching flag+checklist bits."""
    if len(answers) < 2:
        return 1.0
    scores = []
    for i in range(len(answers)):
        for j in range(i + 1, len(answers)):
            a, b = answers[i], answers[j]
            cat = float(a["cat"] == b["cat"])
            diff = 1 - abs(a["diff"] - b["diff"]) / 9
            sk = 1 - sum(abs(a["skills"][k] - b["skills"][k]) for k in SKILL_AXES) / (10 * len(SKILL_AXES))
            bits = [a["flags"][f] == b["flags"][f] for f in FLAGS] + [a["check"][c] == b["check"][c] for c in CHECKLIST_IDS]
            scores.append((cat + diff + sk + sum(bits) / len(bits)) / 4)
    return round(sum(scores) / len(scores), 4)


def merge(answers: list[dict], difficulty_override: list[float] | None = None,
          tiebreak: list[dict] | None = None) -> dict:
    """Merge cleaned teacher answers (see label.clean_answer) into CONTRACTS.md soft labels.

    `tiebreak` holds partial answers ({cat, cat2, diff}) from a third teacher; they join the
    average for category and difficulty only.
    """
    if not answers:
        raise ValueError("no teacher answers")
    n = len(answers)
    cd = answers + list(tiebreak or [])
    labels = {
        "category": category_dist(cd),
        "difficulty": [round(x, 6) for x in smooth_points([a["diff"] for a in cd], 1, 10)],
        "skills": {ax: [round(x, 6) for x in smooth_points([a["skills"][ax] for a in answers], 0, 10)] for ax in SKILL_AXES},
        "flags": {f: round(sum(a["flags"][f] for a in answers) / n, 4) for f in FLAGS},
        "checklist": {c: round(sum(a["check"][c] for a in answers) / n, 4) for c in CHECKLIST_IDS},
        "out_tokens_log10": round(sum(math.log10(max(10, a["out_tokens"])) for a in answers) / n, 4),
    }
    if difficulty_override is not None:
        labels["difficulty"] = [round(x, 6) for x in difficulty_override]
    return labels
