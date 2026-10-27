"""Batched judge via Codex CLI (gpt-5.6-terra; not an attempter). judge name in grades.jsonl: 'codex-terra'.

  parity   grade the 100 gold cells that have both ds-think and kimi labels -> kappa vs each (printed)
  judge    grade every answer with no valid ds-think / dsh / codex-terra grade
Each prompt holds up to --batch (task, criteria, answer) items; the reply is a JSON array of {id, pass, reason}.
A reply that does not cover exactly the batch ids is retried singly for the missing items.
Usage: .venv/bin/python scripts/outcomes/judge_terra.py STEP [--workers 6] [--batch 10] [--limit N]
"""

import argparse
import json
import re
import sys
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "outcomes"))

from attempts import RAW, ok_answer, read_jsonl, tasks  # noqa: E402
from attempts_v4 import append  # noqa: E402

from panda_router.outcomes.cli_chat import codex_chat  # noqa: E402
from panda_router.outcomes.grade import cohen_kappa, code_check, format_criteria  # noqa: E402

JUDGE = "codex-terra"
VALID = ("ds-think", "dsh", JUDGE)
MAX_ANS, MAX_TASK = 14000, 6000
SYSTEM = ("You are a strict grader. You grade independent items; each has a TASK, CRITERIA and an ANSWER written by an "
          "unknown assistant that had no tools or file access. Do not use tools. Reply with JSON only.")
RULES = """For each item decide whether the ANSWER satisfies the TASK.
PASS only if every [critical] criterion is met, no more than one non-critical criterion is missed, and the answer contains \
no material factual, mathematical or code error. A truncated, evasive, generic or mostly-placeholder answer FAILS. Check \
math and code yourself. Judge each item on its own merits; do not compare items.

Reply with a JSON array only, one element per item: [{"id": <item id>, "pass": true|false, "reason": "<=20 words"}, ...]"""
STOP = threading.Event()


def build(items: list) -> str:
    parts = [RULES, ""]
    for i, (t, crit, ans) in enumerate(items):
        text = ans["answer"][:MAX_ANS]
        if ans["finish"] == "length" or len(ans["answer"]) > MAX_ANS:
            text += "\n\n[ANSWER TRUNCATED]"
        parts.append(f"=== ITEM {i} ===\nTASK:\n<<<\n{t['text'][:MAX_TASK]}\n>>>\nCRITERIA:\n{format_criteria(crit)}\n"
                     f"ANSWER:\n<<<\n{text}\n>>>\n")
    return "\n".join(parts)


def parse(text: str, n: int) -> dict:
    m = re.search(r"\[.*\]", text or "", re.S)
    try:
        rows = json.loads(m.group(0)) if m else []
    except json.JSONDecodeError:
        return {}
    return {r["id"]: r for r in rows if isinstance(r, dict) and r.get("id") in range(n) and isinstance(r.get("pass"), bool)}


def grade_batch(items: list) -> list:
    """-> list of grade rows (only for items that got a valid verdict)."""
    out, got = [], {}
    o = codex_chat("codex-terra", SYSTEM, build(items))
    if o.get("quota"):
        STOP.set()
    if not o["error"]:
        got = parse(o["text"], len(items))
    for i, (t, crit, ans) in enumerate(items):
        if i not in got and len(items) > 1 and not STOP.is_set():  # retry the missing ones singly
            r = grade_batch([(t, crit, ans)])
            out += r
            continue
        if i in got:
            v = got[i]["pass"]
            verify = code_check(ans["answer"]) if t["category"] not in ("chat_simple", "docs_writing") else None
            out.append({"task_id": t["id"], "model": ans["model"], "judge": JUDGE, "pass": v and (verify is None or verify["ran"]),
                        "judge_pass": v, "reason": got[i].get("reason"), "verify": verify, "cost": 0.0, "error": "",
                        "batch": len(items), "ts": time.time()})
    return out


def todo(parity_only: bool = False) -> list:
    tmap = {t["id"]: t for t in tasks()}
    rub = {r["task_id"]: r["criteria"] for r in read_jsonl(RAW / "rubrics.jsonl") if r.get("criteria")}
    grades = read_jsonl(RAW / "grades.jsonl")
    have = {(r["task_id"], r["model"]) for r in grades if r["judge"] in VALID and r.get("pass") is not None}
    done = {(r["task_id"], r["model"]) for r in grades if r["judge"] == JUDGE and r.get("pass") is not None}
    ans = {(r["task_id"], r["model"]): r for r in read_jsonl(RAW / "answers.jsonl") if ok_answer(r)}
    if parity_only:
        by = {}
        for r in grades:
            if r.get("pass") is not None:
                by.setdefault((r["task_id"], r["model"]), set()).add(r["judge"])
        want = {k for k, v in by.items() if {"ds-think", "kimi"} <= v and k in ans} - done
    else:
        want = {k for k in ans if k not in have}
    order = {t["id"]: j for j, t in enumerate(tasks())}
    keys = sorted((k for k in want if k[0] in tmap and k[0] in rub), key=lambda k: (order[k[0]], k[1]))
    jobs = []
    for k in keys:
        a = ans[k]
        if not a["answer"].strip():  # empty reply fails without a judge call (as grade_one)
            append(RAW / "grades.jsonl", {"task_id": k[0], "model": k[1], "judge": JUDGE, "pass": False,
                                          "reason": "empty answer", "cost": 0.0, "verify": None, "error": ""})
            continue
        jobs.append((tmap[k[0]], rub[k[0]], a))
    return jobs


def run(jobs: list, batch: int, workers: int, label: str):
    batches = [jobs[i:i + batch] for i in range(0, len(jobs), batch)]
    t0, n, lock = time.time(), [0], threading.Lock()
    print(f"{label}: {len(jobs)} items in {len(batches)} batches", flush=True)

    def fn(b):
        if STOP.is_set():
            return
        rows = grade_batch(b)
        for r in rows:
            append(RAW / "grades.jsonl", r)
        with lock:
            n[0] += len(rows)
            print(f"{label}: {n[0]}/{len(jobs)} graded {time.time() - t0:.0f}s", flush=True)

    with ThreadPoolExecutor(workers) as ex:
        list(ex.map(fn, batches))
    if STOP.is_set():
        print(f"{label}: QUOTA HIT, stopped", flush=True)


def parity_report():
    by = {}
    for r in read_jsonl(RAW / "grades.jsonl"):
        if r.get("pass") is not None:
            by.setdefault((r["task_id"], r["model"]), {})[r["judge"]] = r["pass"]
    ks = [k for k, v in by.items() if {JUDGE, "ds-think", "kimi"} <= v.keys()]
    g = lambda j: [by[k][j] for k in ks]  # noqa: E731
    res = {"n": len(ks)}
    for y in ("ds-think", "kimi"):
        res[f"kappa_vs_{y}"] = round(cohen_kappa(g(JUDGE), g(y)), 3)
        res[f"agree_vs_{y}"] = round(sum(a == b for a, b in zip(g(JUDGE), g(y))) / max(1, len(ks)), 3)
    res["pass_rate"] = {j: round(sum(g(j)) / max(1, len(ks)), 3) for j in (JUDGE, "ds-think", "kimi")}
    print(json.dumps(res))
    return res


if __name__ == "__main__":
    ap = argparse.ArgumentParser()
    ap.add_argument("step", choices=["parity", "judge", "report"])
    ap.add_argument("--workers", type=int, default=6)
    ap.add_argument("--batch", type=int, default=10)
    ap.add_argument("--limit", type=int, default=0)
    a = ap.parse_args()
    if a.step == "report":
        parity_report()
    else:
        jobs = todo(a.step == "parity")[:a.limit or None]
        run(jobs, a.batch, a.workers, a.step)
        if a.step == "parity":
            parity_report()
