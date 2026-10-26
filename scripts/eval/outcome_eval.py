"""Outcome-difficulty Spearman: profiler expected difficulty vs outcome-IRT irt_b (data/outcomes/tasks.jsonl).

  .venv/bin/python scripts/eval/outcome_eval.py --profiler onnx:artifacts/panda-router-v2 --out eval_reports/v2/outcome_v2.json

Subsets: `heldout` = checkpoints/outcome/heldout.jsonl (repos never trained on, the headline number), its
n_systems >= 100 slice, and `all` (2,594 tasks; v2 trains on ~62% of them, so only comparable for v1).
`*_within_repo`: task-weighted mean per-repo Spearman (repos >= 30 tasks).
Two contexts: `issue` (issue_context(), like the training rows) and `report` ({requires_tools, has_images: false},
the data/outcomes/REPORT.md baseline setting).
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402
from scipy.stats import spearmanr  # noqa: E402

from panda_router.eval.baselines import load_profiler  # noqa: E402
from panda_router.train.data import load_jsonl  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
REPORT_CTX = {"requires_tools": True, "has_images": False}


def expected_difficulties(profiler, tasks: list[dict]) -> np.ndarray:
    if hasattr(profiler, "profile_batch"):
        return np.concatenate([[p.expected_difficulty() for p in profiler.profile_batch(tasks[j:j + 32])]
                               for j in range(0, len(tasks), 32)])
    return np.array([profiler.profile(t).expected_difficulty() for t in tasks])


def rho_ci(e: np.ndarray, b: np.ndarray, n_boot: int = 500) -> dict:
    rng = np.random.default_rng(0)
    boots = [spearmanr(e[ix], b[ix])[0] for ix in (rng.integers(0, len(b), len(b)) for _ in range(n_boot))]
    return {"n": len(b), "spearman": round(float(spearmanr(e, b)[0]), 4),
            "ci95": [round(float(np.percentile(boots, q)), 4) for q in (2.5, 97.5)],
            "mean_pred": round(float(e.mean()), 3), "sd_pred": round(float(e.std()), 3)}


def within_repo(e: np.ndarray, b: np.ndarray, repos: list[str], min_n: int = 30) -> dict:
    """Task-weighted mean of per-repo Spearman (repos with >= min_n tasks): ordering from the issue text alone."""
    per = {r: (int(m.sum()), float(spearmanr(e[m], b[m])[0]))
           for r in sorted(set(repos)) if (m := np.array([x == r for x in repos])).sum() >= min_n}
    n = sum(v[0] for v in per.values())
    return {"n": n, "spearman": round(sum(k * v for k, v in per.values()) / n, 4),
            "per_repo": {r: [k, round(v, 4)] for r, (k, v) in per.items()}}


def evaluate(spec: str) -> dict:
    prof = load_profiler(spec)
    held = load_jsonl(ROOT / "checkpoints" / "outcome" / "heldout.jsonl")
    allt = load_jsonl(ROOT / "data" / "outcomes" / "tasks.jsonl")
    res = {"profiler": spec}
    b = np.array([r["outcome"]["irt_b"] for r in held])
    big = np.array([r["outcome"]["n_systems"] >= 100 for r in held])
    for ctx in ("issue", "report"):
        tasks = [r["task"] if ctx == "issue" else {"text": r["task"]["text"], "context": REPORT_CTX} for r in held]
        e = expected_difficulties(prof, tasks)
        res[f"heldout_{ctx}"] = rho_ci(e, b)
        res[f"heldout_{ctx}_within_repo"] = within_repo(e, b, [r["meta"]["repo"] for r in held])
        res[f"heldout_{ctx}_nsys100"] = rho_ci(e[big], b[big])
    e = expected_difficulties(prof, [{"text": t["text"], "context": REPORT_CTX} for t in allt])
    res["all_report"] = rho_ci(e, np.array([t["irt_b"] for t in allt]))
    return res


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profiler", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = evaluate(a.profiler)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps(res, indent=2))
    print(json.dumps(res))


if __name__ == "__main__":
    main()
