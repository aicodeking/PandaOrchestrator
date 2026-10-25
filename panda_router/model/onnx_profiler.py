"""Serving profilers: OnnxProfiler (onnxruntime CPU, no torch needed) and TorchProfiler (checkpoint dir)."""

import json
import time
from pathlib import Path

import numpy as np

from ..profile import Profiler, TaskProfile
from ..taxonomy import VERSION
from ..text import format_input
from . import HEAD_ORDER
from .decode import decode_probs, to_profiles


def _tokenizer(path):
    from transformers import AutoTokenizer

    return AutoTokenizer.from_pretrained(path)


class OnnxProfiler(Profiler):
    def __init__(self, artifacts_dir, quantized: bool = True, threads: int | None = None):
        import onnxruntime as ort

        d = Path(artifacts_dir)
        self.heads = json.loads((d / "heads.json").read_text())
        if self.heads.get("taxonomy_version") != VERSION:
            raise ValueError(f"artifact taxonomy {self.heads.get('taxonomy_version')} != {VERSION}")
        self.temps = self.heads["temperatures"]
        self.max_len = int(self.heads.get("max_len", 512))
        self.tokenizer = _tokenizer(d)
        opts = ort.SessionOptions()
        if threads:
            opts.intra_op_num_threads = threads
        path = d / ("model.int8.onnx" if quantized else "model.onnx")
        self.name = f"OnnxProfiler({d.resolve().name}/{path.name})"  # shown as router.profiler
        self.session = ort.InferenceSession(str(path), opts, providers=["CPUExecutionProvider"])
        self.output_names = [o.name for o in self.session.get_outputs()]

    def raw(self, input_ids: np.ndarray, attention_mask: np.ndarray) -> dict:
        res = self.session.run(None, {"input_ids": input_ids.astype(np.int64),
                                      "attention_mask": attention_mask.astype(np.int64)})
        return dict(zip(self.output_names, res))

    def profile_batch(self, tasks: list[dict]) -> list[TaskProfile]:
        enc = self.tokenizer([format_input(t) for t in tasks], truncation=True, max_length=self.max_len,
                             padding=True, return_tensors="np")
        return to_profiles(decode_probs(self.raw(enc["input_ids"], enc["attention_mask"]), self.temps))

    def profile(self, task: dict) -> TaskProfile:
        return self.profile_batch([task])[0]


class TorchProfiler(Profiler):
    def __init__(self, checkpoint_dir, device: str = "cpu"):
        import torch

        from .net import load_checkpoint

        self._torch = torch
        self.model, self.tokenizer, self.meta, temps = load_checkpoint(checkpoint_dir, device)
        self.temps = temps or {}
        self.device = device
        self.max_len = int(self.meta.get("max_len", 512))

    def profile_batch(self, tasks: list[dict]) -> list[TaskProfile]:
        enc = self.tokenizer([format_input(t) for t in tasks], truncation=True, max_length=self.max_len,
                             padding=True, return_tensors="pt")
        with self._torch.no_grad():
            out = self.model(enc["input_ids"].to(self.device), enc["attention_mask"].to(self.device))
        raw = {k: out[k].float().cpu().numpy() for k in HEAD_ORDER}
        return to_profiles(decode_probs(raw, self.temps))

    def profile(self, task: dict) -> TaskProfile:
        return self.profile_batch([task])[0]


def bench_latency(profiler: Profiler, tasks: list[dict], n: int = 200, warmup: int = 10) -> dict:
    """Batch-1 wall-clock latency of profiler.profile (tokenize + run + decode), ms."""
    for i in range(warmup):
        profiler.profile(tasks[i % len(tasks)])
    times = []
    for i in range(n):
        t0 = time.perf_counter()
        profiler.profile(tasks[i % len(tasks)])
        times.append((time.perf_counter() - t0) * 1000)
    a = np.asarray(times)
    return {"n": n, "p50_ms": float(np.percentile(a, 50)), "p95_ms": float(np.percentile(a, 95)),
            "mean_ms": float(a.mean())}
