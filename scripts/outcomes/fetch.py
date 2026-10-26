"""Download public per-instance outcome data into data/outcomes/raw (git-ignored).

- swe-bench/experiments (sparse clone: results.json / per_instance_details.json / metadata.yaml).
- SWE-bench full test / Verified / Lite / Multimodal / Multilingual task parquets (problem statements) from HF.
- ibragim-bad/swe_rebench_07_2026_trajectories: only (instance, participant, run, status) is kept;
  each 5 MB shard is streamed and deleted. Licence "other" -> outcome facts only, no text.

Usage: .venv/bin/python scripts/outcomes/fetch.py [swebench|tasks|rebench07 ...]
"""

import gzip
import json
import subprocess
import sys
from pathlib import Path

RAW = Path(__file__).resolve().parents[2] / "data" / "outcomes" / "raw"
HF_TASKS = {"verified": ("princeton-nlp/SWE-bench_Verified", "data/test-00000-of-00001.parquet"),
            "lite": ("princeton-nlp/SWE-bench_Lite", "data/test-00000-of-00001.parquet"),
            "multimodal": ("princeton-nlp/SWE-bench_Multimodal", "data/test-00000-of-00001.parquet"),
            "test": ("princeton-nlp/SWE-bench", "data/test-00000-of-00001.parquet"),
            "multilingual": ("SWE-bench/SWE-bench_Multilingual", "data/test-00000-of-00001.parquet")}
REBENCH07 = "ibragim-bad/swe_rebench_07_2026_trajectories"


def swebench():
    d = RAW / "swebench-experiments"
    if not d.exists():
        subprocess.run(["git", "clone", "--filter=blob:none", "--no-checkout", "--depth", "1",
                        "https://github.com/swe-bench/experiments.git", str(d)], check=True)
    subprocess.run(["git", "-C", str(d), "sparse-checkout", "set", "--no-cone",
                    "/evaluation/*/*/results/results.json", "/evaluation/*/*/per_instance_details.json",
                    "/evaluation/*/*/metadata.yaml", "/evaluation/*/*/metadata.yml"], check=True)
    subprocess.run(["git", "-C", str(d), "checkout"], check=True)


def tasks():
    from huggingface_hub import hf_hub_download

    for split, (repo, fn) in HF_TASKS.items():
        p = hf_hub_download(repo, fn, repo_type="dataset", local_dir=RAW / "hf" / split)
        print(split, p)


def rebench07():
    from huggingface_hub import hf_hub_download

    out = RAW / "rebench07_outcomes.jsonl"
    done = set()
    if out.exists():
        done = {(r["participant"], r["run"]) for r in map(json.loads, out.open())}
    idx = hf_hub_download(REBENCH07, "index.jsonl", repo_type="dataset", local_dir=RAW / "rebench07")
    with out.open("a") as fo:
        for shard in map(json.loads, open(idx)):
            key = (shard["participant_key"], shard["run"])
            if key in done:
                continue
            p = Path(hf_hub_download(REBENCH07, shard["path"], repo_type="dataset", local_dir=RAW / "rebench07"))
            rows = []
            with gzip.open(p, "rt") as f:
                for line in f:
                    r = json.loads(line)
                    pt = r["participant"]
                    rows.append({"instance_id": r["instance_id"], "language": r["language"], "participant": pt["key"],
                                 "type": pt["type"], "scaffold": pt["scaffold"], "model": pt["model"],
                                 "reasoning_effort": pt["reasoning_effort"], "run": r["run"]["index"],
                                 "status": (r["evaluation"] or {}).get("status"), "resolved": bool((r["evaluation"] or {}).get("resolved"))})
            # write a whole shard at once so a crash never leaves a half shard behind
            fo.write("".join(json.dumps(x) + "\n" for x in rows))
            fo.flush()
            p.unlink()
            print(key, len(rows), flush=True)


if __name__ == "__main__":
    steps = {"swebench": swebench, "tasks": tasks, "rebench07": rebench07}
    for s in sys.argv[1:] or list(steps):
        steps[s]()
