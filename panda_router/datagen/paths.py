from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent.parent
DATA = ROOT / "data"
RAW = DATA / "raw"
CACHE = DATA / "cache"
CALLS = CACHE / "calls"
POOL = CACHE / "pool"  # unlabelled task pools (*.jsonl)
LABELS = CACHE / "labels"  # per-teacher answers (<teacher>.jsonl)
PAIRWISE = CACHE / "pairwise"
CALL_LOG = CACHE / "call_log.jsonl"


def ensure() -> None:
    for p in (RAW, CACHE, CALLS, POOL, LABELS, PAIRWISE):
        p.mkdir(parents=True, exist_ok=True)
