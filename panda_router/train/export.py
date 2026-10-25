"""ONNX export (torch.compile off, dynamic batch+seq), int8 dynamic quantisation with per-head
fp32-vs-int8 comparison on val, and sensitive-node exclusion when any head drops > 1 point."""

import json
import re
import shutil
from pathlib import Path

import numpy as np
import onnx
import onnxruntime as ort
import torch
from onnxruntime.quantization import QuantType, quantize_dynamic

from ..model import HEAD_ORDER
from ..model.decode import decode_probs
from ..model.net import ExportWrapper, load_checkpoint, write_heads_json
from ..text import format_input
from .data import PairAwareBatchSampler, ProfileDataset, stack_labels
from .metrics import compute_metrics, primary_metrics

TOKENIZER_FILES = ("tokenizer.json", "tokenizer_config.json", "special_tokens_map.json", "vocab.txt",
                   "merges.txt", "vocab.json")


def onnx_predict(session: ort.InferenceSession, ds: ProfileDataset, batch_size: int = 32) -> dict:
    names = [o.name for o in session.get_outputs()]
    chunks, order = [], []
    for idx in PairAwareBatchSampler(ds, batch_size, shuffle=False):
        b = ds.collate(idx)
        res = session.run(None, {"input_ids": b["input_ids"].numpy(), "attention_mask": b["attention_mask"].numpy()})
        chunks.append(dict(zip(names, res)))
        order.extend(idx)
    inv = np.argsort(np.asarray(order))
    return {k: np.concatenate([c[k] for c in chunks])[inv] for k in names}


def _session(path) -> ort.InferenceSession:
    return ort.InferenceSession(str(path), providers=["CPUExecutionProvider"])


def export_fp32(model, path: Path, opset: int = 17, seq: int = 64):
    wrapper = ExportWrapper(model).eval()
    ids = torch.randint(5, 1000, (2, seq))
    mask = torch.ones_like(ids)
    mask[1, seq // 2:] = 0
    dyn = {"input_ids": {0: "batch", 1: "seq"}, "attention_mask": {0: "batch", 1: "seq"}}
    dyn.update({k: {0: "batch"} for k in HEAD_ORDER})
    with torch.no_grad():
        torch.onnx.export(wrapper, (ids, mask), str(path), input_names=["input_ids", "attention_mask"],
                          output_names=HEAD_ORDER, dynamic_axes=dyn, opset_version=opset, dynamo=False,
                          do_constant_folding=True)
    onnx.checker.check_model(str(path))


def parity(model, session, tokenizer, texts: list[str]) -> float:
    """Max abs diff torch vs onnx over several sequence lengths and padding patterns."""
    worst = 0.0
    for n in (1, len(texts)):
        enc = tokenizer(texts[:n], padding=True, truncation=True, max_length=512, return_tensors="pt")
        with torch.no_grad():
            t = model(enc["input_ids"], enc["attention_mask"])
        o = session.run(None, {"input_ids": enc["input_ids"].numpy(), "attention_mask": enc["attention_mask"].numpy()})
        for k, v in zip(HEAD_ORDER, o):
            worst = max(worst, float(np.abs(t[k].numpy() - v).max()))
    return worst


def exclusion_stages(model_path: Path, n_layers: int) -> list[list[str]]:
    """Stage 0: quantise all; 1: keep heads fp32; then also keep the last k encoder layers fp32."""
    nodes = [(n.name, n.op_type) for n in onnx.load(str(model_path), load_external_data=False).graph.node
             if n.op_type in ("MatMul", "Gemm")]
    heads = [n for n, _ in nodes if "/backbone/" not in n]
    stages = [[], heads]
    for k in range(1, n_layers + 1):
        layers = {str(i) for i in range(n_layers - k, n_layers)}
        extra = [n for n, _ in nodes if (m := re.search(r"layers\.(\d+)/", n)) and m.group(1) in layers]
        stages.append(heads + extra)
    return stages


def export_artifacts(ckpt_dir, out_dir, data_dir, max_drop: float = 1.0, opset: int = 17,
                     limit_val: int | None = None) -> dict:
    torch._dynamo.config.disable = True
    out = Path(out_dir)
    out.mkdir(parents=True, exist_ok=True)
    model, tok, meta, temps = load_checkpoint(ckpt_dir, "cpu", attn_implementation="eager")
    temps = temps or {}
    fp32_path, int8_path = out / "model.onnx", out / "model.int8.onnx"
    export_fp32(model, fp32_path, opset)
    val_ds = ProfileDataset.from_file(Path(data_dir) / "val.jsonl", tok, meta.get("max_len", 512), limit=limit_val)
    texts = [format_input(val_ds.examples[i]["task"]) for i in range(min(4, len(val_ds)))]
    texts.append(" ".join(texts) * 8)  # > local attention window and > export trace length
    fp32_sess = _session(fp32_path)
    max_abs = parity(model, fp32_sess, tok, texts)
    y = stack_labels(val_ds.labels)
    m_fp32 = compute_metrics(decode_probs(onnx_predict(fp32_sess, val_ds), temps), y)
    p_fp32 = primary_metrics(m_fp32)

    attempts = []
    n_layers = int(getattr(model.backbone.config, "num_hidden_layers", 0))
    for excluded in exclusion_stages(fp32_path, n_layers):
        quantize_dynamic(str(fp32_path), str(int8_path), weight_type=QuantType.QInt8, per_channel=False,
                         nodes_to_exclude=excluded)
        m_int8 = compute_metrics(decode_probs(onnx_predict(_session(int8_path), val_ds), temps), y)
        drops = {k: p_fp32[k] - v for k, v in primary_metrics(m_int8).items()}
        attempts.append({"n_excluded": len(excluded), "drops": drops})
        if max(drops.values()) <= max_drop:
            break
    for f in TOKENIZER_FILES:
        if (Path(ckpt_dir) / f).exists():
            shutil.copy(Path(ckpt_dir) / f, out / f)
    ok = max(attempts[-1]["drops"].values()) <= max_drop
    write_heads_json(out, temps or {}, meta, {"source_checkpoint": str(ckpt_dir), "int8_excluded_nodes": excluded,
                                              "opset": opset})
    metrics = {"val_examples": len(val_ds), "fp32": m_fp32, "int8": m_int8, "int8_drops_points": attempts[-1]["drops"],
               "int8_within_tolerance": ok, "quant_attempts": attempts, "torch_vs_onnx_max_abs": max_abs,
               "size_mb": {"fp32": fp32_path.stat().st_size / 2**20, "int8": int8_path.stat().st_size / 2**20}}
    (out / "metrics.json").write_text(json.dumps(metrics, indent=2))
    return metrics
