"""Plain PyTorch training loop (MPS-first): buckets, bf16 autocast, AdamW, warmup+linear decay,
early stopping, minimal-pair ranking loss, decision-focused regret loss and teacher distillation."""

import json
import math
import random
import time
from dataclasses import asdict, dataclass
from pathlib import Path

import numpy as np
import torch
from transformers import AutoTokenizer

from ..model.corn import corn_level_probs
from ..model.decode import decode_probs
from ..model.losses import LossNormalizer, anchor_loss, distill_losses, head_losses, pair_loss
from ..model.net import ProfilerModel, default_lr, save_checkpoint
from ..model.soft_matcher import regret_loss, sample_pools
from .data import PairAwareBatchSampler, ProfileDataset, load_anchors, stack_labels
from .metrics import compute_metrics


@dataclass
class TrainConfig:
    backbone: str = "jhu-clsp/ettin-encoder-32m"
    data_dir: str = "data"
    out: str = "checkpoints/run"
    epochs: int = 6
    seed: int = 0
    init_seed: int = 0
    batch_size: int = 32
    eval_batch_size: int = 64
    lr: float | None = None
    weight_decay: float = 0.01
    warmup_frac: float = 0.06
    grad_clip: float = 1.0
    dropout: float = 0.1
    max_len: int = 512
    regret_weight: float = 0.05
    regret_tau: float = 0.05
    regret_cards: int = 6
    regret_mode: str = "max_utility"  # or "cheapest" (soft cheapest_above_threshold, the serving default)
    pair_weight: float = 0.5
    pair_margin: float = 0.5
    single_teacher_weight: float = 0.5
    anchors: str | None = None
    anchor_weight: float = 0.0
    outcome_anchors: str | None = None  # jsonl of difficulty-only outcome rows (scripts/train/outcome_anchors.py)
    outcome_val: str | None = None  # held-out outcome rows: Spearman logged per epoch (not used for selection)
    distill_from: str | None = None
    distill_T: float = 3.0
    distill_alpha: float = 0.5
    patience: int = 2
    device: str | None = None
    bf16: bool = True
    max_steps: int | None = None
    limit_train: int | None = None
    limit_val: int | None = None
    calibrate: bool = True
    empty_cache_every: int = 100


def pick_device(pref: str | None = None) -> torch.device:
    if pref:
        return torch.device(pref)
    if torch.backends.mps.is_available():
        return torch.device("mps")
    return torch.device("cuda" if torch.cuda.is_available() else "cpu")


def seed_everything(seed: int):
    random.seed(seed)
    np.random.seed(seed)
    torch.manual_seed(seed)


def autocast(device: torch.device, enabled: bool):
    return torch.autocast(device_type=device.type, dtype=torch.bfloat16, enabled=enabled and device.type != "cpu")


@torch.no_grad()
def predict(model, ds: ProfileDataset, device, batch_size: int = 64, bf16: bool = True) -> dict:
    """Raw head outputs (numpy, dataset order) using length-bucketed batches."""
    model.eval()
    sampler = PairAwareBatchSampler(ds, batch_size, shuffle=False)
    chunks, order = [], []
    for idx in sampler:
        b = ds.collate(idx)
        with autocast(device, bf16):
            out = model(b["input_ids"].to(device), b["attention_mask"].to(device))
        chunks.append({k: v.float().cpu().numpy() for k, v in out.items()})
        order.extend(idx)
    inv = np.argsort(np.asarray(order))
    return {k: np.concatenate([c[k] for c in chunks])[inv] for k in chunks[0]}


def evaluate(model, ds, device, batch_size=64, bf16=True, temps=None) -> tuple[dict, dict]:
    raw = predict(model, ds, device, batch_size, bf16)
    return compute_metrics(decode_probs(raw, temps), stack_labels(ds.labels)), raw


def outcome_spearman(model, ds: ProfileDataset, device, batch_size=64, bf16=True) -> float:
    """Spearman of expected difficulty vs the outcome anchor on difficulty-only rows."""
    from scipy.stats import spearmanr

    raw = predict(model, ds, device, batch_size, bf16)
    ed = (decode_probs(raw)["difficulty"] * np.arange(1, 11)).sum(-1)
    return round(float(spearmanr(ed, stack_labels(ds.labels)["anchor"])[0]), 4)


def _to(d: dict, device):
    return {k: v.to(device) for k, v in d.items()}


def load_teacher_cache(path) -> dict:
    return torch.load(path, map_location="cpu", weights_only=True)


def train(cfg: TrainConfig) -> dict:
    seed_everything(cfg.seed)
    device = pick_device(cfg.device)
    out = Path(cfg.out)
    out.mkdir(parents=True, exist_ok=True)
    lr = cfg.lr or default_lr(cfg.backbone)
    tok = AutoTokenizer.from_pretrained(cfg.backbone)
    teacher = load_teacher_cache(cfg.distill_from) if cfg.distill_from else None
    data = Path(cfg.data_dir)
    anchors = load_anchors(cfg.anchors) if cfg.anchors and cfg.anchor_weight > 0 else None
    use_anchor = cfg.anchor_weight > 0 and bool(anchors or cfg.outcome_anchors)
    train_ds = ProfileDataset.from_file(data / "train.jsonl", tok, cfg.max_len, teacher, cfg.limit_train,
                                        extra=cfg.outcome_anchors if cfg.anchor_weight > 0 else None,
                                        single_teacher_weight=cfg.single_teacher_weight, anchors=anchors)
    val_ds = ProfileDataset.from_file(data / "val.jsonl", tok, cfg.max_len, None, cfg.limit_val)
    oval_ds = ProfileDataset.from_file(cfg.outcome_val, tok, cfg.max_len) if cfg.outcome_val else None
    torch.manual_seed(cfg.init_seed)  # same head init for every seed, so seed runs can be souped
    model = ProfilerModel.from_backbone(cfg.backbone, cfg.dropout).to(device)
    if cfg.seed != cfg.init_seed:
        seed_everything(cfg.seed)

    sampler = PairAwareBatchSampler(train_ds, cfg.batch_size, seed=cfg.seed)
    steps_per_epoch = len(sampler)
    total = cfg.epochs * steps_per_epoch if cfg.max_steps is None else min(cfg.max_steps, cfg.epochs * steps_per_epoch)
    warmup = max(1, int(cfg.warmup_frac * total))
    decay, no_decay = [], []
    for n, p in model.named_parameters():
        (no_decay if p.ndim < 2 or "norm" in n.lower() else decay).append(p)
    opt = torch.optim.AdamW([{"params": decay, "weight_decay": cfg.weight_decay},
                             {"params": no_decay, "weight_decay": 0.0}], lr=lr)
    sched = torch.optim.lr_scheduler.LambdaLR(
        opt, lambda s: (s + 1) / warmup if s < warmup else max(0.0, (total - s) / max(1, total - warmup)))
    norm = LossNormalizer()
    gen = torch.Generator().manual_seed(cfg.seed + 12345)
    meta = {**asdict(cfg), "lr": lr, "steps_per_epoch": steps_per_epoch, "total_steps": total}
    (out / "train_config.json").write_text(json.dumps(meta, indent=2))

    history, best, bad, step = [], -math.inf, 0, 0
    t_start = time.time()
    n_seen = 0
    for epoch in range(cfg.epochs):
        model.train()
        sampler.set_epoch(epoch)
        sums: dict[str, float] = {}
        nb = 0
        for idx in sampler:
            if step >= total:
                break
            b = train_ds.collate(idx)
            y = _to(b["y"], device)
            with autocast(device, cfg.bf16):
                o = model(b["input_ids"].to(device), b["attention_mask"].to(device))
            o = {k: v.float() for k, v in o.items()}
            parts = head_losses(o, y)
            loss = 0.0
            if "teacher" in b:
                kd = distill_losses(o, _to(b["teacher"], device), cfg.distill_T, y["w"])
                for k in parts:
                    loss = loss + (1 - cfg.distill_alpha) * norm(k, parts[k]) + cfg.distill_alpha * norm("kd_" + k, kd[k])
                parts.update({"kd_" + k: v for k, v in kd.items()})
            else:
                for k, v in parts.items():
                    loss = loss + norm(k, v)
            if cfg.pair_weight > 0 and b["pairs"]:
                pl = pair_loss(o, b["pairs"], cfg.pair_margin)
                if pl is not None:
                    parts["pair"] = pl
                    loss = loss + cfg.pair_weight * norm("pair", pl)
            if use_anchor and (al := anchor_loss(o, y["anchor"], y["anchor_w"])) is not None:
                parts["anchor"] = al
                loss = loss + cfg.anchor_weight * norm("anchor", al)
            if cfg.regret_weight > 0 and bool((y["w"] > 0).any()):
                pool = sample_pools(len(idx), cfg.regret_cards, gen, device)
                pred = {"difficulty": corn_level_probs(o["difficulty"]), "skills": corn_level_probs(o["skills"]),
                        "out_p50": o["out_tokens"][:, 1]}
                lab = {"difficulty": y["difficulty"], "skills": y["skills"], "out_p50": y["out_tokens"]}
                rl = regret_loss(pred, lab, y["in_tokens"], pool, cfg.regret_tau, mode=cfg.regret_mode,
                                 w=(y["w"] > 0).float())
                parts["regret"] = rl
                loss = loss + cfg.regret_weight * norm("regret", rl)
            opt.zero_grad(set_to_none=True)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), cfg.grad_clip)
            opt.step()
            sched.step()
            step += 1
            nb += 1
            n_seen += len(idx)
            if device.type == "mps" and step % cfg.empty_cache_every == 0:
                torch.mps.empty_cache()  # the MPS caching allocator otherwise grows across length buckets
            if step % 50 == 0:
                mem = round(torch.mps.driver_allocated_memory() / 2**30, 1) if device.type == "mps" else None
                print(json.dumps({"step": step, "of": total, "ex_per_s": round(n_seen / (time.time() - t_start), 1),
                                  "mps_gb": mem}), flush=True)
            sums["total"] = sums.get("total", 0.0) + float(loss.detach())
            for k, v in parts.items():
                sums[k] = sums.get(k, 0.0) + float(v.detach())
        train_losses = {k: v / max(nb, 1) for k, v in sums.items()}
        metrics, _ = evaluate(model, val_ds, device, cfg.eval_batch_size, cfg.bf16)
        if device.type == "mps":
            torch.mps.empty_cache()
        rec = {"epoch": epoch, "step": step, "train": train_losses, "val": metrics,
               "elapsed_s": time.time() - t_start}
        if oval_ds is not None:
            rec["outcome_val_spearman"] = outcome_spearman(model, oval_ds, device, cfg.eval_batch_size, cfg.bf16)
        history.append(rec)
        print(json.dumps({"epoch": epoch, "step": step, "loss": train_losses.get("total"),
                          "val_score": round(metrics["val_score"], 3),
                          "outcome_val_spearman": rec.get("outcome_val_spearman")}), flush=True)
        if metrics["val_score"] > best:
            best, bad = metrics["val_score"], 0
            save_checkpoint(model, tok, out / "best", {"backbone": cfg.backbone, "dropout": cfg.dropout,
                                                       "max_len": cfg.max_len, "val_score": best, "seed": cfg.seed})
        else:
            bad += 1
            if bad > cfg.patience:
                break
        if step >= total:
            break

    summary = {"best_val_score": best, "epochs_run": len(history), "steps": step,
               "train_examples_per_s": n_seen / max(time.time() - t_start, 1e-9),
               "loss_init": norm.state_dict(), "history": history, "best_dir": str(out / "best")}
    if cfg.calibrate:
        from .calibrate import calibrate_checkpoint
        summary["calibration"] = calibrate_checkpoint(out / "best", val_ds=val_ds, device=device, bf16=cfg.bf16)
    (out / "train_summary.json").write_text(json.dumps(summary, indent=2))
    return summary
