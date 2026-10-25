"""Outcome anchors for NON-gold SWE-rebench training/val records (stretch, PLAN.md 12.4 #1).

  .venv/bin/python scripts/train/anchors_train.py

Fits the same 1PL IRT model as scripts/eval/fit_anchors.py on all published Nebius outcomes, then
for every swe-rebench original in data/{train,val}.jsonl with outcomes writes
checkpoints/anchors_{train,val}.jsonl: {id, raw_id, irt_b, irt_b_se, n_models, difficulty_1_10}.
`difficulty_1_10` is a quantile map of irt_b onto the teacher expected-difficulty marginal of the
same anchored train records, so the aux loss only changes the ordering, not the label scale.
Gold-partition ids are asserted absent.
"""

import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import numpy as np  # noqa: E402

from panda_router.datagen.common import is_gold_reserved  # noqa: E402
from panda_router.eval.anchors import fit_anchors  # noqa: E402
from panda_router.eval.metrics import DIFF_LEVELS, expected, spearman  # noqa: E402
from panda_router.train.data import load_jsonl  # noqa: E402


def main() -> None:
    anchors, _ = fit_anchors()
    out_dir = Path("checkpoints")
    picked = {}
    for split in ("train", "val"):
        rows = [r for r in load_jsonl(Path("data") / f"{split}.jsonl")
                if r["source"] == "swe-rebench" and (r.get("meta") or {}).get("raw_id") in anchors]
        assert not any(is_gold_reserved(r["meta"]["raw_id"]) for r in rows), "gold id in training data"
        picked[split] = rows
    tr = picked["train"]
    ref = np.sort([expected(r["labels"]["difficulty"], DIFF_LEVELS) for r in tr])
    b_ref = np.sort([anchors[r["meta"]["raw_id"]]["irt_b"] for r in tr])

    def qmap(b: float) -> float:
        q = np.searchsorted(b_ref, b, side="right") / len(b_ref)
        return float(np.quantile(ref, min(max(q, 0.0), 1.0)))

    report = {}
    for split, rows in picked.items():
        recs = []
        for r in rows:
            a = anchors[r["meta"]["raw_id"]]
            recs.append({"id": r["id"], "raw_id": r["meta"]["raw_id"], "irt_b": a["irt_b"], "irt_b_se": a["irt_b_se"],
                         "n_models": a["n_models"], "difficulty_1_10": qmap(a["irt_b"])})
        with open(out_dir / f"anchors_{split}.jsonl", "w") as f:
            f.writelines(json.dumps(x) + "\n" for x in recs)
        teach = [expected(r["labels"]["difficulty"], DIFF_LEVELS) for r in rows]
        report[split] = {"n": len(recs), "spearman_teacher_vs_irt": spearman(teach, [x["irt_b"] for x in recs])}
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
