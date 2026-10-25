"""Dataset, label encoding, fixed-length buckets and the pair-aware batch sampler."""

import json
import random
from collections import defaultdict
from pathlib import Path

import numpy as np
import torch

from ..model.net import BUCKETS
from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, N_DIFFICULTY, N_SKILL_LEVELS, SKILL_AXES
from ..text import format_input

DEFAULT_IN_TOKENS = 2000.0


def load_jsonl(path) -> list[dict]:
    with open(path) as f:
        return [json.loads(line) for line in f if line.strip()]


def _norm(v):
    v = np.asarray(v, dtype=np.float32)
    s = v.sum()
    return v / s if s > 0 else np.full_like(v, 1.0 / len(v))


def encode_labels(ex: dict) -> dict:
    lab = ex["labels"]
    ctx = (ex.get("task") or {}).get("context") or {}
    return {
        "category": _norm([lab["category"].get(c, 0.0) for c in CATEGORIES]),
        "difficulty": _norm(lab["difficulty"]),
        "skills": np.stack([_norm(lab["skills"].get(a, [1.0] + [0.0] * (N_SKILL_LEVELS - 1))) for a in SKILL_AXES]),
        "flags": np.asarray([lab["flags"].get(f, 0.0) for f in FLAGS], np.float32),
        "checklist": np.asarray([lab["checklist"].get(c, 0.0) for c in CHECKLIST_IDS], np.float32),
        "out_tokens": np.float32(lab["out_tokens_log10"]),
        "in_tokens": np.float32(ctx.get("estimated_input_tokens") or DEFAULT_IN_TOKENS),
    }


def stack_labels(items: list[dict]) -> dict:
    return {k: np.stack([it[k] for it in items]) for k in items[0]}


def bucket_len(n: int, max_len: int = 512) -> int:
    for b in BUCKETS:
        if n <= b and b <= max_len:
            return b
    return max_len


class ProfileDataset:
    def __init__(self, examples: list[dict], tokenizer, max_len: int = 512, teacher: dict | None = None):
        self.examples = examples
        self.max_len = max_len
        texts = [format_input(ex["task"]) for ex in examples]
        enc = tokenizer(texts, truncation=True, max_length=max_len)
        self.ids = enc["input_ids"]
        self.pad_id = tokenizer.pad_token_id if tokenizer.pad_token_id is not None else 0
        self.labels = [encode_labels(ex) for ex in examples]
        self.index = {ex["id"]: i for i, ex in enumerate(examples)}
        self.pairs: dict[int, tuple[int, dict]] = {}  # edited idx -> (original idx, expected_delta)
        for i, ex in enumerate(examples):
            orig = ex.get("pair_of")
            if ex.get("source") == "minimal-pair" and orig in self.index:
                self.pairs[i] = (self.index[orig], (ex.get("meta") or {}).get("expected_delta") or {})
        self.teacher = None
        if teacher is not None:
            pos = {tid: k for k, tid in enumerate(teacher["ids"])}
            missing = [ex["id"] for ex in examples if ex["id"] not in pos]
            if missing:
                raise ValueError(f"teacher cache misses {len(missing)} ids, e.g. {missing[:3]}")
            order = torch.tensor([pos[ex["id"]] for ex in examples])
            self.teacher = {k: v[order] for k, v in teacher["outputs"].items()}

    @classmethod
    def from_file(cls, path, tokenizer, max_len=512, teacher=None, limit: int | None = None):
        ex = load_jsonl(path)
        return cls(ex[:limit] if limit else ex, tokenizer, max_len, teacher)

    def __len__(self):
        return len(self.examples)

    def units(self) -> list[list[int]]:
        """Groups of indices that must share a batch (an original and all its minimal-pair edits)."""
        root = {}
        for i in range(len(self)):
            r = i
            seen = set()
            while r in self.pairs and r not in seen:
                seen.add(r)
                r = self.pairs[r][0]
            root[i] = r
        groups = defaultdict(list)
        for i, r in root.items():
            groups[r].append(i)
        return [sorted(g) for g in groups.values()]

    def collate(self, idx: list[int]) -> dict:
        n = max(len(self.ids[i]) for i in idx)
        L = bucket_len(n, self.max_len)
        input_ids = torch.full((len(idx), L), self.pad_id, dtype=torch.long)
        mask = torch.zeros((len(idx), L), dtype=torch.long)
        for r, i in enumerate(idx):
            ids = self.ids[i][:L]
            input_ids[r, : len(ids)] = torch.tensor(ids)
            mask[r, : len(ids)] = 1
        y = {k: torch.from_numpy(v) for k, v in stack_labels([self.labels[i] for i in idx]).items()}
        local = {g: r for r, g in enumerate(idx)}
        pairs = [(local[i], local[self.pairs[i][0]], self.pairs[i][1])
                 for i in idx if i in self.pairs and self.pairs[i][0] in local]
        batch = {"input_ids": input_ids, "attention_mask": mask, "y": y, "pairs": pairs, "idx": idx}
        if self.teacher is not None:
            t = torch.tensor(idx)
            batch["teacher"] = {k: v[t] for k, v in self.teacher.items()}
        return batch


class PairAwareBatchSampler:
    """Batches never split a pair unit; each batch holds a single length bucket (fixed shapes on MPS)."""

    def __init__(self, ds: ProfileDataset, batch_size: int, seed: int = 0, shuffle: bool = True):
        self.ds, self.bs, self.seed, self.shuffle = ds, batch_size, seed, shuffle
        self.epoch = 0
        by_bucket = defaultdict(list)
        for u in ds.units():
            by_bucket[bucket_len(max(len(ds.ids[i]) for i in u), ds.max_len)].append(u)
        self.by_bucket = dict(by_bucket)

    def set_epoch(self, e: int):
        self.epoch = e

    def batches(self) -> list[list[int]]:
        rng = random.Random(self.seed * 1000 + self.epoch)
        out = []
        for b in sorted(self.by_bucket):
            units = list(self.by_bucket[b])
            if self.shuffle:
                rng.shuffle(units)
            cur = []
            for u in units:
                if cur and len(cur) + len(u) > self.bs:
                    out.append(cur)
                    cur = []
                cur.extend(u)
            if cur:
                out.append(cur)
        if self.shuffle:
            rng.shuffle(out)
        return out

    def __iter__(self):
        return iter(self.batches())

    def __len__(self):
        return len(self.batches())
