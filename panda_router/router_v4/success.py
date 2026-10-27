"""Learned P(pass | task, model): a frozen-feature logistic head over the profiler's TaskProfile.

Trained by scripts/outcomes/train_success_head.py on graded train/val attempts only (gold is never seen). One logistic
model per card id with a shared component (fit jointly: logit_m = b_m + (w + W_m) . x), bootstrapped over tasks;
`predict` returns the bootstrap-mean P and a lower confidence bound sigmoid(mean - z * sd) of the logits.

Underspecified requests (short text, high ambiguous_spec) widen the difficulty distribution toward the population
prior before features are built (`widen_difficulty`), so the same transform applies at train and serve time.
"""

from __future__ import annotations

import json
import re
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..profile import TaskProfile
from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES

LEVELS = np.arange(1, 11, dtype=float)
_WORD = re.compile(r"\w+")


def n_words(text: str) -> int:
    return len(_WORD.findall(text or ""))


def vagueness(profile: TaskProfile, text: str, short_words: float) -> float:
    """0..1: excess ambiguity x shortness. Ambiguity counts only above 0.5 (rescaled to 0..1); shortness is 1 at
    <= 2 words and 0 at >= short_words words."""
    short = float(np.clip((short_words - n_words(text)) / max(short_words - 2.0, 1.0), 0.0, 1.0))
    amb = float(np.clip((profile.flags.get("ambiguous_spec", 0.0) - 0.5) / 0.5, 0.0, 1.0))
    return amb * short


def widen_difficulty(diff, omega: float, prior) -> np.ndarray:
    """Mix toward the population prior; never moves mass below the profiler's own distribution's mean
    (an underspecified request can hide work, it cannot make a task easier)."""
    d = np.asarray(diff, float)
    d = d / d.sum()
    mixed = (1.0 - omega) * d + omega * np.asarray(prior, float)
    return mixed if mixed @ LEVELS >= d @ LEVELS else d


def quantile_level(diff, q: float) -> float:
    """Interpolated q-quantile of a distribution over levels 1..10."""
    c = np.cumsum(np.asarray(diff, float) / np.sum(diff))
    k = int(np.searchsorted(c, q))
    if k == 0:
        return 1.0
    lo = c[k - 1]
    return float(k + (q - lo) / max(c[k] - lo, 1e-9))


def feature_names() -> list[str]:
    return ([f"cat:{c}" for c in CATEGORIES] + [f"diff:{i}" for i in range(1, 11)] + ["diff:mean", "diff:q"]
            + [f"skill:{a}" for a in SKILL_AXES] + [f"flag:{f}" for f in FLAGS] + [f"check:{c}" for c in CHECKLIST_IDS]
            + ["out_tokens_p50", "log_words", "vague"])


def task_features(profile: TaskProfile, text: str, diff: np.ndarray, q: float, vague: float) -> np.ndarray:
    exp_sk = [profile.expected_skill(a) / 10.0 for a in SKILL_AXES]
    return np.array([profile.category.get(c, 0.0) for c in CATEGORIES] + list(diff)
                    + [float(diff @ LEVELS) / 10.0, quantile_level(diff, q) / 10.0] + exp_sk
                    + [profile.flags.get(f, 0.0) for f in FLAGS] + [profile.checklist.get(c, 0.0) for c in CHECKLIST_IDS]
                    + [profile.out_tokens_log10.get("p50", 3.0) / 4.0, np.log1p(n_words(text)) / 6.0, vague], float)


class SuccessHead:
    def __init__(self, params: dict, source: str = "inline"):
        self.params = params
        self.source = source
        self.cards: list[str] = list(params["cards"])
        self.index = {c: i for i, c in enumerate(self.cards)}
        self.mu, self.sd = np.asarray(params["mu"], float), np.asarray(params["sd"], float)
        self.coef = np.asarray(params["coef"], float)  # (B, M, d)
        self.bias = np.asarray(params["bias"], float)  # (B, M)
        self.prior = np.asarray(params["prior_difficulty"], float)
        self.q = float(params.get("difficulty_quantile", 0.75))
        self.lcb_z = float(params.get("lcb_z", 1.0))
        self.omega_max = float(params.get("omega_max", 0.7))
        self.short_words = float(params.get("short_words", 12))
        if self.coef.shape[1:] != (len(self.cards), len(self.mu)) or self.bias.shape != self.coef.shape[:2]:
            raise ValueError("success head: coef/bias shapes do not match cards/features")
        if len(self.mu) != len(feature_names()):
            raise ValueError("success head: feature count does not match this taxonomy")

    @classmethod
    def load(cls, path: str | Path) -> "SuccessHead":
        return _load(str(Path(path).resolve()))

    @property
    def name(self) -> str:
        return self.params.get("name", "success_head")

    def decision_difficulty(self, profile: TaskProfile, text: str, diff=None) -> tuple[np.ndarray, float]:
        """(widened difficulty distribution, vagueness) for a task; `diff` overrides the profile's
        distribution (an escalation posterior)."""
        v = vagueness(profile, text, self.short_words)
        base = profile.difficulty if diff is None else diff
        return widen_difficulty(base, self.omega_max * v, self.prior), v

    def features(self, profile: TaskProfile, text: str, diff=None) -> np.ndarray:
        d, v = self.decision_difficulty(profile, text, diff)
        return task_features(profile, text, d, self.q, v)

    def failure_offset(self, failed_cards: list[str], card_ids: list[str]) -> np.ndarray:
        """Log-odds shift of each card's P given that `failed_cards` already failed on this task (train/val
        conditional pass rates, P(B | A failed) vs P(B)). Pairs the head has no data for (an uncovered card on
        either side) get the table's mean shift: failures are correlated, so an unknown card is not treated as
        independent of the one that failed."""
        adj = self.params.get("escalation_logit") or {}
        vals = [v for row in adj.values() for v in row.values()]
        default = float(np.mean(vals)) if vals else 0.0
        return np.array([sum(adj[f][c] if f in adj and c in adj[f] else (0.0 if f == c else default)
                             for f in failed_cards) for c in card_ids])

    def predict_logits(self, x: np.ndarray, rows: list[int]) -> np.ndarray:
        """(B, len(rows)) bootstrap logits for feature vector x."""
        z = (x - self.mu) / self.sd
        return np.einsum("bmd,d->bm", self.coef[:, rows], z) + self.bias[:, rows]

    def predict(self, x: np.ndarray, card_ids: list[str], offset=0.0) -> tuple[np.ndarray, np.ndarray]:
        """(calibrated P, lower bound) for the given card ids (all must be in self.cards). The bootstrap-mean logit
        (+ `offset`, e.g. failure_offset) goes through the card's Platt calibration; the bound applies the same
        calibration to mean - lcb_z * sd (the head's bootstrap uncertainty)."""
        L = self.predict_logits(x, [self.index[c] for c in card_ids]) + offset
        m, s = L.mean(axis=0), L.std(axis=0)
        platt = self.params.get("platt") or {}
        ab = np.array([platt.get(c, (0.0, 1.0)) for c in card_ids], float)
        return _sigmoid(ab[:, 0] + ab[:, 1] * m), _sigmoid(ab[:, 0] + ab[:, 1] * (m - self.lcb_z * s))


def _sigmoid(x):
    return 1.0 / (1.0 + np.exp(-np.asarray(x, float)))


@lru_cache(maxsize=4)
def _load(path: str) -> SuccessHead:
    return SuccessHead(json.loads(Path(path).read_text()), source=path)
