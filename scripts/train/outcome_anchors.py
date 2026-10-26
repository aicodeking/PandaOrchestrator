"""Difficulty-only training rows from outcome-IRT anchors (data/outcomes/tasks.jsonl, SWE-bench).

  .venv/bin/python scripts/train/outcome_anchors.py [--center-repo --out checkpoints/outcome_rc]

Writes checkpoints/outcome/{train,val,heldout}.jsonl. Rows look like a profiler example without `labels`:
{id, source: "outcome-anchor", task: {text, context}, outcome: {difficulty, w, irt_b, ...}}.
- heldout: every task of HELDOUT_REPOS plus half of the multilingual repos (by hash). Never trained on;
  this is where outcome Spearman is reported.
- val: 10% of the remaining tasks (by id hash), for tuning the anchor weight.
- difficulty: quantile map of irt_b onto the teacher expected-difficulty marginal of the labelled SWE train
  rows, so the anchor changes the ordering of SWE tasks but not the label scale used by gold/routing.
- --center-repo: irt_b minus its (shrunk) repo mean before the map, so the anchor teaches the within-repo ordering
  from the issue text instead of per-repo levels (which do not transfer to unseen repos). heldout keeps raw irt_b.
- w = clip((0.5 / se_router)^2, 0.05, 1): outcome trust (REPORT.md: weight by 1/se^2).
- context: issue_context() from the issue text only, like the labelled SWE rows.
"""

import argparse
import hashlib
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from panda_router.datagen.real import issue_body, issue_context  # noqa: E402
from panda_router.train.data import load_jsonl  # noqa: E402

ROOT = Path(__file__).resolve().parents[2]
HELDOUT_REPOS = {"sympy/sympy", "sphinx-doc/sphinx", "pytest-dev/pytest", "astropy/astropy", "psf/requests"}
SE_REF, W_MIN = 0.5, 0.05
SHRINK_N = 5  # repo mean is shrunk to the global mean with weight n / (n + SHRINK_N)


def _h(s: str) -> int:
    return int(hashlib.sha1(s.encode()).hexdigest()[:8], 16)


def split_of(t: dict) -> str:
    if t["repo"] in HELDOUT_REPOS or ("multilingual" in t["source"] and _h(t["repo"]) % 2):
        return "heldout"
    return "val" if _h(t["id"]) % 10 == 0 else "train"


def repo_centered(tasks: list[dict]) -> dict:
    """{task id: irt_b - shrunk repo mean + global mean}."""
    g = float(np.mean([t["irt_b"] for t in tasks]))
    by = {}
    for t in tasks:
        by.setdefault(t["repo"], []).append(t["irt_b"])
    mean = {r: (len(v) * np.mean(v) + SHRINK_N * g) / (len(v) + SHRINK_N) for r, v in by.items()}
    return {t["id"]: t["irt_b"] - mean[t["repo"]] + g for t in tasks}


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--center-repo", action="store_true")
    ap.add_argument("--out", default=str(ROOT / "checkpoints" / "outcome"))
    a = ap.parse_args()
    tasks = load_jsonl(ROOT / "data" / "outcomes" / "tasks.jsonl")
    gold = {(r.get("meta") or {}).get("raw_id") for r in load_jsonl(ROOT / "data" / "gold" / "gold.jsonl")}
    assert not gold & {t["raw_id"] for t in tasks}, "outcome task in gold"
    lab = [r for r in load_jsonl(ROOT / "data" / "train.jsonl") if r["source"] in ("swe-rebench", "swe-smith")]
    ref = np.sort([float(np.dot(r["labels"]["difficulty"], np.arange(1, 11))) for r in lab])
    parts = {t["id"]: split_of(t) for t in tasks}
    fit = [t for t in tasks if parts[t["id"]] != "heldout"]
    tb = repo_centered(fit) if a.center_repo else {t["id"]: t["irt_b"] for t in fit}
    b_ref = np.sort([tb[t["id"]] for t in fit if parts[t["id"]] == "train"])

    def qmap(b: float) -> float:
        return float(np.quantile(ref, np.searchsorted(b_ref, b, side="right") / len(b_ref)))

    out = {"train": [], "val": [], "heldout": []}
    for t in tasks:
        body = issue_body(t["text"])
        out[parts[t["id"]]].append({
            "id": f"oa-{t['id']}", "source": "outcome-anchor",
            "task": {"text": t["text"], "context": issue_context(body, t["repo"])},
            "outcome": {"difficulty": qmap(tb.get(t["id"], t["irt_b"])), "w": float(np.clip((SE_REF / t["se_router"]) ** 2, W_MIN, 1.0)),
                        "irt_b": t["irt_b"], "irt_b_router_scale": t["irt_b_router_scale"],
                        "se_router": t["se_router"], "n_systems": t["n_systems"]},
            "meta": {"raw_id": t["raw_id"], "repo": t["repo"], "outcome_source": t["source"]},
        })
    d = Path(a.out)
    d.mkdir(parents=True, exist_ok=True)
    for k, rows in out.items():
        with open(d / f"{k}.jsonl", "w") as f:
            f.writelines(json.dumps(r) + "\n" for r in rows)
    print(json.dumps({k: {"n": len(v), "repos": len({r["meta"]["repo"] for r in v}),
                          "mean_target": round(float(np.mean([r["outcome"]["difficulty"] for r in v])), 2),
                          "mean_w": round(float(np.mean([r["outcome"]["w"] for r in v])), 3)} for k, v in out.items()}))


if __name__ == "__main__":
    main()
