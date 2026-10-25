"""Numpy-only decoding of raw head outputs into probabilities and TaskProfiles.

Shared by training metrics, TorchProfiler and OnnxProfiler so serving and evaluation agree.
Raw outputs (all float32):
  category (B,13) logits | difficulty (B,9) CORN logits | skills (B,10,10) CORN logits
  flags (B,7) logits | checklist (B,24) logits | out_tokens (B,3) monotone p10/p50/p90 of log10
Temperatures (heads.json "temperatures"): category, difficulty, flags, checklist (floats),
skills (list of 10 floats, one per axis), out_tokens_width (scale of the p10/p90 spread).
"""

import numpy as np

from ..profile import TaskProfile
from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES

DEFAULT_TEMPS = {
    "category": 1.0, "difficulty": 1.0, "skills": [1.0] * len(SKILL_AXES),
    "flags": 1.0, "checklist": 1.0, "out_tokens_width": 1.0,
}


def sigmoid(x):
    return 1.0 / (1.0 + np.exp(-x))


def softmax(x, axis=-1):
    z = x - x.max(axis=axis, keepdims=True)
    e = np.exp(z)
    return e / e.sum(axis=axis, keepdims=True)


def corn_probs_np(logits):
    surv = np.cumprod(sigmoid(logits), axis=-1)
    one = np.ones_like(surv[..., :1])
    probs = np.concatenate([one, surv], -1) - np.concatenate([surv, np.zeros_like(one)], -1)
    probs = np.clip(probs, 0.0, None)
    return probs / probs.sum(-1, keepdims=True)


def decode_probs(raw: dict, temps: dict | None = None) -> dict:
    t = {**DEFAULT_TEMPS, **(temps or {})}
    skill_t = np.asarray(t["skills"], dtype=np.float64).reshape(1, -1, 1)
    q = np.asarray(raw["out_tokens"], dtype=np.float64)
    p50 = q[:, 1]
    w = float(t["out_tokens_width"])
    return {
        "category": softmax(np.asarray(raw["category"], np.float64) / t["category"]),
        "difficulty": corn_probs_np(np.asarray(raw["difficulty"], np.float64) / t["difficulty"]),
        "skills": corn_probs_np(np.asarray(raw["skills"], np.float64) / skill_t),
        "flags": sigmoid(np.asarray(raw["flags"], np.float64) / t["flags"]),
        "checklist": sigmoid(np.asarray(raw["checklist"], np.float64) / t["checklist"]),
        "out_tokens": np.stack([p50 - w * (p50 - q[:, 0]), p50, p50 + w * (q[:, 2] - p50)], -1),
    }


def to_profiles(probs: dict) -> list[TaskProfile]:
    out = []
    for i in range(probs["category"].shape[0]):
        out.append(TaskProfile(
            category={c: float(p) for c, p in zip(CATEGORIES, probs["category"][i])},
            difficulty=[float(p) for p in probs["difficulty"][i]],
            skills={a: [float(p) for p in probs["skills"][i, k]] for k, a in enumerate(SKILL_AXES)},
            flags={f: float(p) for f, p in zip(FLAGS, probs["flags"][i])},
            checklist={c: float(p) for c, p in zip(CHECKLIST_IDS, probs["checklist"][i])},
            out_tokens_log10={k: float(v) for k, v in zip(("p10", "p50", "p90"), probs["out_tokens"][i])},
        ))
    return out
