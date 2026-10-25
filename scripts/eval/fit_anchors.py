"""Fit 1PL IRT outcome anchors and compare with teacher difficulty.

  .venv/bin/python scripts/eval/fit_anchors.py

Writes data/gold/anchors.jsonl ({id, raw_id, irt_b, irt_b_se, difficulty_1_10, n_models, outcomes}) for
gold SWE-rebench tasks that have published outcomes, plus data/gold/anchor_report.json with the
model abilities and the Spearman correlations between teacher difficulty and IRT difficulty.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from panda_router.eval.anchors import fit_anchors  # noqa: E402
from panda_router.eval.gold import CANDIDATES, GOLD, GOLD_PATH, read_jsonl, write_jsonl  # noqa: E402
from panda_router.eval.metrics import DIFF_LEVELS, expected, spearman  # noqa: E402


def main() -> None:
    anchors, fit = fit_anchors()
    rows = read_jsonl(GOLD_PATH) or read_jsonl(CANDIDATES)
    out = []
    for r in rows:
        a = anchors.get(r["meta"]["raw_id"])
        if a:
            out.append({"id": r["id"], "raw_id": r["meta"]["raw_id"], **a})
    write_jsonl(GOLD / "anchors.jsonl", out)

    report = {"fit": fit, "n_gold_anchored": len(out)}
    by_id = {r["id"]: r for r in rows if "labels" in r}
    paired = [(by_id[a["id"]], a) for a in out if a["id"] in by_id]
    if len(paired) >= 3:
        irt = [a["irt_b"] for _, a in paired]
        merged = [expected(g["labels"]["difficulty"], DIFF_LEVELS) for g, _ in paired]
        report["spearman_teacher_merged_vs_irt"] = spearman(merged, irt)
        per_t = {}
        for t in ("codex", "grok", "kimi", "ollama"):
            xs = [(g["meta"]["teacher_answers"][t]["diff"], a["irt_b"]) for g, a in paired
                  if t in g["meta"].get("teacher_answers", {})]
            if len(xs) >= 3:
                per_t[t] = {"n": len(xs), "spearman": spearman(*zip(*xs))}
        report["spearman_per_teacher_vs_irt"] = per_t
        ll = [(g["meta"].get("rebench_llm_difficulty_score"), a["irt_b"]) for g, a in paired]
        ll = [x for x in ll if x[0] is not None and x[0] >= 0]
        if len(ll) >= 3:
            report["spearman_rebench_llm_score_vs_irt"] = {"n": len(ll), "spearman": spearman(*zip(*ll))}
        # Bootstrap CI for the key reality check.
        rng = np.random.default_rng(0)
        m, b = np.array(merged), np.array(irt)
        boots = [spearman(m[i], b[i]) for i in (rng.integers(0, len(m), len(m)) for _ in range(2000))]
        boots = [x for x in boots if x is not None]
        report["spearman_teacher_merged_vs_irt_ci95"] = [float(np.percentile(boots, 2.5)), float(np.percentile(boots, 97.5))]
        report["n_paired"] = len(paired)
    (GOLD / "anchor_report.json").write_text(json.dumps(report, indent=2))
    print(json.dumps({k: v for k, v in report.items() if k != "fit"} | {"models": fit["models"]}, indent=2))


if __name__ == "__main__":
    main()
