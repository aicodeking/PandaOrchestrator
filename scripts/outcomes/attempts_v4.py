"""v4 attempt-and-grade on subscription harnesses (no OpenRouter calls). Resumable; rows append to the same
data/outcomes/raw/attempts/{answers,grades}.jsonl as attempts.py.

  parity    re-grade the 100-answer gold validation sample with the dsh judge (compare to stored ds-think)
  judge     grade every answer that has no ds-think label with the dsh judge (judge='dsh')
  attempt   --model M: claude-haiku-5.5 | claude-sonnet-5.5 | claude-opus-5.5 | codex-gpt-6-luna on gold + train/val tasks
  status    counts

Usage: .venv/bin/python scripts/outcomes/attempts_v4.py STEP [--model M] [--workers 4] [--limit N]
"""

import argparse
import json
import os
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "outcomes"))

from attempts import RAW, _grade_jobs, grade_one, hash_order, ok_answer, read_jsonl, tasks  # noqa: E402

from panda_router.outcomes.cli_chat import CLAUDE_MODELS, CODEX_MODELS, claude_chat, codex_chat  # noqa: E402
from panda_router.outcomes.grade import ATTEMPT_SYSTEM  # noqa: E402

N_TRAINVAL, N_OPUS_TRAINVAL = 400, 150
STOP = threading.Event()  # set when a harness reports a quota/rate limit


def append(p: Path, row: dict):
    """One os.write per row on an O_APPEND fd: atomic across the concurrent harness processes sharing the files."""
    fd = os.open(p, os.O_WRONLY | os.O_APPEND | os.O_CREAT)
    try:
        os.write(fd, (json.dumps(row, ensure_ascii=False) + "\n").encode())
    finally:
        os.close(fd)


def labelled() -> set:
    return {(r["task_id"], r["model"]) for r in read_jsonl(RAW / "grades.jsonl")
            if r["judge"] == "ds-think" and r.get("pass") is not None}


def parity_sample() -> set:
    return {(r["task_id"], r["model"]) for r in read_jsonl(RAW / "grades.jsonl") if r["judge"] == "kimi" and r.get("pass") is not None}


def run(jobs: list, fn, workers: int, label: str):
    done, t0, lock = [0], time.time(), threading.Lock()

    def wrap(j):
        if STOP.is_set():
            return
        r = fn(j)
        with lock:
            done[0] += 1
            if r and r.get("quota"):
                STOP.set()
                print(f"{label}: QUOTA HIT, stopping", flush=True)
            if done[0] % 25 == 0:
                print(f"{label}: {done[0]}/{len(jobs)} {time.time() - t0:.0f}s", flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(wrap, jobs))
    print(f"{label}: finished {done[0]}/{len(jobs)} in {time.time() - t0:.0f}s", flush=True)


def grade_jobs(ids, args):
    jobs = _grade_jobs("dsh", ids)[:args.limit or None]

    def fn(job):
        row = grade_one(*job, "dsh")
        row["secs"] = None
        if row.get("pass") is not None or row.get("error"):
            append(RAW / "grades.jsonl", row)
        return row

    run(jobs, fn, args.workers, "judge-dsh")


def parity(args):
    grade_jobs(parity_sample(), args)


def judge(args):
    have = labelled()
    ids = {k for k in ((r["task_id"], r["model"]) for r in read_jsonl(RAW / "answers.jsonl") if ok_answer(r)) if k not in have}
    grade_jobs(ids, args)


def attempt_tasks(model: str) -> list:
    """Gold + a fixed hash-ordered train/val sample from the budget subset (opus gets the first 150 of the 400)."""
    t = tasks()
    tv = sorted((x for x in t if x["split"] != "gold"), key=lambda x: hash_order(x["id"]))
    n = N_OPUS_TRAINVAL if model == "claude-opus-5.5" else N_TRAINVAL
    return [x for x in t if x["split"] == "gold"] + tv[:n]


def attempt(args):
    model = args.model
    have = {(r["task_id"]) for r in read_jsonl(RAW / "answers.jsonl") if r["model"] == model and ok_answer(r)}
    jobs = [t for t in attempt_tasks(model) if t["id"] not in have][:args.limit or None]

    def fn(t):
        o = (claude_chat(model, ATTEMPT_SYSTEM, t["text"]) if model in CLAUDE_MODELS
             else codex_chat(model, ATTEMPT_SYSTEM, t["text"]))
        row = {"task_id": t["id"], "model": model, "slug": model, "answer": o["text"], "finish": o["finish"],
               "usage": o["usage"], "cost": 0.0, "list_cost": o.get("list_cost"), "provider": o["provider"],
               "error": o["error"], "secs": o["secs"], "ts": time.time()}
        if not o.get("quota"):
            append(RAW / "answers.jsonl", row)
        return o

    run(jobs, fn, args.workers, f"attempt-{model}")


def status(_):
    ans = Counter(r["model"] for r in read_jsonl(RAW / "answers.jsonl") if ok_answer(r))
    gr = Counter((r["judge"], r["pass"] is not None) for r in read_jsonl(RAW / "grades.jsonl"))
    print(dict(ans), dict(gr), "pending dsh:", len(_grade_jobs("dsh", {k for k in ((r["task_id"], r["model"]) for r in
          read_jsonl(RAW / "answers.jsonl") if ok_answer(r)) if k not in labelled()})))


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["parity", "judge", "attempt", "status"])
    ap.add_argument("--model", choices=[*CLAUDE_MODELS, *CODEX_MODELS])
    ap.add_argument("--workers", type=int, default=4)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    globals()[a.step](a)
