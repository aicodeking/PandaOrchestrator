"""Stage 4: pairwise difficulty judgments (Codex, both orders) -> Bradley-Terry -> calibrated 1-10.

BT scores are only comparable within a category (pairs are sampled within category), so the
calibration is a per-category monotone quantile map: the i-th ranked BT score is mapped to the
i-th ranked teacher mean difficulty of the same tasks. The ordering comes from the pairwise
judgments; the marginal matches the teachers' absolute ratings.
"""

import json
import random

import numpy as np

from . import paths, teachers
from .jsonio import append_jsonl, read_jsonl

BATCH = 40
OUT = paths.PAIRWISE / "judgments.jsonl"
OUT_DEEPSEEK = paths.PAIRWISE / "judgments_deepseek.jsonl"
_OUT = {"codex": OUT, "deepseek": OUT_DEEPSEEK}


def read_judgments() -> list[dict]:
    return read_jsonl(OUT) + read_jsonl(OUT_DEEPSEEK)
MAX_CHARS = 1200

PROMPT = """For each pair below, decide which task is HARDER for an AI assistant to complete correctly (needs a stronger model:
more scope, subtlety, ambiguity, required expertise). Judge substance, not text length. Answer "A", "B", or "tie" if truly equal.
Return ONLY JSON: {{"answers": [{{"id": "<pair id>", "harder": "A" | "B" | "tie"}}, ...]}}, one per pair. Do not use tools.

{pairs}
"""


def _clip(t: str) -> str:
    return t if len(t) <= MAX_CHARS else t[:MAX_CHARS - 200] + " [...] " + t[-150:]


def sample_pairs(items: list[dict], n_pairs: int, seed: int = 0) -> list[tuple[str, str]]:
    """items: {"id", "category", "diff_mean"}. Half random, half near-neighbour (|Δ teacher diff| <= 2)."""
    rng = random.Random(seed)
    by_cat: dict[str, list[dict]] = {}
    for it in items:
        by_cat.setdefault(it["category"], []).append(it)
    cats = [c for c, v in by_cat.items() if len(v) >= 6]
    weights = [len(by_cat[c]) for c in cats]
    pairs, seen = [], set()
    tries = 0
    while len(pairs) < n_pairs and tries < n_pairs * 20:
        tries += 1
        c = rng.choices(cats, weights)[0]
        pool = by_cat[c]
        a = rng.choice(pool)
        if rng.random() < 0.5:
            near = [x for x in pool if x["id"] != a["id"] and abs(x["diff_mean"] - a["diff_mean"]) <= 2]
            b = rng.choice(near) if near else rng.choice(pool)
        else:
            b = rng.choice(pool)
        key = tuple(sorted((a["id"], b["id"])))
        if a["id"] == b["id"] or key in seen:
            continue
        seen.add(key)
        pairs.append(key)
    return pairs


def _parser(pids):
    def parse(obj):
        items = obj.get("answers") if isinstance(obj, dict) else obj
        got = {}
        for it in items or []:
            pid, h = str(it.get("id", "")), str(it.get("harder", "")).strip().upper()
            if pid in pids and h in ("A", "B", "TIE"):
                got[pid] = h
        if len(got) < 0.7 * len(pids):
            raise ValueError(f"only {len(got)}/{len(pids)} answers")
        return got
    return parse


async def _batch(rows: list[tuple[str, str]], texts: dict[str, str], teacher: str = "codex") -> None:
    pids = [f"p{i:02d}" for i in range(len(rows))]
    blocks = [f"### pair {pid}\n[A]\n{_clip(texts[a])}\n[B]\n{_clip(texts[b])}\n" for pid, (a, b) in zip(pids, rows)]
    got = await teachers.call(teacher, PROMPT.format(pairs="\n".join(blocks)), _parser(pids), purpose="pairwise")
    out = []
    for pid, (a, b) in zip(pids, rows):
        if pid in got:
            h = got[pid]
            out.append({"a": a, "b": b, "harder": "tie" if h == "TIE" else (a if h == "A" else b)})
    append_jsonl(_OUT[teacher], out)
    print(f"[pairwise] +{len(out)}/{len(rows)}", flush=True)


async def judge(pairs: list[tuple[str, str]], texts: dict[str, str], seed: int = 0, teacher: str = "codex") -> None:
    """Ask `teacher` about each pair in BOTH presentation orders, in different (shuffled) batches."""
    paths.ensure()
    done = {(r["a"], r["b"]) for r in read_jsonl(_OUT[teacher])}
    ordered = [(a, b) for a, b in pairs] + [(b, a) for a, b in pairs]
    todo = [p for p in ordered if p not in done]
    random.Random(seed).shuffle(todo)
    print(f"[pairwise] {len(todo)} ordered judgments to run", flush=True)
    await teachers.gather_limited([_batch(todo[i:i + BATCH], texts, teacher) for i in range(0, len(todo), BATCH)])


def fit_bt(judgments: list[dict], iters: int = 500, prior: float = 0.1) -> dict[str, float]:
    """Bradley-Terry by gradient ascent on the log-likelihood with a small Gaussian prior (keeps
    disconnected components and perfect records finite). Ties count as half a win each."""
    ids = sorted({j["a"] for j in judgments} | {j["b"] for j in judgments})
    ix = {k: i for i, k in enumerate(ids)}
    w, l, y = [], [], []
    for j in judgments:
        a, b = ix[j["a"]], ix[j["b"]]
        if j["harder"] == "tie":
            w += [a, b]; l += [b, a]; y += [0.5, 0.5]
        else:
            h = ix[j["harder"]]
            w.append(h); l.append(b if h == a else a); y.append(1.0)
    w, l, y = np.array(w), np.array(l), np.array(y)
    s = np.zeros(len(ids))
    lr = 0.5
    for _ in range(iters):
        p = 1 / (1 + np.exp(-(s[w] - s[l])))
        g = np.zeros_like(s)
        np.add.at(g, w, y * (1 - p))
        np.add.at(g, l, -y * (1 - p))
        g -= prior * s
        cnt = np.bincount(np.concatenate([w, l]), minlength=len(s)) + 1
        s += lr * g / cnt
    return {k: float(s[ix[k]]) for k in ids}


def calibrate(scores: dict[str, float], teacher_mean: dict[str, float], category: dict[str, str]) -> dict[str, float]:
    """Per-category monotone quantile map of BT scores onto the teachers' difficulty marginal."""
    out = {}
    by_cat: dict[str, list[str]] = {}
    for k in scores:
        by_cat.setdefault(category[k], []).append(k)
    for ks in by_cat.values():
        ranked = sorted(ks, key=lambda k: scores[k])
        targets = sorted(teacher_mean[k] for k in ks)
        for k, t in zip(ranked, targets):
            out[k] = round(float(min(10, max(1, t))), 3)
    return out


def consistency(judgments: list[dict]) -> dict:
    """Order-swap self-consistency: fraction of pairs whose two orders agree."""
    first: dict[tuple, str] = {}
    agree = total = 0
    for j in judgments:
        key = tuple(sorted((j["a"], j["b"])))
        if key in first:
            total += 1
            agree += first[key] == j["harder"]
        else:
            first[key] = j["harder"]
    return {"pairs_both_orders": total, "order_consistency": round(agree / total, 4) if total else None,
            "ties": sum(j["harder"] == "tie" for j in judgments), "judgments": len(judgments)}


def dump_scores(path, scores, calibrated, teacher_mean):
    path.write_text(json.dumps({k: {"bt": round(scores[k], 4), "calibrated": calibrated[k],
                                    "teacher_mean": round(teacher_mean[k], 3)} for k in scores}, indent=0))
