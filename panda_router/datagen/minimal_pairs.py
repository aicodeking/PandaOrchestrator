"""Stage 5: counterfactual minimal pairs. One controlled edit per original; the label delta is known
by construction (meta.expected_delta). Edited tasks are labelled by the teachers like any other."""

import json
import random

from . import paths, teachers
from .common import norm_context
from .jsonio import append_jsonl, read_jsonl

BATCH = 20
OUT = "minimal_pairs.jsonl"

EDITS = {
    "add_huge_log": {
        "instr": "Attach a very large input that the task now depends on: invent a task-specific attachment (a log, trace, dump, "
                 "CSV, transcript, monorepo, spec PDF...) with its own realistic name and size (80k-250k tokens, or MB/lines), "
                 "mention it naturally in the persona's voice, optionally paste a short excerpt. Never reuse wording from other "
                 "tasks. Set context.estimated_input_tokens to 80000-250000. Change nothing else.",
        "delta": {"flags.long_context": 1, "checklist.input_gt_50k_tokens": 1},
    },
    "add_screenshots": {
        "instr": "Make the task depend on attached images: invent task-specific visuals (screenshots, a Figma mockup, a photo of a "
                 "whiteboard, a chart, an architecture diagram, a scanned form...), vary their number and how they are referred "
                 "to, in the persona's voice. Never reuse wording from other tasks. Set context.has_images=true. Change nothing else.",
        "delta": {"flags.needs_vision": 1, "checklist.has_images": 1},
    },
    "remove_acceptance": {
        "instr": "Remove the acceptance criteria, success conditions and concrete requirements (exact behaviour, numbers, "
                 "formats, constraints), making the request vague and underspecified. KEEP any pasted code, logs, data or "
                 "repository name verbatim: only the asks become vague. The scope of work must stay the same.",
        "delta": {"flags.ambiguous_spec": 1, "checklist.clear_acceptance_criteria": 0},
    },
    "add_scope": {
        "instr": "Make it clearly harder by adding substantial scope: e.g. 'and write a zero-downtime migration plan', 'and support "
                 "3 more backends', 'and make it safe under concurrent writers', or 'and prove it'. Keep the original text and append "
                 "the extra requirement(s). Increase context.files_in_scope accordingly.",
        "delta": {"difficulty": "+"},
    },
    "simplify": {
        "instr": "Simplify it into a much easier one-line request on the same topic (a small sub-part of the original). "
                 "Shrink context.files_in_scope and estimated_input_tokens accordingly.",
        "delta": {"difficulty": "-", "checklist.trivial_one_liner": 1},
    },
}

PROMPT = """You apply ONE controlled edit to each task below, producing a "minimal pair": the edited task must differ from the
original ONLY by the requested edit; keep voice, topic, names and everything else the same. Phrase every edit differently and
specifically for its task; do not copy wording from these instructions or repeat the same sentence across tasks.

{edits}

Return ONLY JSON: {{"edits": [{{"id": "<id>", "text": "<edited task text>", "context": {{edited context object}}}}, ...]}}, one per task.
Do not use tools.

TASKS:
{tasks}
"""


def choose_edit(task: dict, rng: random.Random) -> str:
    """Pick an edit whose expected flag flip is not already true for this task."""
    ctx = task.get("context") or {}
    text = task["text"].lower()
    opts = ["add_scope", "add_scope"]
    if len(task["text"]) > 250:
        opts.append("remove_acceptance")
    if (ctx.get("estimated_input_tokens") or 0) < 30000 and "attached" not in text:
        opts.append("add_huge_log")
    if not ctx.get("has_images") and "screenshot" not in text and "image" not in text:
        opts.append("add_screenshots")
    if len(task["text"]) > 160:
        opts += ["simplify", "simplify"]
    return rng.choice(opts)


def _parser(lids):
    def parse(obj):
        items = obj.get("edits") if isinstance(obj, dict) else obj
        got = {}
        for it in items or []:
            lid = str(it.get("id", ""))
            if lid in lids and len((it.get("text") or "").strip()) >= 8:
                got[lid] = {"text": it["text"].strip(), "context": norm_context(it.get("context"))}
        if len(got) < 0.7 * len(lids):
            raise ValueError(f"only {len(got)}/{len(lids)} edits")
        return got
    return parse


async def _batch(teacher: str, batch: list[tuple[dict, str]]) -> None:
    lids = [f"m{i:02d}" for i in range(len(batch))]
    blocks = []
    for lid, (r, edit) in zip(lids, batch):
        blocks.append(f"### id={lid}  EDIT={edit}\ncontext: {json.dumps(r['task'].get('context') or {})}\n{r['task']['text'][:3500]}\n")
    prompt = PROMPT.format(edits="\n".join(f"EDIT={k}: {v['instr']}" for k, v in EDITS.items()), tasks="\n".join(blocks))
    got = await teachers.call(teacher, prompt, _parser(lids), purpose="minimal_pair")
    rows = []
    for lid, (r, edit) in zip(lids, batch):
        if lid not in got or got[lid]["text"].strip() == r["task"]["text"].strip():
            continue
        rows.append({
            "id": f"mp-{r['id']}-{edit}", "source": "minimal-pair", "pair_of": r["id"], "task": got[lid],
            "meta": {"edit": edit, "expected_delta": EDITS[edit]["delta"], "editor": teacher,
                     "orig_source": r["source"], "persona": r.get("meta", {}).get("persona")},
        })
    append_jsonl(paths.POOL / OUT, rows)
    print(f"[mp] {teacher}: +{len(rows)}/{len(batch)}", flush=True)


async def make_pairs(originals: list[dict], n: int, seed: int = 0, editors: tuple[str, ...] = ("codex", "grok")) -> None:
    paths.ensure()
    done = {r["pair_of"] for r in read_jsonl(paths.POOL / OUT)}
    rng = random.Random(seed)
    pool = sorted(originals, key=lambda r: r["id"])
    rng.shuffle(pool)
    todo = [r for r in pool if r["id"] not in done][:max(0, n - len(done))]
    plan = [(r, choose_edit(r["task"], random.Random(r["id"]))) for r in todo]
    jobs = [_batch(editors[(i // BATCH) % len(editors)], plan[i:i + BATCH]) for i in range(0, len(plan), BATCH)]
    print(f"[mp] {len(plan)} edits in {len(jobs)} batches", flush=True)
    await teachers.gather_limited(jobs)
