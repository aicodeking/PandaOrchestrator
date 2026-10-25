"""Stage 3: independent labelling by two teacher families (Codex, Kimi) + Ollama tie-breaker.

Answers are point answers per task, stored in data/cache/labels/<teacher>.jsonl (append-only, one
line per task id). Re-running only labels tasks that are missing for that teacher.
"""

import json
import random

from . import paths, teachers
from .common import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES, sha_int
from .jsonio import append_jsonl, read_jsonl
from ..taxonomy import CHECKLIST

BATCH = {"codex": 15, "kimi": 15, "grok": 15, "deepseek": 15, "ollama": 4}
CHUNK = 300
MAX_TASK_CHARS = 4000

FLAG_DEFS = {
    "needs_tools": "must run commands, tests, code or other tools in an environment",
    "needs_vision": "must look at images / screenshots / designs / diagrams",
    "long_context": "must read a very large input (> ~50k tokens: big logs, many files, long docs)",
    "needs_review": "risky enough that the output should be reviewed by a stronger model or human",
    "ambiguous_spec": "underspecified: key requirements, terms or success criteria are missing",
    "multi_file": "changes or reasoning span several files / components",
    "needs_web": "needs browsing or fetching current external information",
}
CATEGORY_DEFS = {
    "implementation": "build new code/features", "bugfix": "diagnose and fix wrong behaviour",
    "refactor": "restructure code without changing behaviour", "test_writing": "write or fix tests",
    "code_review": "review/critique existing code or PRs",
    "research": "investigate and synthesise several sources/options/literature, compare alternatives, deep fact-finding",
    "planning": "plans, designs, estimates, roadmaps", "docs_writing": "documentation, READMEs, reports",
    "ui_frontend": "visual UI building/styling", "data_analysis": "analyse/transform data, SQL, metrics",
    "devops_infra": "CI/CD, deployment, cloud, infra config", "math_reasoning": "math, proofs, algorithms puzzles",
    "chat_simple": "quick Q&A, a short explanation or short writing answerable from general knowledge, no code changes or investigation",
}

ANCHORS = """ANCHOR EXAMPLES (abbreviated: unlisted skills are 0, unlisted flags/checklist ids are 0):
A) "rename the helper `fmt_dt` to `format_datetime` in utils/time.py and update its 2 call sites"
   -> cat=refactor, diff=1, skills: coding=1; flags: none; check: edits_code=1, trivial_one_liner=1, clear_acceptance_criteria=1; out_tokens=150
B) "Add limit/offset pagination to GET /api/orders in our FastAPI app, default 50, max 200, return total count; add pytest tests." ctx: python, 3 files
   -> cat=implementation, diff=4, skills: coding=4, debugging=1, planning=1; flags: needs_tools=1, multi_file=1; check: edits_code=1, new_feature=1,
      needs_run_commands=1, clear_acceptance_criteria=1; out_tokens=1500
C) "Our Go worker pool drops ~0.1% of Kafka messages under load, only in prod. Logs attached (2k lines). Find out why and fix it without hurting throughput."
   -> cat=bugfix, diff=7, skills: coding=6, debugging=8, reasoning=6; flags: needs_tools=1, needs_review=1, multi_file=1; check: edits_code=1,
      has_failing_behavior=1, needs_root_cause=1, needs_run_commands=1, concurrency_or_distributed=1, high_stakes=1, multi_step_plan=1; out_tokens=3000
D) "Design and implement CRDT-based offline sync for our notes app across iOS, Android and web, migrate 40M existing documents with zero downtime,
   and prove the merge function converges." -> cat=implementation (cat2=planning), diff=9, skills: coding=9, planning=9, reasoning=9, math=7,
   debugging=6, review=5; flags: needs_tools=1, needs_review=1, multi_file=1, ambiguous_spec=1; check: edits_code=1, touches_gt3_files=1, new_feature=1,
   needs_run_commands=1, concurrency_or_distributed=1, formal_math_or_proof=1, design_decisions=1, multi_step_plan=1, high_stakes=1; out_tokens=20000"""

PROMPT = """You label tasks for an LLM router. For EACH task below, estimate what a competent assistant would need.

Categories (pick the primary; optional secondary if clearly mixed): {cats}
Difficulty 1-10 (how strong a model must be to succeed): 1 = trivial for any small model; 2-3 = easy, small models usually
succeed; 4-5 = mid-tier model usually succeeds; 6-7 = needs a strong model, subtle/multi-step; 8 = only frontier models usually
succeed; 9 = frontier models often fail; 10 = frontier models usually fail. Use the full range; most everyday tasks are 2-6.
Skills: required level 0-10 for EACH axis ({axes}); 0 = not needed, 10 = best-in-class ability needed. The main axis is usually
near the difficulty; unrelated axes are 0.
Flags (0/1): {flags}
Checklist (0/1 each): {check}
out_tokens: expected number of output tokens a competent model writes to fully complete the task (code + prose), e.g. 50..50000.

{anchors}

Answer ONLY with JSON: {{"labels": [{{"id": "...", "cat": "...", "cat2": null, "diff": 1-10, "skills": {{all {n_axes} axes}},
"flags": {{all {n_flags} ids: 0/1}}, "check": {{all {n_check} ids: 0/1}}, "out_tokens": int}}, ...]}} with one entry per task, same ids.
Do not use tools or read files; judge from the text only.

TASKS:
{tasks}
"""


def _task_block(lid: str, task: dict) -> str:
    text = task["text"]
    if len(text) > MAX_TASK_CHARS:
        text = text[:MAX_TASK_CHARS - 600] + "\n[...]\n" + text[-500:]
    return f"### id={lid}\ncontext: {json.dumps(task.get('context') or {})}\n{text}\n"


def build_prompt(items: list[tuple[str, dict]]) -> str:
    return PROMPT.format(
        cats="; ".join(f"{k} ({v})" for k, v in CATEGORY_DEFS.items()),
        axes=", ".join(SKILL_AXES), flags="; ".join(f"{k} = {v}" for k, v in FLAG_DEFS.items()),
        check="; ".join(f"{c['id']} = {c['q']}" for c in CHECKLIST), anchors=ANCHORS,
        n_axes=len(SKILL_AXES), n_flags=len(FLAGS), n_check=len(CHECKLIST_IDS),
        tasks="\n".join(_task_block(lid, t) for lid, t in items),
    )


def _bit(v) -> int:
    if isinstance(v, str):
        return 1 if v.strip().lower() in ("1", "yes", "y", "true") else 0
    return 1 if v and float(v) >= 0.5 else 0


def clean_answer(a: dict) -> dict:
    """Validate and normalise one teacher answer; raise ValueError if unusable."""
    cat = str(a.get("cat", "")).strip()
    if cat not in CATEGORIES:
        raise ValueError(f"bad cat {cat}")
    cat2 = a.get("cat2")
    cat2 = cat2 if cat2 in CATEGORIES and cat2 != cat else None
    diff = int(round(float(a["diff"])))
    if not 1 <= diff <= 10:
        raise ValueError("bad diff")
    sk = a.get("skills") or {}
    skills = {ax: min(10, max(0, int(round(float(sk.get(ax, 0) or 0))))) for ax in SKILL_AXES}
    fl, ck = a.get("flags") or {}, a.get("check") or {}
    if sum(k in ck for k in CHECKLIST_IDS) < len(CHECKLIST_IDS) - 2:
        raise ValueError("checklist incomplete")
    out_tokens = min(200000, max(10, int(float(a.get("out_tokens") or 0))))
    return {"cat": cat, "cat2": cat2, "diff": diff, "skills": skills,
            "flags": {f: _bit(fl.get(f, 0)) for f in FLAGS},
            "check": {c: _bit(ck.get(c, 0)) for c in CHECKLIST_IDS}, "out_tokens": out_tokens}


def _parser(lids: list[str]):
    def parse(obj):
        items = obj.get("labels") if isinstance(obj, dict) else obj
        if not isinstance(items, list):
            raise ValueError("no labels list")
        got = {}
        for it in items:
            lid = str(it.get("id", "")).strip()
            if lid in lids:
                try:
                    got[lid] = clean_answer(it)
                except (ValueError, TypeError, KeyError):
                    continue
        if len(got) < 0.6 * len(lids):
            raise ValueError(f"only {len(got)}/{len(lids)} labels")
        return got
    return parse


def load_answers(teacher: str) -> dict[str, dict]:
    return {r["id"]: r["ans"] for r in read_jsonl(paths.LABELS / f"{teacher}.jsonl")}


async def _label_batch(teacher: str, batch: list[dict]) -> int:
    lids = [f"t{i:02d}" for i in range(len(batch))]
    prompt = build_prompt(list(zip(lids, [r["task"] for r in batch])))
    got = await teachers.call(teacher, prompt, _parser(lids), purpose="label")
    rows = [{"id": r["id"], "teacher": teacher, "ans": got[lid]} for lid, r in zip(lids, batch) if lid in got]
    append_jsonl(paths.LABELS / f"{teacher}.jsonl", rows)
    print(f"[label] {teacher}: +{len(rows)}/{len(batch)}", flush=True)
    return len(rows)


async def label(tasks: list[dict], teacher: str, seed: int, passes: int = 2) -> None:
    """Label every task missing an answer from `teacher`. Each teacher gets its own shuffle."""
    paths.ensure()
    for p in range(passes):
        have = load_answers(teacher)
        # Same priority order for every teacher (so an early stop still leaves fully dual-labelled
        # tasks), but each teacher shuffles within chunks, giving different batch mates and order.
        todo = sorted((t for t in tasks if t["id"] not in have), key=lambda t: sha_int(f"prio|{t['id']}"))
        if not todo:
            return
        rng = random.Random(f"{teacher}-{seed}-{p}")
        for i in range(0, len(todo), CHUNK):
            chunk = todo[i:i + CHUNK]
            rng.shuffle(chunk)
            todo[i:i + CHUNK] = chunk
        bs = BATCH[teacher]
        print(f"[label] {teacher} pass {p}: {len(todo)} tasks", flush=True)
        await teachers.gather_limited([_label_batch(teacher, todo[i:i + bs]) for i in range(0, len(todo), bs)])


def strong_disagreement(a: dict, b: dict) -> bool:
    return abs(a["diff"] - b["diff"]) >= 3 or a["cat"] != b["cat"]


TIEBREAK_BATCH = 10
TIEBREAK_PROMPT = """You label tasks for an LLM router. For EACH task give only its category and difficulty.

Categories (pick the primary; optional secondary if clearly mixed): {cats}
Difficulty 1-10 (how strong a model must be to succeed): 1 = trivial for any small model; 2-3 = easy, small models usually
succeed; 4-5 = mid-tier model usually succeeds; 6-7 = needs a strong model, subtle/multi-step; 8 = only frontier models usually
succeed; 9 = frontier models often fail; 10 = frontier models usually fail. Most everyday tasks are 2-6.
Anchors: rename a helper and its 2 call sites = refactor, 1. Add limit/offset pagination + tests to a FastAPI endpoint =
implementation, 4. Find why a Go worker pool drops 0.1% of Kafka messages in prod and fix it = bugfix, 7. Design+implement CRDT
offline sync on 3 platforms with zero-downtime migration and a convergence proof = implementation (planning), 9.

Answer ONLY with JSON: {{"labels": [{{"id": "...", "cat": "...", "cat2": null, "diff": 1-10}}, ...]}}, one entry per task.

TASKS:
{tasks}
"""


def clean_tiebreak(a: dict) -> dict:
    cat = str(a.get("cat", "")).strip()
    if cat not in CATEGORIES:
        raise ValueError(f"bad cat {cat}")
    cat2 = a.get("cat2")
    diff = int(round(float(a["diff"])))
    if not 1 <= diff <= 10:
        raise ValueError("bad diff")
    return {"cat": cat, "cat2": cat2 if cat2 in CATEGORIES and cat2 != cat else None, "diff": diff}


def _tb_parser(lids):
    def parse(obj):
        items = obj.get("labels") if isinstance(obj, dict) else obj
        got = {}
        for it in items or []:
            lid = str(it.get("id", "")).strip()
            if lid in lids:
                try:
                    got[lid] = clean_tiebreak(it)
                except (ValueError, TypeError, KeyError):
                    continue
        if len(got) < 0.6 * len(lids):
            raise ValueError(f"only {len(got)}/{len(lids)} labels")
        return got
    return parse


async def _tiebreak_batch(batch: list[dict]) -> None:
    lids = [f"t{i:02d}" for i in range(len(batch))]
    prompt = TIEBREAK_PROMPT.format(cats="; ".join(f"{k} ({v})" for k, v in CATEGORY_DEFS.items()),
                                    tasks="\n".join(_task_block(l, r["task"]) for l, r in zip(lids, batch)))
    got = await teachers.call("ollama", prompt, _tb_parser(lids), purpose="tiebreak")
    rows = [{"id": r["id"], "teacher": "ollama", "ans": got[l]} for l, r in zip(lids, batch) if l in got]
    append_jsonl(paths.LABELS / "ollama.jsonl", rows)
    print(f"[tiebreak] ollama: +{len(rows)}/{len(batch)}", flush=True)


async def tiebreak(tasks: list[dict], passes: int = 2) -> None:
    """Third opinion (category + difficulty only) from local Ollama, most-disputed first."""
    for _ in range(passes):
        have = load_answers("ollama")
        todo = [t for t in tasks if t["id"] not in have]
        if not todo:
            return
        print(f"[tiebreak] {len(todo)} tasks", flush=True)
        await teachers.gather_limited([_tiebreak_batch(todo[i:i + TIEBREAK_BATCH]) for i in range(0, len(todo), TIEBREAK_BATCH)])
