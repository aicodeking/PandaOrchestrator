"""Greedy model soup (Wortsman et al., 2022) over seed runs of one backbone, ranked by val score."""

import json
from pathlib import Path

import torch
from safetensors.torch import load_file

from ..model.net import load_checkpoint, save_checkpoint
from .data import ProfileDataset


def greedy_soup(run_dirs: list, data_dir, out_dir, device=None, bf16: bool = True) -> dict:
    from .trainer import evaluate, pick_device

    dev = pick_device(device)
    ckpts = [Path(r) / "best" if (Path(r) / "best").exists() else Path(r) for r in run_dirs]
    model, tok, meta, _ = load_checkpoint(ckpts[0], dev)
    val_ds = ProfileDataset.from_file(Path(data_dir) / "val.jsonl", tok, meta.get("max_len", 512))
    states, scores = {}, {}
    for c in ckpts:
        sd = load_file(str(c / "model.safetensors"))
        model.load_state_dict(sd)
        scores[str(c)] = evaluate(model, val_ds, dev, 64, bf16)[0]["val_score"]
        states[str(c)] = sd
    ranked = sorted(scores, key=scores.get, reverse=True)
    members, soup = [ranked[0]], {k: v.clone() for k, v in states[ranked[0]].items()}
    best = scores[ranked[0]]
    for cand in ranked[1:]:
        n = len(members)
        trial = {k: (soup[k] * n + states[cand][k]) / (n + 1) for k in soup}
        model.load_state_dict(trial)
        s = evaluate(model, val_ds, dev, 64, bf16)[0]["val_score"]
        if s >= best:
            members, soup, best = members + [cand], trial, s
    model.load_state_dict(soup)
    out = Path(out_dir)
    save_checkpoint(model, tok, out, {**meta, "val_score": best, "soup_members": members})
    report = {"individual": scores, "members": members, "soup_val_score": best}
    (out / "soup.json").write_text(json.dumps(report, indent=2))
    if dev.type == "mps":
        torch.mps.empty_cache()
    return report
