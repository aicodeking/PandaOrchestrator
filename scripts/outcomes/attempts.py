"""Attempt-and-grade ladder for non-SWE tasks (resumable; every call is cached under data/outcomes/raw/attempts/).

Steps (run in order; each skips work already cached):
  select    sample ~1,500 train/val tasks (stratified by top category x teacher difficulty band, SWE sources and
            gold excluded) + 150 non-SWE gold tasks (eval only) -> tasks.json
  subset    budget cut: keep 1,000 of the 1,500 train/val tasks, same strata proportions (grows only) -> subset.json
  attempt   every attempter answers every task once (single turn, no tools) -> answers.jsonl
  rubric    the judge writes one blind checklist per task, shared by all answers -> rubrics.jsonl
  judge     --judge (labels: ds-think) grades each answer against the checklist; a stdlib Python block must also run -> grades.jsonl
  validate  100 random gold answers re-graded with --judge (ds-think, ds-strict, strong, kimi) for agreement -> grades.jsonl

Spend guard: stops issuing calls once logged spend reaches --budget (default $57; hard cap $60).
Usage: .venv/bin/python scripts/outcomes/attempts.py STEP [--limit N] [--budget USD] [--workers N]
"""

import argparse
import json
import random
import sys
import threading
import time
from collections import Counter
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from panda_router.outcomes.grade import (ATTEMPT_SYSTEM, JUDGE_PROMPT, RUBRIC_PROMPT, STRICT_JUDGE_PROMPT,  # noqa: E402
                                         chat, code_check, format_criteria, parse_json, strict_verdict)

RAW = ROOT / "data" / "outcomes" / "raw" / "attempts"
ATTEMPTERS = {  # card id -> OpenRouter slug, weakest to strongest by current card
    "openrouter-deepseek-v4.1-flash": "deepseek/deepseek-v4.1-flash",
    "openrouter-qwen3.8-flash": "qwen/qwen3.8-flash",
    "openrouter-minimax-m3.1-flash": "minimax/minimax-m3.1-flash",
    "openrouter-gemini-3.8-flash": "google/gemini-3.8-flash",
    "openrouter-gpt-6.1-sol": "openai/gpt-6.1-sol",  # pilot: $0.012/task vs kimi-k3.1-pro $0.031/task
}
REASONING = {"max_tokens": 1500, "exclude": True}  # same thinking budget for every model (qwen ignores effort=low)
LOW = {"effort": "low", "exclude": True}
# judge name -> (slug, reasoning). DeepSeek ignores a reasoning token cap, so the judge runs either without thinking
# or at effort=low with a large max_tokens. The rubric is written without thinking (it is shared by all answers).
JUDGES = {"ds": ("deepseek/deepseek-v4.1-flash", {"enabled": False}),
          "ds-think": ("deepseek/deepseek-v4.1-flash", LOW),
          "ds-strict": ("deepseek/deepseek-v4.1-flash", {"enabled": False}),  # STRICT_JUDGE_PROMPT, verdict in code
          "strong": ("openai/gpt-6.1-sol", LOW),
          "kimi": ("moonshotai/kimi-k3.1-pro", LOW)}  # non-attempter cross-check of the strong judge (self-preference)
RUBRIC_JUDGE = "ds"
ATTEMPT_MAX_TOKENS, JUDGE_MAX_TOKENS = 5000, 8000
N_TRAINVAL, N_GOLD, N_VALIDATE, N_SUBSET = 1500, 150, 100, 1000
SWE = ("swe-rebench", "swe-smith")
BANDS = ((1, 3.5), (3.5, 5.5), (5.5, 7.5), (7.5, 11))
LOCK = threading.Lock()


def read_jsonl(p: Path) -> list[dict]:
    return [json.loads(x) for x in p.read_text().splitlines() if x.strip()] if p.exists() else []


def append(p: Path, row: dict):
    with LOCK, p.open("a") as f:
        f.write(json.dumps(row, ensure_ascii=False) + "\n")


def spent() -> float:
    return sum(r.get("cost", 0.0) for f in ("answers", "rubrics", "grades") for r in read_jsonl(RAW / f"{f}.jsonl"))


def ok_answer(r: dict) -> bool:
    """A usable attempt: the call succeeded and the provider did not abort the stream (finish_reason 'error')."""
    return not r["error"] and r["finish"] != "error"


def top_cat(r: dict) -> str:
    return max(r["labels"]["category"].items(), key=lambda kv: kv[1])[0]


def teacher_diff(r: dict) -> float:
    return sum((i + 1) * p for i, p in enumerate(r["labels"]["difficulty"]))


def select(_args):
    rows = []
    for split in ("train", "val"):
        rows += [{**json.loads(x), "_split": split} for x in (ROOT / "data" / f"{split}.jsonl").read_text().splitlines()]
    gold = [json.loads(x) for x in (ROOT / "data" / "gold" / "gold.jsonl").read_text().splitlines()]
    gold_ids = {g["id"] for g in gold}
    gold_text = {g["task"]["text"].strip().lower() for g in gold}
    cand = [r for r in rows if r["source"] not in SWE and r["id"] not in gold_ids
            and r["task"]["text"].strip().lower() not in gold_text]
    strata: dict = {}
    for r in cand:
        band = next(j for j, (lo, hi) in enumerate(BANDS) if lo <= teacher_diff(r) < hi)
        strata.setdefault((top_cat(r), band), []).append(r)
    rng = random.Random(0)
    w = {k: len(v) ** 0.5 for k, v in strata.items()}  # sqrt allocation: small categories/bands get more weight
    quota = {k: min(len(strata[k]), round(N_TRAINVAL * w[k] / sum(w.values()))) for k in strata}
    while sum(quota.values()) < N_TRAINVAL:  # top up from strata with spare rows, largest first
        k = max((k for k in strata if quota[k] < len(strata[k])), key=lambda k: len(strata[k]) - quota[k])
        quota[k] += 1
    picked = []
    for k, v in sorted(strata.items()):
        v = sorted(v, key=lambda r: r["id"])
        rng.shuffle(v)
        v.sort(key=lambda r: bool(r["task"]["context"].get("requires_tools")))  # self-contained first (stable)
        picked += v[:quota[k]]
    g = sorted([x for x in gold if x["source"] not in SWE], key=lambda r: r["id"])
    gpick = rng.sample(g, min(N_GOLD, len(g)))

    def slim(r, split):
        return {"id": r["id"], "split": split, "source": r["source"], "text": r["task"]["text"],
                "context": r["task"]["context"], "category": top_cat(r), "teacher_difficulty": round(teacher_diff(r), 3),
                "hard_group": (r.get("meta") or {}).get("hard_group")}

    out = [slim(r, r["_split"]) for r in picked] + [slim(r, "gold") for r in gpick]
    RAW.mkdir(parents=True, exist_ok=True)
    (RAW / "tasks.json").write_text(json.dumps(out, ensure_ascii=False))
    print(len(picked), "train/val,", len(gpick), "gold;", Counter(t["category"] for t in out[:len(picked)]))


def all_tasks() -> list[dict]:
    return json.loads((RAW / "tasks.json").read_text())


def tasks() -> list[dict]:
    """Active tasks: gold + the budget subset of train/val (subset.json) when it exists, in a fixed random order."""
    t = all_tasks()
    if (RAW / "subset.json").exists():
        keep = set(json.loads((RAW / "subset.json").read_text()))
        t = [x for x in t if x["split"] == "gold" or x["id"] in keep]
    return sorted(t, key=lambda x: (x["split"] != "gold", hash_order(x["id"])))


def hash_order(s: str) -> str:
    import hashlib
    return hashlib.sha1(s.encode()).hexdigest()


def subset(args):
    """Budget cut (see REPORT_attempts.md): keep N_SUBSET train/val tasks, proportional to the (category, band) strata
    of the 1,500 selection; within a stratum prefer tasks already attempted by every model (no new attempt cost)."""
    sel = [t for t in all_tasks() if t["split"] != "gold"]
    done: dict = {}
    for r in read_jsonl(RAW / "answers.jsonl"):
        if ok_answer(r):
            done.setdefault(r["task_id"], set()).add(r["model"])
    strata: dict = {}
    for t in sel:
        band = next(j for j, (lo, hi) in enumerate(BANDS) if lo <= t["teacher_difficulty"] < hi)
        strata.setdefault((t["category"], band), []).append(t)
    n = args.limit or N_SUBSET
    prev = set(json.loads((RAW / "subset.json").read_text())) if (RAW / "subset.json").exists() else set()  # grow only
    keep = []
    for k, v in sorted(strata.items()):
        v = sorted(v, key=lambda t: (t["id"] not in prev, len(done.get(t["id"], ())) < len(ATTEMPTERS),
                                     hash_order(t["id"])))
        keep += [t["id"] for t in v[:max(1, round(n * len(v) / len(sel)))]]
    (RAW / "subset.json").write_text(json.dumps(sorted(keep)))
    print(len(keep), "train/val tasks;", sum(len(done.get(i, ())) == len(ATTEMPTERS) for i in keep), "already attempted")


def GOLD_IDS() -> set:  # noqa: N802
    return {t["id"] for t in tasks() if t["split"] == "gold"}


def run_pool(jobs: list, fn, workers: int, budget: float, label: str):
    """Run fn(job) -> row with a thread pool; stop submitting when spend reaches budget. Prints progress."""
    base = spent()
    done, cost, t0, stop = 0, 0.0, time.time(), threading.Event()
    print(f"{label}: {len(jobs)} jobs, spent so far ${base:.2f}", flush=True)
    with ThreadPoolExecutor(workers) as ex:
        it = iter(jobs)
        futs = {ex.submit(fn, j) for j in [next(it) for _ in range(min(workers * 2, len(jobs)))]}
        while futs:
            f = next(as_completed(futs))
            futs.remove(f)
            row = f.result()
            done, cost = done + 1, cost + row.get("cost", 0.0)
            if base + cost >= budget:
                stop.set()
            if done % 100 == 0 or not futs:
                print(f"{label}: {done}/{len(jobs)} ${base + cost:.2f} {time.time() - t0:.0f}s", flush=True)
            nxt = None if stop.is_set() else next(it, None)
            if nxt is not None:
                futs.add(ex.submit(fn, nxt))
    if stop.is_set():
        print(f"{label}: STOPPED at budget ${budget:.2f}", flush=True)


def attempt(args):
    have = {(r["task_id"], r["model"]) for r in read_jsonl(RAW / "answers.jsonl") if ok_answer(r)}
    jobs = [(t, cid) for t in tasks() for cid in ATTEMPTERS if (t["id"], cid) not in have]
    jobs = jobs[:args.limit] if args.limit else jobs

    def fn(job):
        t, cid = job
        o = chat(ATTEMPTERS[cid], [{"role": "system", "content": ATTEMPT_SYSTEM}, {"role": "user", "content": t["text"]}],
                 ATTEMPT_MAX_TOKENS, REASONING)
        row = {"task_id": t["id"], "model": cid, "slug": ATTEMPTERS[cid], "answer": o["text"], "finish": o["finish"],
               "usage": o["usage"], "cost": o["cost"], "provider": o["provider"], "error": o["error"], "ts": time.time()}
        append(RAW / "answers.jsonl", row)
        return row

    run_pool(jobs, fn, args.workers, args.budget, "attempt")


def rubric(args):
    have = {r["task_id"] for r in read_jsonl(RAW / "rubrics.jsonl") if r.get("criteria")}
    jobs = [t for t in tasks() if t["id"] not in have]
    jobs = jobs[:args.limit] if args.limit else jobs

    def fn(t):
        o = chat(JUDGES[RUBRIC_JUDGE][0], [{"role": "user", "content": RUBRIC_PROMPT.format(task=t["text"])}],
                 JUDGE_MAX_TOKENS, JUDGES[RUBRIC_JUDGE][1])
        crit = (parse_json(o["text"]) or {}).get("criteria") or []
        crit = [c for c in crit if isinstance(c, dict) and "id" in c and "text" in c]
        row = {"task_id": t["id"], "criteria": crit, "cost": o["cost"], "usage": o["usage"], "error": o["error"]}
        append(RAW / "rubrics.jsonl", row)
        return row

    run_pool(jobs, fn, args.workers, args.budget, "rubric")


def grade_one(t: dict, crit: list, ans: dict, judge: str) -> dict:
    text = ans["answer"]
    base = {"task_id": t["id"], "model": ans["model"], "judge": judge}
    if not text.strip():  # empty or reasoning-only reply: fail without a judge call
        return {**base, "pass": False, "reason": f"empty answer (finish={ans['finish']})", "cost": 0.0, "verify": None}
    if ans["finish"] == "length":
        text += "\n\n[ANSWER TRUNCATED AT THE TOKEN LIMIT]"
    slug, reasoning = JUDGES[judge]
    prompt = STRICT_JUDGE_PROMPT if judge.endswith("strict") else JUDGE_PROMPT
    o = chat(slug, [{"role": "user", "content": prompt.format(task=t["text"], criteria=format_criteria(crit),
                                                              answer=text)}], JUDGE_MAX_TOKENS, reasoning)
    j = parse_json(o["text"]) or {}
    verdict = strict_verdict(j, crit) if judge.endswith("strict") else j.get("pass")
    verify = code_check(ans["answer"]) if t["category"] not in ("chat_simple", "docs_writing") else None
    ok = bool(verdict) and (verify is None or verify["ran"])
    return {**base, "pass": ok if isinstance(verdict, bool) else None, "judge_pass": verdict, "met": j.get("met") or [r.get("id") for r in j.get("criteria") or []
                                                                         if isinstance(r, dict) and r.get("met")],
            "errors": j.get("errors") or j.get("material_errors"), "verify": verify, "cost": o["cost"], "usage": o["usage"], "error": o["error"]}


def _grade_jobs(judge: str, ids: set | None = None) -> list:
    tmap = {t["id"]: t for t in tasks()}
    rub = {r["task_id"]: r["criteria"] for r in read_jsonl(RAW / "rubrics.jsonl") if r.get("criteria")}
    rows = [r for r in read_jsonl(RAW / "grades.jsonl") if r["judge"] == judge]
    tries = Counter((r["task_id"], r["model"]) for r in rows if r.get("pass") is None and not r.get("error"))
    # graded, or unparseable twice (DeepSeek sometimes spends the whole budget reasoning): leave the cell missing
    have = {(r["task_id"], r["model"]) for r in rows if r.get("pass") is not None} | {k for k, v in tries.items() if v >= 2}
    ans = {(r["task_id"], r["model"]): r for r in read_jsonl(RAW / "answers.jsonl") if ok_answer(r)}
    order = {t["id"]: j for j, t in enumerate(tasks())}  # gold first, then fixed random order
    keys = sorted((k for k in ans if k[0] in rub and k[0] in order and k not in have and (ids is None or k in ids)),
                  key=lambda k: (order[k[0]], k[1]))
    return [(tmap[k[0]], rub[k[0]], ans[k]) for k in keys]


def judge(args):
    jobs = _grade_jobs(args.judge)
    jobs = jobs[:args.limit] if args.limit else jobs

    def fn(job):
        row = grade_one(*job, args.judge)
        append(RAW / "grades.jsonl", row)
        return row

    run_pool(jobs, fn, args.workers, args.budget, "judge")


def validate(args):
    """Re-grade a fixed random sample of 100 gold answers (non-empty, judged by 'ds') with --judge.
    --model M: instead, 60 random train/val answers by M judged by ds-think (self-preference check of the judge)."""
    rows = read_jsonl(RAW / "grades.jsonl")
    if args.model:
        graded = sorted((r["task_id"], r["model"]) for r in rows if r["judge"] == "ds-think" and r["model"] == args.model
                        and r.get("judge_pass") is not None and r["task_id"] not in GOLD_IDS())
        ids = set(random.Random(2).sample(graded, min(60, len(graded))))
    else:
        graded = sorted((r["task_id"], r["model"]) for r in rows
                        if r["judge"] == "ds" and r.get("judge_pass") is not None and r["task_id"] in GOLD_IDS())
        ids = set(random.Random(1).sample(graded, min(N_VALIDATE, len(graded))))
    jobs = _grade_jobs(args.judge, ids)

    def fn(job):
        row = grade_one(*job, args.judge)
        append(RAW / "grades.jsonl", row)
        return row

    run_pool(jobs, fn, args.workers, args.budget, "validate")


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["select", "subset", "attempt", "rubric", "judge", "validate", "spent"])
    ap.add_argument("--limit", type=int, default=0)
    ap.add_argument("--budget", type=float, default=57.0)
    ap.add_argument("--workers", type=int, default=16)
    ap.add_argument("--judge", choices=list(JUDGES), default="ds")
    ap.add_argument("--model", choices=list(ATTEMPTERS), default=None)
    args = ap.parse_args()
    args.budget = min(args.budget, 60.0)
    if args.step == "spent":
        print(f"${spent():.2f}")
        return
    globals()[args.step](args)


if __name__ == "__main__":
    main()
