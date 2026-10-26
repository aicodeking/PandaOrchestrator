"""Stage 1b: synthetic hard-tail tasks the v1 profiler under-rated.

Three groups, each generated from topic seeds x personas x lengths (same cell format and output
shape as generate.py, written to pool/hard.jsonl):
  hard      difficulty 7-10 in concurrency, distributed systems, compilers, proofs, performance, security,
            large refactors, research-grade math
  deceptive simple-sounding tasks (one-liners) whose real difficulty is 7-10
  scary     alarming / jargon-heavy tasks whose real difficulty is 1-4
"""

import random

from . import paths, teachers
from .generate import _parser
from .grid import LENGTHS, PERSONAS
from .jsonio import append_jsonl, read_jsonl

OUT = "hard.jsonl"
BATCH = 10
GEN_BATCH_BASE = 10000  # keeps meta.gen_batch disjoint from generate.py batches

TOPICS = [
    ("concurrency", "lock-free / wait-free data structures, memory ordering, linearizability, deadlocks"),
    ("distributed systems", "consensus, replication, CRDTs, exactly-once delivery, distributed transactions, clock skew"),
    ("compilers", "parsers, type inference, optimisation passes, JIT, register allocation, garbage collectors"),
    ("formal proofs", "proving algorithm correctness, loop invariants, Coq/Lean/TLA+ specifications, refinement"),
    ("performance", "profiling and optimising hot paths, cache behaviour, SIMD, GPU kernels, p99 latency"),
    ("security", "exploit analysis, cryptographic protocol flaws, sandbox escapes, side channels, threat modelling"),
    ("large refactors", "migrating a million-line codebase, monolith decomposition, zero-downtime schema migrations"),
    ("research math", "combinatorics, number theory, probability bounds, optimisation theory, numerical analysis"),
    ("databases", "query planners, storage engines, MVCC, index design, replication lag, WAL recovery"),
    ("systems / OS", "kernel drivers, schedulers, filesystems, virtual memory, eBPF, containers internals"),
    ("ML systems", "distributed training, numerical stability, custom autograd, quantisation, serving at scale"),
    ("legacy / ambiguity", "undocumented legacy systems, conflicting requirements, no tests, high-stakes data migration"),
]

GROUPS = {
    "hard": ("Write tasks whose REAL difficulty is {lo}-{hi} on the scale: only frontier models usually succeed, or even they usually fail. "
             "Difficulty must come from substance: subtle invariants, huge scope, deep theory, tight constraints, interacting components. "
             "Mix coding, design, proof and analysis tasks. Give concrete specifics (languages, sizes, constraints).", (7, 10)),
    "deceptive": ("Write tasks that SOUND simple, short and casual (often one or two sentences, no scary jargon in the framing) "
                  "but whose REAL difficulty is {lo}-{hi}: a small-looking request hiding an open-ended, subtle or research-grade problem "
                  "(e.g. 'make our checkout idempotent', 'why is this test flaky only on CI', 'speed this up 10x', 'prove this holds for all n').",
                  (7, 10)),
    "scary": ("Write tasks that SOUND intimidating (urgent tone, heavy jargon, 'production', 'critical', 'security', 'kernel', 'proof') "
              "but whose REAL difficulty is only {lo}-{hi}: a routine edit, a well-known recipe, a textbook question or a small config change "
              "hidden behind alarming wording.", (1, 4)),
}

PROMPT = """You write realistic task requests that a human or an orchestrator agent sends to an AI coding/knowledge assistant.
{group_rule}

Difficulty scale: 1 = trivial for any small model; 3 = routine, small models usually succeed; 5 = mid-tier model usually
succeeds; 7 = needs a strong model, multi-step, subtle; 8 = only frontier models usually succeed; 9 = frontier models often
fail; 10 = frontier models usually fail (open research-level, huge scope, deeply ambiguous or adversarial).
Never say "this is hard/easy" and never mention the difficulty scale; the substance must carry the difficulty.

Write exactly one task per CELL. Each cell fixes a topic area, the writer persona and the length.
Rules:
- Write in the persona's voice. Vary openings; avoid "Can you" every time. Use concrete names: files, functions, services, numbers.
- Respect each cell's length target; long cells should include realistic pasted code, logs or specs. Keep each text under 3500 characters.
- Also write a plausible context object the orchestrator would attach:
  {{"repo_languages": [..] or [], "files_in_scope": int, "estimated_input_tokens": int, "has_images": bool, "requires_tools": bool}}
- Output ONLY JSON: {{"tasks": [{{"cell": <cell number>, "text": "...", "context": {{...}}}}, ...]}} with one entry per cell.

CELLS:
{cells}
"""

COUNTS = {"hard": 400, "deceptive": 150, "scary": 150}


def make_cells(group: str, n: int, seed: int) -> list[dict]:
    rng = random.Random(f"{group}-{seed}")
    lengths = LENGTHS if group == "hard" else LENGTHS[:3] if group == "deceptive" else LENGTHS[:4]
    return [{"group": group, "topic": TOPICS[i % len(TOPICS)], "persona": rng.choice(PERSONAS), "length": rng.choice(lengths)}
            for i in range(n)]


def _line(i: int, c: dict) -> str:
    return f"{i}. topic={c['topic'][0]} ({c['topic'][1]}); persona={c['persona']}; length={c['length']}"


async def _batch(b: int, group: str, cells: list[dict], teacher: str) -> None:
    rule, (lo, hi) = GROUPS[group]
    prompt = PROMPT.format(group_rule=rule.format(lo=lo, hi=hi), cells="\n".join(_line(i, c) for i, c in enumerate(cells)))
    got = await teachers.call(teacher, prompt, _parser(cells), purpose="generate-hard")
    rows = [{"id": f"hrd-{b:04d}{i:02d}", "source": "synthetic", "pair_of": None, "task": t,
             "meta": {"persona": cells[i]["persona"], "cell": cells[i], "generator": teacher,
                      "gen_batch": GEN_BATCH_BASE + b, "hard_group": group}}
            for i, t in sorted(got.items())]
    append_jsonl(paths.POOL / OUT, rows)
    print(f"[hard] batch {b} ({group}) via {teacher}: {len(rows)} tasks", flush=True)


async def generate(counts: dict[str, int] = COUNTS, seed: int = 0, teacher: str = "codex") -> None:
    paths.ensure()
    done = {r["meta"]["gen_batch"] - GEN_BATCH_BASE for r in read_jsonl(paths.POOL / OUT)}
    jobs, b = [], 0
    for group, n in counts.items():
        cells = make_cells(group, n, seed)
        for i in range(0, n, BATCH):
            if b not in done:
                jobs.append(_batch(b, group, cells[i:i + BATCH], teacher))
            b += 1
    print(f"[hard] {len(jobs)} batches to run", flush=True)
    await teachers.gather_limited(jobs)
