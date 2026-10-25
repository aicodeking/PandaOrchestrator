"""CPU latency benchmark (batch 1, tokenize+run+decode) of exported artifacts; merges into metrics.json.
.venv/bin/python scripts/train/bench.py --artifacts artifacts/profiler-32m --data-dir data --n 300
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.model.onnx_profiler import OnnxProfiler, bench_latency  # noqa: E402
from panda_router.text import format_input  # noqa: E402
from panda_router.train.data import load_jsonl  # noqa: E402


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--artifacts", required=True)
    ap.add_argument("--data-dir", default="data")
    ap.add_argument("--split", default="val")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--threads", type=int, default=None)
    ap.add_argument("--long-words", type=int, default=300, help="also bench a synthetic task of ~N words (0=off)")
    a = ap.parse_args()
    tasks = [ex["task"] for ex in load_jsonl(Path(a.data_dir) / f"{a.split}.jsonl")]
    long_task = {"text": " ".join(f"refactor module{i % 50} handler" for i in range(a.long_words // 3)),
                 "context": {"repo_languages": ["python"], "files_in_scope": 5, "requires_tools": True}}
    res = {"threads": a.threads}
    for quantized in (True, False):
        prof = OnnxProfiler(a.artifacts, quantized=quantized, threads=a.threads)
        key = "int8" if quantized else "fp32"
        res[key] = bench_latency(prof, tasks, a.n)
        if a.long_words:
            n_tok = len(prof.tokenizer(format_input(long_task), truncation=True, max_length=prof.max_len)["input_ids"])
            res[f"{key}_long"] = {**bench_latency(prof, [long_task], a.n), "tokens": n_tok}
    path = Path(a.artifacts) / "metrics.json"
    metrics = json.loads(path.read_text()) if path.exists() else {}
    metrics["cpu_latency_batch1"] = res
    path.write_text(json.dumps(metrics, indent=2))
    print(json.dumps(res, indent=2))


if __name__ == "__main__":
    main()
