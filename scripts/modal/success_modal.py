"""v4 router GPU jobs on Modal: fine-tune the chosen 32M profiler on data/train + data/vague_v4 (vague requests).

  .venv/bin/python -m modal run scripts/modal/success_modal.py --stage vague_ft [--init t150m_s32m_soup]

Initialises from /vol/runs/<init> (the souped student), trains on data/train.jsonl + data/vague_v4/train.jsonl and
validates on data/val.jsonl + data/vague_v4/val.jsonl, same anchors / --under-w 2.5 recipe as the v4 candidates (no
distillation: the teacher cache has no logits for the vague rows). Costs go to checkpoints/v4/cost_log.jsonl;
launches refuse past this worker's $15 budget or the $30 project total.
The success model stays a frozen-feature head (scripts/outcomes/train_success_head.py); no end-to-end job is run
unless its CV beats the head (see eval_reports/v4/REPORT.md).
"""
import json
import subprocess
import sys
import time
from pathlib import Path

import modal

ROOT = Path(__file__).resolve().parents[2] if len(Path(__file__).resolve().parents) > 2 else Path("/root/repo")
COST_LOG = ROOT / "checkpoints/v4/cost_log.jsonl"
MY_PREFIX = "v4r_"
MY_CAP_USD, TOTAL_CAP_USD = 15.0, 30.0
PRICE = {"L40S": 0.000542}  # $/s list price; x1.08 for the container's CPU/memory
OVERHEAD = 1.08

app = modal.App("panda-router-v4-router")
vol = modal.Volume.from_name("panda-router", create_if_missing=True)
image = (
    modal.Image.debian_slim(python_version="3.12")
    .pip_install("torch", "transformers==4.57.6", "numpy", "scipy", "scikit-learn", "jsonschema",
                 "onnxruntime", "onnx", "datasets", "accelerate")
    .env({"HF_HOME": "/vol/hf", "TOKENIZERS_PARALLELISM": "false"})
    .add_local_dir(ROOT / "panda_router", "/root/repo/panda_router", ignore=["**/__pycache__", "*.pyc"])
    .add_local_dir(ROOT / "schemas", "/root/repo/schemas")
)
D = "/vol/data"


@app.function(gpu="L40S", image=image, volumes={"/vol": vol}, timeout=2 * 3600)
def finetune(init: str, data_dir: str, out: str, epochs: int, lr: float, seed: int) -> dict:
    sys.path.insert(0, "/root/repo")
    from panda_router.model.net import ProfilerModel, load_checkpoint
    from panda_router.train.trainer import TrainConfig, train

    # warm start: the trainer builds from a HF backbone name; load the full profiler (encoder + heads) instead
    ProfilerModel.from_backbone = classmethod(lambda cls, path, dropout=0.1, **_: load_checkpoint(path)[0].train())
    vol.reload()
    t0 = time.time()
    summary = train(TrainConfig(
        backbone=init, data_dir=data_dir, out=out, epochs=epochs, seed=seed, lr=lr, regret_weight=0.0,
        anchors=f"{D}/attempt_outcome_v3/train.jsonl", anchor_weight=0.3,
        outcome_anchors=f"{D}/outcome_v3/train.jsonl", outcome_val=f"{D}/outcome_v3/val.jsonl",
        under_w=2.5, max_len=512))
    vol.commit()
    return {"wall_s": time.time() - t0, "summary": {k: v for k, v in summary.items() if k != "history"}}


def _spent(prefix: str = "") -> float:
    if not COST_LOG.exists():
        return 0.0
    rows = [json.loads(ln) for ln in COST_LOG.read_text().splitlines() if ln.strip()]
    return sum(r["usd"] for r in rows if r["run"].startswith(prefix))


def _log(run: str, wall_s: float) -> None:
    usd = wall_s * PRICE["L40S"] * OVERHEAD
    total = _spent() + usd
    with COST_LOG.open("a") as f:
        f.write(json.dumps({"run": run, "gpu": "L40S", "wall_s": wall_s, "usd": round(usd, 4),
                            "total_usd": round(total, 4)}) + "\n")
    print(f"[cost] {run} {wall_s:.0f}s ${usd:.2f}; mine ${_spent(MY_PREFIX):.2f}, total ${total:.2f}", flush=True)


def _merge(dst: Path) -> None:
    dst.mkdir(parents=True, exist_ok=True)
    for split in ("train", "val"):
        rows = (ROOT / f"data/{split}.jsonl").read_text().rstrip("\n") + "\n"
        rows += (ROOT / f"data/vague_v4/{split}.jsonl").read_text().rstrip("\n") + "\n"
        (dst / f"{split}.jsonl").write_text(rows)


@app.local_entrypoint()
def main(stage: str = "vague_ft", init: str = "t150m_s32m_soup", epochs: int = 3, lr: float = 3e-5,
         seed: int = 0, est_usd: float = 0.5):
    if stage != "vague_ft":
        raise SystemExit(f"unknown stage {stage!r}")
    if _spent(MY_PREFIX) + est_usd > MY_CAP_USD or _spent() + est_usd > TOTAL_CAP_USD:
        raise SystemExit(f"cap: mine ${_spent(MY_PREFIX):.2f}, total ${_spent():.2f}, est ${est_usd}")
    run = f"{MY_PREFIX}vague_ft_{init}_e{epochs}_s{seed}"
    local = ROOT / "checkpoints/v4/data_vague_ft"
    _merge(local)
    for split in ("train", "val"):
        subprocess.run([sys.executable, "-m", "modal", "volume", "put", "--force", "panda-router",
                        str(local / f"{split}.jsonl"), f"data_vague_ft/{split}.jsonl"], cwd=ROOT, check=True)
    t0 = time.time()
    try:
        res = finetune.remote(f"/vol/runs/{init}", "/vol/data_vague_ft", f"/vol/runs/{run}", epochs, lr, seed)
        _log(run, res["wall_s"] + 60)  # + container start / image
    except Exception:
        _log(run + "_FAILED", time.time() - t0)
        raise
    print(json.dumps(res["summary"], indent=1, default=str)[:3000])
    dst = ROOT / "checkpoints/v4" / run
    dst.mkdir(parents=True, exist_ok=True)
    subprocess.run([sys.executable, "-m", "modal", "volume", "get", "--force", "panda-router",
                    f"runs/{run}/best", str(dst)], cwd=ROOT, check=True)
