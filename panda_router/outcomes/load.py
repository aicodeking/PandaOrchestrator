"""Load per-instance outcomes from data/outcomes/raw into long binomial-count tables.

Rows: (system, source, instance_id, k, n). For swe-bench/experiments every split instance that is not
in a submission's `resolved` list counts as a failure (the leaderboard convention).
"""

from __future__ import annotations

import json
import re
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[2]
RAW = ROOT / "data" / "outcomes" / "raw"
EXP = RAW / "swebench-experiments" / "evaluation"
SPLITS = ("verified", "lite", "multimodal", "test", "multilingual")
LICENCES = {
    "swebench-experiments": "no licence file in github.com/swe-bench/experiments; per-instance resolved lists used "
                            "as outcome facts only (raw not redistributed)",
    "swebench-tasks": "MIT (SWE-bench repo / SWE-bench_Multilingual card); problem statements come from public "
                      "GitHub issues of the respective repositories",
    "rebench07": "other (ibragim-bad/swe_rebench_07_2026_trajectories: no relicensing; outcome facts only, "
                 "no task text used)",
}


def split_tasks(split: str) -> pd.DataFrame:
    p = RAW / "hf" / split / "data" / "test-00000-of-00001.parquet"
    df = pd.read_parquet(p, columns=["instance_id", "repo", "problem_statement"])
    return df.assign(split=split)


def _metadata(d: Path) -> dict:
    import yaml

    for name in ("metadata.yaml", "metadata.yml"):
        if (d / name).exists():
            try:
                return yaml.safe_load((d / name).read_text()) or {}
            except yaml.YAMLError:
                return {}
    return {}


def _resolved(d: Path) -> set[str] | None:
    pid = d / "per_instance_details.json"
    if pid.exists():
        return {k for k, v in json.loads(pid.read_text()).items() if v.get("resolved")}
    res = d / "results" / "results.json"
    if res.exists():
        r = json.loads(res.read_text()).get("resolved", [])
        return set(r) if isinstance(r, list) else None  # some early multimodal entries only give a count
    return None


def load_swebench() -> tuple[pd.DataFrame, pd.DataFrame]:
    """Returns (outcomes[system, source, instance_id, k, n], systems[system, source, base_model_raw, agent, ...])."""
    rows, systems = [], []
    for split in SPLITS:
        universe = split_tasks(split).instance_id.tolist()
        for d in sorted(p for p in (EXP / split).iterdir() if p.is_dir()):
            res = _resolved(d)
            if res is None:
                continue
            res &= set(universe)
            meta = _metadata(d)
            tags, info = meta.get("tags") or {}, meta.get("info") or {}
            models = tags.get("model") or []
            sysname = f"{split}/{d.name}"
            systems.append({"system": sysname, "source": f"swebench-{split}", "dir": d.name,
                            "base_model_raw": "|".join(map(str, models)) if isinstance(models, list) else str(models),
                            "agent": tags.get("agent") or info.get("name"), "os_model": tags.get("os_model"),
                            "attempts": ((tags.get("system") or {}).get("attempts")), "n_resolved": len(res)})
            rows.extend((sysname, f"swebench-{split}", x, int(x in res), 1) for x in universe)
    return (pd.DataFrame(rows, columns=["system", "source", "instance_id", "k", "n"]), pd.DataFrame(systems))


def load_rebench07() -> tuple[pd.DataFrame, pd.DataFrame]:
    p = RAW / "rebench07_outcomes.jsonl"
    df = pd.read_json(p, lines=True)
    df = df[df.status.isin(["resolved", "failed"])]  # drop the 1 'skipped'
    df["system"] = "rebench07/" + df.participant
    out = df.groupby(["system", "instance_id"]).resolved.agg(k="sum", n="count").reset_index()
    out["source"] = "rebench07"
    sys = (df.groupby("system").agg(participant=("participant", "first"), type=("type", "first"),
                                    scaffold=("scaffold", "first"), base_model_raw=("model", "first"),
                                    reasoning_effort=("reasoning_effort", "first"), n_resolved=("resolved", "sum"))
           .reset_index().assign(source="rebench07"))
    return out[["system", "source", "instance_id", "k", "n"]], sys


def norm_text(t: str) -> str:
    """Normalised text for duplicate checks: lowercase, alnum tokens only, single spaces."""
    return " ".join(re.findall(r"[a-z0-9]+", (t or "").lower()))
