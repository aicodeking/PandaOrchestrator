"""Stage 1: teacher-written synthetic tasks from the seed grid (20 cells per call)."""

import json

from . import paths, teachers
from .common import norm_context
from .grid import sample_cells
from .jsonio import append_jsonl, read_jsonl

BATCH = 20
OUT = "synthetic.jsonl"

PROMPT = """You write realistic task requests that a human or an orchestrator agent sends to an AI coding/knowledge assistant.
Write exactly one task per CELL below. Each cell fixes: category, the primary skill the task stresses, a target
difficulty band on this 1-10 scale, a stack/domain, properties the task must exhibit, the writer persona and the length.

Difficulty scale: 1 = trivial for any small model; 3 = routine, small models usually succeed; 5 = mid-tier model usually
succeeds; 7 = needs a strong model, multi-step, subtle; 8 = only frontier models usually succeed; 10 = frontier models usually fail
(open research-level, huge scope, deeply ambiguous or adversarial). Make the task's real difficulty match the band
through its substance (scope, subtlety, constraints), NOT by saying "this is hard".

Property meanings: needs_tools = must run commands/tests/tools; needs_vision = includes or refers to attached screenshots/
images/designs; long_context = attaches or references very large input (huge logs, whole repos, long docs, >50k tokens; you
may write "[attached: 180k-token log]" style placeholders); ambiguous_spec = vague, missing key details; multi_file = spans
many files; needs_web = needs browsing/fetching current external info; needs_review = output must be reviewed carefully (risky).
"none" = no special properties.

Rules:
- Write in the persona's voice (tone, grammar, vocabulary). Do not mention the persona, the category, the band or these rules.
- Vary openings; avoid "Can you" every time. Use concrete names: files, functions, services, error messages, numbers.
- Respect each cell's length target in characters; long cells should really be long (paste realistic code/logs/config).
- Include code snippets, stack traces, logs or paths when the length allows and it fits. Keep each text under 3500 characters.
- Not every task is a coding task: follow the category (e.g. chat_simple can be a quick factual or writing question).
- Also write a plausible context object the orchestrator would attach:
  {{"repo_languages": [..] or [], "files_in_scope": int, "estimated_input_tokens": int, "has_images": bool, "requires_tools": bool}}
- Output ONLY JSON: {{"tasks": [{{"cell": <cell number>, "text": "...", "context": {{...}}}}, ...]}} with one entry per cell.

CELLS:
{cells}
"""


def _cell_line(i: int, c: dict) -> str:
    return (f"{i}. category={c['category']}; primary_skill={c['axis']}; difficulty_band={c['band'][0]}-{c['band'][1]}; "
            f"stack={c['stack']}; properties={','.join(c['flags']) or 'none'}; persona={c['persona']}; length={c['length']}")


def _parser(cells: list[dict]):
    def parse(obj):
        items = obj.get("tasks") if isinstance(obj, dict) else obj
        if not isinstance(items, list):
            raise ValueError("no tasks list")
        got = {}
        for it in items:
            try:
                idx = int(it["cell"])
            except (KeyError, TypeError, ValueError):
                continue
            text = (it.get("text") or "").strip()
            if 0 <= idx < len(cells) and len(text) >= 8:
                got[idx] = {"text": text, "context": norm_context(it.get("context"))}
        if len(got) < 0.8 * len(cells):
            raise ValueError(f"only {len(got)}/{len(cells)} tasks")
        return got
    return parse


async def _batch(b: int, cells: list[dict], teacher: str) -> list[dict]:
    prompt = PROMPT.format(cells="\n".join(_cell_line(i, c) for i, c in enumerate(cells)))
    got = await teachers.call(teacher, prompt, _parser(cells), purpose="generate")
    rows = []
    for i, t in sorted(got.items()):
        c = cells[i]
        rows.append({
            "id": f"syn-{b:04d}{i:02d}", "source": "synthetic", "pair_of": None,
            "task": t,
            "meta": {"persona": c["persona"], "cell": c, "generator": teacher, "gen_batch": b},
        })
    append_jsonl(paths.POOL / OUT, rows)
    print(f"[gen] batch {b} via {teacher}: {len(rows)} tasks", flush=True)
    return rows


async def generate(n_batches: int, start: int = 0, seed: int = 0, teachers_: tuple[str, ...] = ("codex", "kimi")) -> None:
    paths.ensure()
    done = {r["meta"]["gen_batch"] for r in read_jsonl(paths.POOL / OUT)}
    cells = sample_cells((start + n_batches) * BATCH, seed)
    jobs = []
    for b in range(start, start + n_batches):
        if b in done:
            continue
        teacher = teachers_[b % len(teachers_)]
        jobs.append(_batch(b, cells[b * BATCH:(b + 1) * BATCH], teacher))
    print(f"[gen] {len(jobs)} batches to run ({len(done)} already done)", flush=True)
    await teachers.gather_limited(jobs)


def preview(n: int = 3) -> str:
    return json.dumps(read_jsonl(paths.POOL / OUT)[:n], indent=1)[:4000]
