import asyncio
import hashlib

from ..taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES


def sha_int(s: str) -> int:
    return int(hashlib.sha1(s.encode()).hexdigest(), 16)


def is_gold_reserved(raw_id: str) -> bool:
    """GOLD EXCLUSION RULE: these records belong to the gold set and never enter training."""
    return sha_int(raw_id) % 10 == 0


def short_hash(s: str, n: int = 10) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:n]


def norm_context(ctx) -> dict:
    """Coerce a teacher/heuristic context into the CONTRACTS.md task-context shape."""
    ctx = ctx if isinstance(ctx, dict) else {}
    out = {}
    langs = ctx.get("repo_languages")
    if isinstance(langs, str):
        langs = [langs]
    if isinstance(langs, list):
        out["repo_languages"] = [str(x).lower()[:30] for x in langs if x][:6]
    for k in ("files_in_scope", "estimated_input_tokens"):
        v = ctx.get(k)
        try:
            if v is not None:
                out[k] = max(0, int(float(v)))
        except (TypeError, ValueError):
            pass
    for k in ("has_images", "requires_tools"):
        if k in ctx:
            out[k] = bool(ctx[k]) and str(ctx[k]).lower() not in ("false", "0", "no")
    return out


def run(coro):
    return asyncio.run(coro)


__all__ = ["CATEGORIES", "CHECKLIST_IDS", "FLAGS", "SKILL_AXES", "sha_int", "is_gold_reserved",
           "short_hash", "norm_context", "run"]
