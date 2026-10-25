"""ProfilerModel: Ettin (ModernBERT) encoder, mean pooling, dropout, multi-task heads (fp32)."""

import json
import math
from pathlib import Path

import torch
import torch.nn as nn
import torch.nn.functional as F
from safetensors.torch import load_file, save_file
from transformers import AutoConfig, AutoModel, AutoTokenizer

from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, N_DIFFICULTY, N_SKILL_LEVELS, SKILL_AXES, VERSION
from . import HEAD_ORDER

N_AXES = len(SKILL_AXES)
BUCKETS = (64, 128, 256, 512)


def _prep_config(cfg, attn_implementation):
    if hasattr(cfg, "reference_compile"):
        cfg.reference_compile = False  # never torch.compile inside the backbone (MPS + ONNX export)
    cfg._attn_implementation = attn_implementation
    return cfg


def fp32_rotary(backbone: nn.Module) -> nn.Module:
    """Force rotary frequencies to fp32 on every device. HF ModernBERT disables autocast for "cpu" when
    running on MPS, so under MPS bf16 autocast `inv_freq @ position_ids` runs in bf16 and positions > 256
    are quantised: models trained that way lose ~1 val point when served in fp32 (ONNX)."""
    for mod in backbone.modules():
        if type(mod).__name__.endswith("RotaryEmbedding") and not getattr(mod, "_fp32_patched", False):
            fwd = mod.forward

            def forward(x, *args, _fwd=fwd, **kw):
                with torch.autocast(device_type=x.device.type, enabled=False):
                    return _fwd(x, *args, **kw)

            mod.forward = forward
            mod._fp32_patched = True
    return backbone


class ProfilerModel(nn.Module):
    def __init__(self, backbone: nn.Module, dropout: float = 0.1):
        super().__init__()
        self.backbone = fp32_rotary(backbone)
        h = backbone.config.hidden_size
        self.dropout = nn.Dropout(dropout)
        self.heads = nn.ModuleDict({
            "category": nn.Linear(h, len(CATEGORIES)),
            "difficulty": nn.Linear(h, N_DIFFICULTY - 1),
            "skills": nn.Linear(h, N_AXES * (N_SKILL_LEVELS - 1)),
            "flags": nn.Linear(h, len(FLAGS)),
            "checklist": nn.Linear(h, len(CHECKLIST_IDS)),
            "out_tokens": nn.Linear(h, 3),
        })
        with torch.no_grad():
            b = self.heads["out_tokens"].bias
            b[0] = 3.0
            b[1:] = math.log(math.expm1(0.5))

    @classmethod
    def from_backbone(cls, name_or_path: str, dropout: float = 0.1, attn_implementation: str = "sdpa"):
        cfg = _prep_config(AutoConfig.from_pretrained(name_or_path), attn_implementation)
        return cls(AutoModel.from_pretrained(name_or_path, config=cfg), dropout)

    @classmethod
    def from_config(cls, cfg, dropout: float = 0.1, attn_implementation: str = "sdpa"):
        return cls(AutoModel.from_config(_prep_config(cfg, attn_implementation)), dropout)

    def pool(self, input_ids, attention_mask):
        hidden = self.backbone(input_ids=input_ids, attention_mask=attention_mask).last_hidden_state
        m = attention_mask.unsqueeze(-1).float()
        return (hidden.float() * m).sum(1) / m.sum(1).clamp_min(1.0)

    def head_forward(self, pooled: torch.Tensor) -> dict:
        x = self.dropout(pooled.float())
        out = {k: head(x) for k, head in self.heads.items()}
        out["skills"] = out["skills"].view(-1, N_AXES, N_SKILL_LEVELS - 1)
        q = out["out_tokens"]
        p50 = q[:, 0]
        out["out_tokens"] = torch.stack([p50 - F.softplus(q[:, 1]), p50, p50 + F.softplus(q[:, 2])], -1)
        return out

    def forward(self, input_ids, attention_mask) -> dict:
        pooled = self.pool(input_ids, attention_mask)
        dev = pooled.device.type
        with torch.autocast(device_type=dev, enabled=False):
            return self.head_forward(pooled)


class ExportWrapper(nn.Module):
    """Tuple outputs in HEAD_ORDER for ONNX export."""

    def __init__(self, model: ProfilerModel):
        super().__init__()
        self.model = model

    def forward(self, input_ids, attention_mask):
        out = self.model(input_ids, attention_mask)
        return tuple(out[k] for k in HEAD_ORDER)


def label_order() -> dict:
    return {"categories": CATEGORIES, "skill_axes": SKILL_AXES, "flags": FLAGS, "checklist": CHECKLIST_IDS,
            "difficulty_levels": list(range(1, N_DIFFICULTY + 1)), "skill_levels": list(range(N_SKILL_LEVELS)),
            "out_tokens_quantiles": ["p10", "p50", "p90"], "outputs": HEAD_ORDER}


def save_checkpoint(model: ProfilerModel, tokenizer, out_dir, meta: dict, temperatures: dict | None = None):
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model.backbone.config.save_pretrained(out)
    tokenizer.save_pretrained(out)
    state = {k: v.detach().float().cpu().contiguous() for k, v in model.state_dict().items()}
    save_file(state, str(out / "model.safetensors"))
    meta = {**meta, "taxonomy_version": VERSION, "buckets": list(BUCKETS)}
    (out / "profiler_config.json").write_text(json.dumps(meta, indent=2))
    if temperatures is not None:
        write_heads_json(out, temperatures, meta)


def write_heads_json(out_dir, temperatures: dict, meta: dict, extra: dict | None = None):
    heads = {"taxonomy_version": VERSION, "temperatures": temperatures, "label_order": label_order(),
             "backbone": meta.get("backbone"), "max_len": meta.get("max_len", 512),
             "buckets": list(BUCKETS), **(extra or {})}
    Path(out_dir, "heads.json").write_text(json.dumps(heads, indent=2))


def load_checkpoint(ckpt_dir, device="cpu", attn_implementation: str = "sdpa"):
    """-> (model, tokenizer, meta, temperatures or None)."""
    d = Path(ckpt_dir)
    meta = json.loads((d / "profiler_config.json").read_text())
    cfg = AutoConfig.from_pretrained(d)
    model = ProfilerModel.from_config(cfg, meta.get("dropout", 0.1), attn_implementation)
    model.load_state_dict(load_file(str(d / "model.safetensors")))
    model.to(device).eval()
    tok = AutoTokenizer.from_pretrained(d)
    temps = json.loads((d / "heads.json").read_text())["temperatures"] if (d / "heads.json").exists() else None
    return model, tok, meta, temps


def default_lr(backbone: str) -> float:
    name = backbone.lower()
    if "400m" in name or "1b" in name:
        return 3e-5
    if "68m" in name or "150m" in name:
        return 5e-5
    return 1e-4
