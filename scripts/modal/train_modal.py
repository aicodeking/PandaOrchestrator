"""GPU training on Modal. Volume 'panda-router' holds /data (train/val/test jsonl + outcome anchors) and /runs.

  modal run scripts/modal/train_modal.py --stage pilot|teachers|cache|distill|soup|student68
Every job logs GPU, wall time and $ to checkpoints/v4/cost_log.jsonl; launches stop before the $15 cap.
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) > 2 else Path("/root/repo")
COST_LOG = ROOT / "checkpoints/v4/cost_log.jsonl"
CAP_USD = 15.0
# Modal $/s (list price) plus ~8% for the CPU/memory the container reserves.
PRICE = {"L40S": 0.000542, "A100-40GB": 0.000583}
OVERHEAD = 1.08

app = modal.App("panda-router-v4")
vol = modal.Volume.from_name("panda-router", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch", "transformers==4.57.6", "numpy", "scipy", "scikit-learn", "jsonschema",
                 "onnxruntime", "onnx", "datasets", "accelerate")
    .env({"HF_HOME": "/vol/hf", "TOKENIZERS_PARALLELISM": "false"})
    .add_local_dir(ROOT / "panda_router", "/root/repo/panda_router", ignore=["**/__pycache__", "*.pyc"])
    .add_local_dir(ROOT / "schemas", "/root/repo/schemas")
    .add_local_dir(ROOT / "scripts/train", "/root/repo/scripts/train", ignore=["**/__pycache__", "*.sh"])
)
D = "/vol/data"
ANCH = (f"--anchors {D}/attempt_outcome_v3/train.jsonl --outcome-anchors {D}/outcome_v3/train.jsonl "
        f"--outcome-val {D}/outcome_v3/val.jsonl")
REC = "--anchor-weight 0.3 --regret-weight 0 --max-len 512 --under-w 2.5"


def _job(script: str, args: list, run: str, gpu: str) -> dict:
    vol.reload()
    t0 = time.time()
    r = subprocess.run([sys.executable, f"scripts/train/{script}", *args], cwd="/root/repo")
    wall = time.time() - t0
    vol.commit()
    if r.returncode:
        raise RuntimeError(f"{script} {run} failed rc={r.returncode}")
    return {"run": run, "gpu": gpu, "wall_s": wall}


_OPTS = dict(image=image, volumes={"/vol": vol}, timeout=3 * 3600, retries=1)


@app.function(gpu="L40S", **_OPTS)
def job_l40s(script, args, run):
    return _job(script, args, run, "L40S")


@app.function(gpu="A100-40GB", **_OPTS)
def job_a100(script, args, run):
    return _job(script, args, run, "A100-40GB")


JOBS = {"L40S": job_l40s, "A100-40GB": job_a100}


def spent() -> float:
    if not COST_LOG.exists():
        return 0.0
    return sum(json.loads(ln)["usd"] for ln in COST_LOG.read_text().splitlines() if ln.strip())


def log_cost(res: dict) -> float:
    usd = res["wall_s"] * PRICE[res["gpu"]] * OVERHEAD
    total = spent() + usd
    COST_LOG.parent.mkdir(parents=True, exist_ok=True)
    with COST_LOG.open("a") as f:
        f.write(json.dumps({**res, "usd": round(usd, 4), "total_usd": round(total, 4)}) + "\n")
    print(f"[cost] {res['run']} {res['gpu']} {res['wall_s']:.0f}s ${usd:.2f} total ${total:.2f}", flush=True)
    return total


def launch(specs):
    """specs: [(gpu, script, argstring, run, est_usd)] run in parallel; refuses past the cap."""
    est = sum(s[4] for s in specs)
    if spent() + est > CAP_USD:
        raise SystemExit(f"cap: spent ${spent():.2f} + est ${est:.2f} > ${CAP_USD}")
    calls = [(s, JOBS[s[0]].spawn(s[1], s[2].split(), s[3])) for s in specs]
    out = []
    for s, c in calls:
        try:
            res = c.get()
        except Exception as e:
            print(f"[fail] {s[3]}: {e}", flush=True)
            log_cost({"run": s[3] + "_FAILED", "gpu": s[0], "wall_s": 60})  # failed jobs still bill (estimate)
            continue
        log_cost(res)
        out.append(res)
    return out


def pull(run: str, subs=("best", "train_summary.json", "train_config.json")):
    dst = ROOT / "checkpoints/v4" / run
    dst.mkdir(parents=True, exist_ok=True)
    for f in subs:
        subprocess.run([sys.executable, "-m", "modal", "volume", "get", "--force", "panda-router",
                        f"runs/{run}/{f}", str(dst)], cwd=ROOT)


def train_args(run, backbone, extra=""):
    return f"--data-dir {D} --out /vol/runs/{run} --backbone jhu-clsp/ettin-encoder-{backbone} {ANCH} {REC} {extra}"


@app.local_entrypoint()
def main(stage: str = "pilot", gpu: str = "L40S", seeds: str = "0,1,2", teacher: str = "t150m",
         e150: int = 10, e400: int = 6, b150: int = 16):
    if stage == "pilot":  # 150 steps of the 150M per GPU type
        launch([(g, "train.py", train_args(f"pilot_{g.lower()}", "150m",
                                           f"--batch-size {b150} --epochs 1 --max-steps 150 --no-calibrate"),
                 f"pilot_{g}", 0.3) for g in JOBS])
    elif stage == "teachers":
        specs = [(gpu, "train.py", train_args("t150m", "150m", f"--batch-size {b150} --epochs {e150}"), "t150m", 2.5)]
        if e400:
            specs.append((gpu, "train.py", train_args("t400m", "400m", f"--batch-size 16 --epochs {e400}"), "t400m", 6.0))
        for r in launch(specs):
            pull(r["run"])
    elif stage == "cache":
        launch([(gpu, "cache_teacher.py",
                 f"--teacher /vol/runs/{teacher}/best --data-dir {D} --out /vol/cache/{teacher}_train.pt "
                 f"--extra {D}/outcome_v3/train.jsonl", f"cache_{teacher}", 0.3)])
    elif stage == "distill":
        for r in launch([(gpu, "train.py", train_args(f"{teacher}_s32m_seed{s}", "32m",
                          f"--seed {s} --epochs 8 --distill-from /vol/cache/{teacher}_train.pt"),
                          f"{teacher}_s32m_seed{s}", 0.8) for s in seeds.split(",")]):
            pull(r["run"])
    elif stage == "soup":
        runs = " ".join(f"/vol/runs/{teacher}_s32m_seed{s}" for s in seeds.split(","))
        launch([(gpu, "soup.py", f"--runs {runs} --data-dir {D} --out /vol/runs/{teacher}_s32m_soup", f"{teacher}_s32m_soup", 0.2)])
        pull(f"{teacher}_s32m_soup", ("."))
    elif stage == "student68":
        for r in launch([(gpu, "train.py", train_args(f"{teacher}_s68m_seed0", "68m",
                          f"--seed 0 --epochs 8 --distill-from /vol/cache/{teacher}_train.pt"), f"{teacher}_s68m_seed0", 1.5)]):
            pull(r["run"])
