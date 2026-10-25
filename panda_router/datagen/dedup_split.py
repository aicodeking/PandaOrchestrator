"""Stage 6: embedding near-duplicate removal (SemDeDup-style) and cluster-level train/val/test split.

Embeddings: jhu-clsp/ettin-encoder-32m, mean-pooled over format_input(task), then mean-centred and
re-normalised (see `center`). Originals with cosine
> DUP_THRESHOLD to an already-kept original are dropped (real sources are kept first). Minimal pairs
are never compared to their own original and are dropped if the original is dropped. Splits are
assigned per cluster (KMeans on originals; SWE repos form their own cluster), and minimal pairs
inherit their original's split.
"""

import random

import numpy as np

from ..text import format_input

MODEL = "jhu-clsp/ettin-encoder-32m"
DUP_THRESHOLD = 0.95
SPLIT_FRACS = {"train": 0.85, "val": 0.075, "test": 0.075}
SOURCE_PRIORITY = {"swe-rebench": 0, "swe-smith": 1, "wildchat": 2, "synthetic": 3}


def embed(texts: list[str], batch: int = 64, max_len: int = 256) -> np.ndarray:
    import torch
    from transformers import AutoModel, AutoTokenizer

    dev = "mps" if torch.backends.mps.is_available() else "cpu"
    tok = AutoTokenizer.from_pretrained(MODEL)
    model = AutoModel.from_pretrained(MODEL).to(dev).eval()
    out = []
    with torch.no_grad():
        for i in range(0, len(texts), batch):
            enc = tok(texts[i:i + batch], padding="max_length", truncation=True, max_length=max_len, return_tensors="pt").to(dev)
            h = model(**enc).last_hidden_state
            m = enc["attention_mask"].unsqueeze(-1).to(h.dtype)
            v = (h * m).sum(1) / m.sum(1).clamp(min=1)
            out.append(torch.nn.functional.normalize(v, dim=-1).float().cpu().numpy())
    return np.concatenate(out) if out else np.zeros((0, 1))


def center(emb: np.ndarray) -> np.ndarray:
    """Remove the common direction and renormalise. Raw mean-pooled Ettin vectors are highly
    anisotropic (random pairs ~0.97 cosine), which would make any 0.95 threshold meaningless."""
    e = emb - emb.mean(0, keepdims=True)
    return e / np.clip(np.linalg.norm(e, axis=1, keepdims=True), 1e-8, None)


def dedup(records: list[dict], emb: np.ndarray, threshold: float = DUP_THRESHOLD) -> tuple[list[int], list[tuple[int, int]]]:
    """Greedy keep-first dedup over originals. Returns kept indices and (dropped, kept_neighbour) pairs."""
    order = sorted(range(len(records)), key=lambda i: (SOURCE_PRIORITY.get(records[i]["source"], 9), records[i]["id"]))
    kept, dropped = [], []
    kept_mat = np.empty_like(emb)
    for i in order:
        if kept:
            sims = kept_mat[:len(kept)] @ emb[i]
            j = int(np.argmax(sims))
            if sims[j] > threshold:
                dropped.append((i, kept[j]))
                continue
        kept_mat[len(kept)] = emb[i]
        kept.append(i)
    return sorted(kept), dropped


def assign_splits(cluster_of: dict[str, str], seed: int = 0, fracs=SPLIT_FRACS) -> dict[str, str]:
    """Greedy: shuffle clusters, fill val then test up to their quotas, rest train."""
    sizes: dict[str, int] = {}
    for c in cluster_of.values():
        sizes[c] = sizes.get(c, 0) + 1
    total = sum(sizes.values())
    clusters = sorted(sizes)
    random.Random(seed).shuffle(clusters)
    quota = {"val": fracs["val"] * total, "test": fracs["test"] * total}
    filled = {"val": 0, "test": 0}
    split_of_cluster = {}
    for c in clusters:
        target = "train"
        for s in ("val", "test"):
            if filled[s] + sizes[c] <= quota[s] * 1.02 and filled[s] < quota[s]:
                target = s
                break
        if target != "train":
            filled[target] += sizes[c]
        split_of_cluster[c] = target
    return {k: split_of_cluster[c] for k, c in cluster_of.items()}


def cluster(records: list[dict], emb: np.ndarray, avg_size: int = 15, seed: int = 0) -> dict[str, str]:
    from sklearn.cluster import KMeans

    out, rest = {}, []
    for i, r in enumerate(records):
        repo = (r.get("meta") or {}).get("repo")
        if repo:
            out[r["id"]] = f"repo:{repo.split('.')[0]}"
        else:
            rest.append(i)
    if rest:
        k = max(2, len(rest) // avg_size)
        lab = KMeans(n_clusters=k, n_init=2, random_state=seed).fit_predict(emb[rest])
        for i, c in zip(rest, lab):
            out[records[i]["id"]] = f"km:{c}"
    return out


def run(originals: list[dict], pairs: list[dict], seed: int = 0) -> tuple[dict[str, list[dict]], dict]:
    """Returns ({split: records}, report)."""
    emb = center(embed([format_input(r["task"]) for r in originals]))
    kept, dropped = dedup(originals, emb)
    kept_recs = [originals[i] for i in kept]
    clusters = cluster(kept_recs, emb[kept], seed=seed)
    split = assign_splits(clusters, seed=seed)
    out = {"train": [], "val": [], "test": []}
    for r in kept_recs:
        out[split[r["id"]]].append(r)
    dropped_pairs = 0
    for p in pairs:
        s = split.get(p["pair_of"])
        if s is None:
            dropped_pairs += 1
        else:
            out[s].append(p)
    report = {
        "originals_in": len(originals), "near_dup_dropped": len(dropped), "minimal_pairs_dropped_with_original": dropped_pairs,
        "clusters": len(set(clusters.values())), "dup_threshold": DUP_THRESHOLD,
        "dup_examples": [(originals[a]["id"], originals[b]["id"]) for a, b in dropped[:10]],
    }
    return out, report
