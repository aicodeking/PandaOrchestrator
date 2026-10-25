"""Measure training throughput (examples/s, full fwd+bwd+AdamW step incl. regret loss) per backbone.
.venv/bin/python scripts/train/throughput.py --backbones 32m 68m 150m 400m --seq 256 --batch-size 32
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

import torch  # noqa: E402

from panda_router.model.corn import corn_level_probs  # noqa: E402
from panda_router.model.losses import head_losses  # noqa: E402
from panda_router.model.net import ProfilerModel  # noqa: E402
from panda_router.model.soft_matcher import regret_loss, sample_pools  # noqa: E402
from panda_router.train.trainer import autocast, pick_device  # noqa: E402


def sync(dev):
    if dev.type == "mps":
        torch.mps.synchronize()
    elif dev.type == "cuda":
        torch.cuda.synchronize()


def bench(backbone: str, dev, bs: int, seq: int, steps: int, warmup: int, bf16: bool) -> dict:
    model = ProfilerModel.from_backbone(backbone).to(dev).train()
    opt = torch.optim.AdamW(model.parameters(), lr=1e-5)
    ids = torch.randint(10, 30000, (bs, seq), device=dev)
    mask = torch.ones_like(ids)
    y = {"category": torch.softmax(torch.randn(bs, 13), -1), "difficulty": torch.softmax(torch.randn(bs, 10), -1),
         "skills": torch.softmax(torch.randn(bs, 10, 11), -1), "flags": torch.rand(bs, 7),
         "checklist": torch.rand(bs, 24), "out_tokens": torch.rand(bs) + 3, "in_tokens": torch.full((bs,), 4000.0)}
    y = {k: v.to(dev) for k, v in y.items()}
    gen = torch.Generator().manual_seed(0)

    def step():
        with autocast(dev, bf16):
            o = model(ids, mask)
        loss = sum(head_losses(o, y).values())
        pred = {"difficulty": corn_level_probs(o["difficulty"]), "skills": corn_level_probs(o["skills"]),
                "out_p50": o["out_tokens"][:, 1]}
        lab = {"difficulty": y["difficulty"], "skills": y["skills"], "out_p50": y["out_tokens"]}
        loss = loss + 0.05 * regret_loss(pred, lab, y["in_tokens"], sample_pools(bs, 6, gen, dev))
        opt.zero_grad(set_to_none=True)
        loss.backward()
        torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
        opt.step()

    for _ in range(warmup):
        step()
    sync(dev)
    t0 = time.perf_counter()
    for _ in range(steps):
        step()
    sync(dev)
    dt = time.perf_counter() - t0
    n_params = sum(p.numel() for p in model.parameters())
    res = {"backbone": backbone, "params_m": round(n_params / 1e6, 1), "batch_size": bs, "seq": seq,
           "examples_per_s": round(bs * steps / dt, 1), "s_per_step": round(dt / steps, 3), "bf16": bf16}
    if dev.type == "mps":
        res["mps_driver_mem_gb"] = round(torch.mps.driver_allocated_memory() / 2**30, 2)
    del model, opt
    if dev.type == "mps":
        torch.mps.empty_cache()
    return res


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--backbones", nargs="+", default=["32m", "68m", "150m", "400m"])
    ap.add_argument("--seq", type=int, default=256)
    ap.add_argument("--batch-size", type=int, default=32)
    ap.add_argument("--steps", type=int, default=10)
    ap.add_argument("--warmup", type=int, default=3)
    ap.add_argument("--device", default=None)
    ap.add_argument("--no-bf16", action="store_true")
    ap.add_argument("--out", default="checkpoints/throughput.json")
    a = ap.parse_args()
    dev = pick_device(a.device)
    results = []
    for b in a.backbones:
        name = b if "/" in b else f"jhu-clsp/ettin-encoder-{b}"
        r = bench(name, dev, a.batch_size, a.seq, a.steps, a.warmup, not a.no_bf16)
        print(json.dumps(r), flush=True)
        results.append(r)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    Path(a.out).write_text(json.dumps({"device": str(dev), "results": results}, indent=2))


if __name__ == "__main__":
    main()
