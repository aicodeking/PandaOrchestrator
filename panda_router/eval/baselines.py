"""Profilers used by the evaluation harness: label->profile (oracle), kNN baseline, and a loader for
`--profiler {heuristic,knn,onnx:<dir>,torch:<ckpt>}`. Model/heuristic modules are imported lazily."""

from __future__ import annotations

import math
from pathlib import Path

import numpy as np

from ..profile import Profiler, TaskProfile
from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES
from ..text import format_input

ROOT = Path(__file__).resolve().parent.parent.parent
KNN_ENCODER = "jhu-clsp/ettin-encoder-32m"
OUT_SPREAD = 0.5  # log10 half-width used for p10/p90 when a label has only a point estimate


def label_profile(labels: dict) -> TaskProfile:
    """CONTRACTS.md soft labels -> TaskProfile (the oracle profile)."""
    o = float(labels["out_tokens_log10"])
    cat = {c: float(labels["category"].get(c, 0.0)) for c in CATEGORIES}
    return TaskProfile(
        category=cat,
        difficulty=[float(x) for x in labels["difficulty"]],
        skills={ax: [float(x) for x in labels["skills"][ax]] for ax in SKILL_AXES},
        flags={f: float(labels["flags"].get(f, 0.0)) for f in FLAGS},
        checklist={c: float(labels["checklist"].get(c, 0.0)) for c in CHECKLIST_IDS},
        out_tokens_log10={"p10": o - OUT_SPREAD, "p50": o, "p90": o + OUT_SPREAD},
    )


def average_labels(rows: list[dict], weights: list[float] | None = None) -> dict:
    """Weighted average of CONTRACTS.md label dicts (all heads are linear in the average)."""
    w = np.asarray(weights if weights is not None else [1.0] * len(rows), float)
    w = w / w.sum()
    out = {
        "category": {c: float(sum(wi * r["category"].get(c, 0.0) for wi, r in zip(w, rows))) for c in CATEGORIES},
        "difficulty": list(np.sum([wi * np.asarray(r["difficulty"], float) for wi, r in zip(w, rows)], axis=0)),
        "skills": {ax: list(np.sum([wi * np.asarray(r["skills"][ax], float) for wi, r in zip(w, rows)], axis=0))
                   for ax in SKILL_AXES},
        "flags": {f: float(sum(wi * r["flags"].get(f, 0.0) for wi, r in zip(w, rows))) for f in FLAGS},
        "checklist": {c: float(sum(wi * r["checklist"].get(c, 0.0) for wi, r in zip(w, rows))) for c in CHECKLIST_IDS},
        "out_tokens_log10": float(sum(wi * r["out_tokens_log10"] for wi, r in zip(w, rows))),
    }
    return out


class MeanPoolEncoder:
    """Mean-pooled, L2-normalised sentence embeddings from a HF encoder (CPU)."""

    def __init__(self, name: str = KNN_ENCODER, max_length: int = 512, batch_size: int = 32):
        import torch
        from transformers import AutoModel, AutoTokenizer

        self.torch = torch
        self.tok = AutoTokenizer.from_pretrained(name)
        self.model = AutoModel.from_pretrained(name).eval()
        self.max_length, self.batch_size = max_length, batch_size

    def encode(self, texts: list[str]) -> np.ndarray:
        out = []
        with self.torch.inference_mode():
            for i in range(0, len(texts), self.batch_size):
                b = self.tok(texts[i:i + self.batch_size], padding=True, truncation=True,
                             max_length=self.max_length, return_tensors="pt")
                h = self.model(**b).last_hidden_state
                m = b["attention_mask"].unsqueeze(-1).to(h.dtype)
                e = (h * m).sum(1) / m.sum(1).clamp(min=1)
                out.append(self.torch.nn.functional.normalize(e, dim=-1).float().numpy())
        return np.concatenate(out) if out else np.zeros((0, 1), np.float32)


class KNNProfiler(Profiler):
    """Embed with ettin-encoder-32m (mean pooling), average the labels of the k nearest training tasks."""

    def __init__(self, train_rows: list[dict], k: int = 10, encoder: MeanPoolEncoder | None = None,
                 cache_path: str | Path | None = None):
        self.k = k
        self.encoder = encoder or MeanPoolEncoder()
        self.labels = [r["labels"] for r in train_rows]
        texts = [format_input(r["task"]) for r in train_rows]
        emb = None
        if cache_path and Path(cache_path).exists():
            z = np.load(cache_path, allow_pickle=False)
            if z["ids"].tolist() == [r["id"] for r in train_rows]:
                emb = z["emb"]
        if emb is None:
            emb = self.encoder.encode(texts)
            if cache_path:
                Path(cache_path).parent.mkdir(parents=True, exist_ok=True)
                np.savez(cache_path, ids=np.array([r["id"] for r in train_rows]), emb=emb)
        self.emb = emb

    def profile(self, task: dict) -> TaskProfile:
        q = self.encoder.encode([format_input(task)])[0]
        sims = self.emb @ q
        idx = np.argsort(-sims)[: self.k]
        return label_profile(average_labels([self.labels[i] for i in idx]))


def load_profiler(spec: str, train_path: str | Path | None = None, k: int = 10) -> Profiler:
    if spec == "heuristic":
        from ..heuristic import HeuristicProfiler

        return HeuristicProfiler()
    if spec == "knn":
        from .gold import read_jsonl

        train_path = Path(train_path or ROOT / "data" / "train.jsonl")
        rows = read_jsonl(train_path)
        if not rows:
            raise FileNotFoundError(f"kNN baseline needs labelled training data at {train_path}")
        cache = ROOT / "eval_reports" / "cache" / f"knn_{train_path.stem}_{len(rows)}.npz"
        return KNNProfiler(rows, k=k, cache_path=cache)
    if spec == "fixed_average":  # same mean training profile for every task: the floor any profiler must beat
        from .gold import read_jsonl

        rows = read_jsonl(Path(train_path or ROOT / "data" / "train.jsonl"))
        mean = label_profile(average_labels([r["labels"] for r in rows if "labels" in r]))

        class _Fixed(Profiler):
            name = "fixed_average"

            def profile(self, task: dict) -> TaskProfile:
                return mean

        return _Fixed()
    if spec.startswith("onnx:"):
        from ..model import OnnxProfiler

        return OnnxProfiler(spec.split(":", 1)[1])
    if spec.startswith("torch:"):
        from ..model import TorchProfiler

        return TorchProfiler(spec.split(":", 1)[1])
    raise ValueError(f"unknown profiler spec {spec!r}")


def finite(x: float) -> bool:
    return x is not None and not math.isnan(x)
