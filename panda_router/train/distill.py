"""Cache teacher raw head outputs for a split once (checkpoints/cache/), keyed by example id."""

from pathlib import Path

import torch

from ..model.net import load_checkpoint
from .data import ProfileDataset


def cache_teacher(teacher_dir, data_dir, out_path, split: str = "train", device=None, bf16: bool = True,
                  extra=None) -> Path:
    from .trainer import pick_device, predict

    dev = pick_device(device)
    model, tok, meta, _ = load_checkpoint(teacher_dir, dev)
    ds = ProfileDataset.from_file(Path(data_dir) / f"{split}.jsonl", tok, meta.get("max_len", 512), extra=extra)
    raw = predict(model, ds, dev, 64, bf16)
    out = Path(out_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    torch.save({"ids": [ex["id"] for ex in ds.examples], "teacher": str(teacher_dir), "split": split,
                "outputs": {k: torch.from_numpy(v).float() for k, v in raw.items()}}, out)
    return out
