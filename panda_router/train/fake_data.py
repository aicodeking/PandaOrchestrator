"""Small fake dataset in the exact CONTRACTS.md format, for pipeline tests only (never for a real model).

Usage: python -m panda_router.train.fake_data --out checkpoints/fake --n 240
"""

import argparse
import json
import random
from pathlib import Path

import numpy as np

from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, N_DIFFICULTY, N_SKILL_LEVELS, SKILL_AXES

SOURCES = ["synthetic", "swe-rebench", "wildchat", "swe-smith"]
CAT_AXIS = {
    "implementation": "coding", "bugfix": "debugging", "refactor": "coding", "test_writing": "coding",
    "code_review": "review", "research": "research", "planning": "planning", "docs_writing": "writing",
    "ui_frontend": "ui_frontend", "data_analysis": "data_analysis", "devops_infra": "coding",
    "math_reasoning": "math", "chat_simple": "writing",
}
VERBS = {
    "implementation": "Implement", "bugfix": "Fix the bug where", "refactor": "Refactor",
    "test_writing": "Write tests for", "code_review": "Review the PR for", "research": "Research",
    "planning": "Plan the rollout of", "docs_writing": "Write docs for", "ui_frontend": "Build the UI for",
    "data_analysis": "Analyse the dataset of", "devops_infra": "Set up CI deploy for",
    "math_reasoning": "Prove the bound on", "chat_simple": "Quickly explain",
}
NOUNS = ["the auth middleware", "the billing service", "a CSV importer", "the cache layer", "the search API",
         "the settings page", "the job scheduler", "the metrics pipeline", "the payment webhook", "a CLI tool"]
LANGS = ["python", "typescript", "go", "rust", "java"]


def smooth_ordinal(level: float, n: int, offset: int, sigma: float = 0.6) -> list[float]:
    x = np.arange(n) + offset
    p = np.exp(-0.5 * ((x - level) / sigma) ** 2)
    return [round(float(v), 5) for v in p / p.sum()]


def make_example(rng: random.Random, idx: int) -> dict:
    cat = rng.choice(CATEGORIES)
    other = rng.choice(CATEGORIES)
    diff = rng.uniform(1, 10)
    long_ctx = rng.random() < 0.2
    text = f"{VERBS[cat]} {rng.choice(NOUNS)}."
    if diff > 6:
        text += " It must handle concurrency, retries and a migration with zero downtime."
    if long_ctx:
        text += " The attached 200k-token log is included below."
    ctx = {"repo_languages": [rng.choice(LANGS)], "files_in_scope": rng.randint(1, 20),
           "estimated_input_tokens": rng.choice([800, 4000, 20000, 200000 if long_ctx else 9000]),
           "has_images": cat == "ui_frontend" and rng.random() < 0.5, "requires_tools": cat != "chat_simple"}
    return {"id": f"fake-{idx:06d}", "source": rng.choice(SOURCES), "pair_of": None,
            "task": {"text": text, "context": ctx}, "labels": make_labels(rng, cat, other, diff, long_ctx, ctx),
            "meta": {"teachers": ["fake"], "agreement": 1.0, "persona": "fixture"}}


def make_labels(rng, cat, other, diff, long_ctx, ctx) -> dict:
    category = {cat: 0.8, other: 0.2} if other != cat else {cat: 1.0}
    skills = {}
    for a in SKILL_AXES:
        lvl = diff if a == CAT_AXIS[cat] else (diff * 0.5 if a == "reasoning" else rng.uniform(0, 2))
        skills[a] = smooth_ordinal(min(lvl, 10), N_SKILL_LEVELS, 0)
    flags = {f: round(rng.uniform(0, 0.2), 3) for f in FLAGS}
    flags["long_context"] = 0.95 if long_ctx else 0.05
    flags["needs_tools"] = 0.9 if ctx["requires_tools"] else 0.1
    flags["needs_vision"] = 0.9 if ctx["has_images"] else 0.05
    checklist = {c: round(rng.uniform(0, 1), 3) for c in CHECKLIST_IDS}
    checklist["input_gt_50k_tokens"] = 1.0 if long_ctx else 0.0
    checklist["edits_code"] = 1.0 if CAT_AXIS[cat] in ("coding", "debugging") else 0.1
    return {"category": category, "difficulty": smooth_ordinal(diff, N_DIFFICULTY, 1), "skills": skills,
            "flags": flags, "checklist": checklist, "out_tokens_log10": round(2.0 + diff * 0.2 + rng.gauss(0, 0.1), 3)}


def make_pair(rng: random.Random, orig: dict, idx: int) -> dict:
    ex = json.loads(json.dumps(orig))
    ex["id"], ex["source"], ex["pair_of"] = f"fake-{idx:06d}", "minimal-pair", orig["id"]
    ex["task"]["text"] += " Also attach and analyse the full 200k-token production log."
    ex["task"]["context"]["estimated_input_tokens"] = 200000
    d = float(np.dot(np.arange(1, 11), orig["labels"]["difficulty"]))
    ex["labels"]["difficulty"] = smooth_ordinal(min(d + 1.5, 10), N_DIFFICULTY, 1)
    ex["labels"]["flags"]["long_context"] = 0.95
    ex["labels"]["checklist"]["input_gt_50k_tokens"] = 1.0
    ex["meta"].update({"edit": "attach 200k-token log", "expected_delta": {"difficulty": "+", "flags.long_context": 1}})
    return ex


def validate_example(ex: dict) -> None:
    """Assert an example follows CONTRACTS.md."""
    for k in ("id", "source", "pair_of", "task", "labels", "meta"):
        assert k in ex, k
    lab = ex["labels"]
    assert set(lab["category"]) <= set(CATEGORIES) and abs(sum(lab["category"].values()) - 1) < 1e-3
    assert len(lab["difficulty"]) == N_DIFFICULTY and abs(sum(lab["difficulty"]) - 1) < 1e-3
    assert set(lab["skills"]) == set(SKILL_AXES)
    assert all(len(v) == N_SKILL_LEVELS and abs(sum(v) - 1) < 1e-3 for v in lab["skills"].values())
    assert set(lab["flags"]) == set(FLAGS) and all(0 <= v <= 1 for v in lab["flags"].values())
    assert set(lab["checklist"]) == set(CHECKLIST_IDS) and all(0 <= v <= 1 for v in lab["checklist"].values())
    assert isinstance(lab["out_tokens_log10"], (int, float))
    if ex["source"] == "minimal-pair":
        assert ex["pair_of"] and "expected_delta" in ex["meta"]


def generate(out_dir, n: int = 240, seed: int = 0, pair_frac: float = 0.2) -> Path:
    rng = random.Random(seed)
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    idx = 0
    splits = {"train": n, "val": max(n // 4, 16), "test": max(n // 4, 16)}
    for split, size in splits.items():
        rows = []
        while len(rows) < size:
            ex = make_example(rng, idx)
            idx += 1
            rows.append(ex)
            if rng.random() < pair_frac and len(rows) < size:
                rows.append(make_pair(rng, ex, idx))
                idx += 1
        rng.shuffle(rows)
        for ex in rows:
            validate_example(ex)
        (out / f"{split}.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    return out


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="checkpoints/fake")
    ap.add_argument("--n", type=int, default=240)
    ap.add_argument("--seed", type=int, default=0)
    a = ap.parse_args()
    print(generate(a.out, a.n, a.seed))


if __name__ == "__main__":
    main()
