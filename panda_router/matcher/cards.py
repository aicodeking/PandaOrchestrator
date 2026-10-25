"""Model-card loading, validation and per-pool compilation (cached by pool hash)."""

from __future__ import annotations

import hashlib
import json
from collections import OrderedDict
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import numpy as np

from ..taxonomy import SKILL_AXES

ROOT = Path(__file__).resolve().parents[2]
SCHEMA_DIR = ROOT / "schemas"
DEFAULT_CARDS_DIR = ROOT / "cards"

DEFAULT_A = 1.2
MISSING_AXIS_SE = 2.0
MISSING_ALL_THETA, MISSING_ALL_SE = 5.0, 2.5
DEFAULT_TTFT_MS, DEFAULT_TPS = 1500.0, 50.0


@lru_cache(maxsize=None)
def _validator(name: str):
    from jsonschema import Draft202012Validator
    from referencing import Registry, Resource

    schemas = {p.name: json.loads(p.read_text()) for p in SCHEMA_DIR.glob("*.schema.json")}
    registry = Registry().with_resources(
        (s["$id"], Resource.from_contents(s)) for s in schemas.values() if "$id" in s
    )
    return Draft202012Validator(schemas[name], registry=registry)


def schema_errors(obj: dict, schema: str) -> list[str]:
    """Return human-readable validation errors of `obj` against `schemas/<schema>.schema.json`."""
    v = _validator(f"{schema}.schema.json")
    return [f"{'/'.join(map(str, e.absolute_path)) or '<root>'}: {e.message}" for e in v.iter_errors(obj)]


def validate_card(card: dict) -> None:
    if errs := schema_errors(card, "model_card"):
        raise ValueError(f"invalid model card {card.get('id', '?')!r}: {errs[:3]}")


_DIR_CACHE: dict[str, tuple[tuple, dict[str, dict]]] = {}


def load_cards(cards_dir: str | Path | None = None) -> dict[str, dict]:
    """Load and validate every `*.json` card in `cards_dir`. Cached until a file changes."""
    d = Path(cards_dir or DEFAULT_CARDS_DIR)
    files = sorted(d.glob("*.json"))
    stamp = tuple((f.name, f.stat().st_mtime_ns) for f in files)
    key = str(d.resolve())
    if (hit := _DIR_CACHE.get(key)) and hit[0] == stamp:
        return hit[1]
    cards: dict[str, dict] = {}
    for f in files:
        card = json.loads(f.read_text())
        validate_card(card)
        if card["id"] in cards:
            raise ValueError(f"duplicate card id {card['id']!r} in {f}")
        cards[card["id"]] = card
    _DIR_CACHE[key] = (stamp, cards)
    return cards


def pool_hash(cards: list[dict]) -> str:
    blob = json.dumps(sorted(cards, key=lambda c: c["id"]), sort_keys=True, separators=(",", ":"))
    return hashlib.sha256(blob.encode()).hexdigest()[:16]


@dataclass(frozen=True)
class Pool:
    """Numeric view of a card pool. Row i corresponds to cards[i]."""

    cards: tuple[dict, ...]
    ids: tuple[str, ...]
    hash: str
    theta: np.ndarray  # (N, K) on the 0..10 skill scale
    se: np.ndarray  # (N, K)
    a: np.ndarray  # (N,)
    cost_in: np.ndarray  # USD per Mtok
    cost_out: np.ndarray
    context: np.ndarray
    ttft_ms: np.ndarray
    tps: np.ndarray
    tools: np.ndarray  # bool
    vision: np.ndarray
    json_mode: np.ndarray
    web: np.ndarray
    local: np.ndarray

    def index(self, model_id: str) -> int:
        return self.ids.index(model_id)


def _skills_row(card: dict) -> tuple[list[float], list[float]]:
    sk = card.get("skills") or {}
    known = [sk[a]["theta"] for a in SKILL_AXES if a in sk]
    if not known:
        return [MISSING_ALL_THETA] * len(SKILL_AXES), [MISSING_ALL_SE] * len(SKILL_AXES)
    known_se = max(sk[a]["se"] for a in SKILL_AXES if a in sk)
    fill_theta = float(np.mean(known)) - 0.5
    fill_se = max(MISSING_AXIS_SE, known_se + 1.0)
    th = [sk[a]["theta"] if a in sk else fill_theta for a in SKILL_AXES]
    se = [sk[a]["se"] if a in sk else fill_se for a in SKILL_AXES]
    return th, se


def compile_pool(cards: list[dict]) -> Pool:
    rows = [_skills_row(c) for c in cards]

    def col(fn, dtype=float):
        return np.array([fn(c) for c in cards], dtype=dtype)

    return Pool(
        cards=tuple(cards),
        ids=tuple(c["id"] for c in cards),
        hash=pool_hash(cards),
        theta=np.array([r[0] for r in rows], dtype=float).reshape(len(cards), len(SKILL_AXES)),
        se=np.array([r[1] for r in rows], dtype=float).reshape(len(cards), len(SKILL_AXES)),
        a=col(lambda c: c.get("discrimination", DEFAULT_A)),
        cost_in=col(lambda c: c["cost"]["input_per_mtok"]),
        cost_out=col(lambda c: c["cost"]["output_per_mtok"]),
        context=col(lambda c: c["limits"]["context_tokens"]),
        ttft_ms=col(lambda c: (c.get("latency") or {}).get("ttft_ms_p50", DEFAULT_TTFT_MS)),
        tps=col(lambda c: (c.get("latency") or {}).get("tokens_per_sec", DEFAULT_TPS)),
        tools=col(lambda c: bool((c.get("features") or {}).get("tools", False)), bool),
        vision=col(lambda c: "image" in (c.get("modalities") or {}).get("input", []), bool),
        json_mode=col(lambda c: bool((c.get("features") or {}).get("json_mode", False)), bool),
        web=col(lambda c: bool((c.get("features") or {}).get("web", False)), bool),
        local=col(lambda c: bool(c.get("local", False)), bool),
    )


class PoolCache:
    """LRU of compiled pools keyed by pool hash."""

    def __init__(self, maxsize: int = 64):
        self.maxsize = maxsize
        self._by_hash: OrderedDict[str, Pool] = OrderedDict()

    def get(self, cards: list[dict]) -> Pool:
        h = pool_hash(cards)
        if (pool := self._by_hash.get(h)) is not None:
            self._by_hash.move_to_end(h)
            return pool
        pool = compile_pool(cards)
        self._by_hash[h] = pool
        if len(self._by_hash) > self.maxsize:
            self._by_hash.popitem(last=False)
        return pool
