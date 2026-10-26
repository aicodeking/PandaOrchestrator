"""Fixed hand-written sanity tasks (easy / medium / hard) scored by expected difficulty.

  .venv/bin/python scripts/eval/hard_tasks.py --profilers onnx:artifacts/panda-router-v1 onnx:artifacts/panda-router-v2 \
      --out eval_reports/v2/hard_tasks.md

A task passes when its expected difficulty is inside its band: easy <= 3, medium 3..7, hard >= 6.
The two contract checks are tighter: the lock-free MPMC proof must be >= 7 and HTTP 418 <= 2.
"""

import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

from panda_router.eval.baselines import load_profiler  # noqa: E402

BANDS = {"easy": (1.0, 3.0), "medium": (3.0, 7.0), "hard": (6.0, 10.0)}
TOOLS = {"requires_tools": True, "repo_languages": ["python"]}
# (band, text, context, optional (lo, hi) override)
TASKS = [
    ("easy", "What does HTTP 418 mean?", {}, (1.0, 2.0)),
    ("easy", "Convert 72 degrees Fahrenheit to Celsius.", {}, None),
    ("easy", "Fix the typo 'recieve' -> 'receive' in README.md.", TOOLS, None),
    ("easy", "What is the capital of Australia?", {}, None),
    ("easy", "Write a one-line Python expression that reverses a string s.", {}, None),
    ("easy", "Rename the variable `tmp` to `buffer` in utils/io.py.", TOOLS, None),
    ("easy", "Give me a synonym for 'happy'.", {}, None),
    ("medium", "Add pagination (limit/offset query params) to the GET /users endpoint of our FastAPI app and update "
               "the tests.", TOOLS, None),
    ("medium", "Write a bash script that rotates the logs in /var/log/myapp daily and keeps 7 compressed copies.", {}, None),
    ("medium", "Our React form re-renders on every keystroke and feels slow; find why and fix it.",
     {**TOOLS, "repo_languages": ["typescript"]}, None),
    ("medium", "Write a SQL query that returns the top 3 customers by revenue per month from orders(customer_id, "
               "amount, created_at).", {}, None),
    ("medium", "Refactor the payment module to use dependency injection for the gateway client; keep behaviour "
               "unchanged.", TOOLS, None),
    ("medium", "Explain the difference between optimistic and pessimistic locking with examples.", {}, None),
    ("hard", "Design a lock-free MPMC queue in Rust and prove it is linearizable", {}, (7.0, 10.0)),
    ("hard", "Our Raft-based KV store loses acknowledged writes after a leader re-election under network partitions. "
             "Find the bug in the log replication code and add a Jepsen-style test.", TOOLS, None),
    ("hard", "Implement a garbage collector (concurrent mark-sweep with write barriers) for our toy JVM in C++.",
     {**TOOLS, "repo_languages": ["cpp"]}, None),
    ("hard", "Prove that every planar graph is 5-colorable, then give a linear-time 5-coloring algorithm.", {}, None),
    ("hard", "Port our CUDA attention kernel to Metal while keeping numerical parity within 1e-3 and beating the "
             "PyTorch MPS baseline.", {**TOOLS, "repo_languages": ["cpp"]}, None),
    ("hard", "Find and fix the data race that corrupts the B-tree under concurrent splits in our storage engine; "
             "it only reproduces under heavy load.", {**TOOLS, "repo_languages": ["rust"]}, None),
    ("hard", "Design a multi-region active-active payment ledger with exactly-once semantics and write the "
             "consistency argument.", {}, None),
]


def run(specs: list[str]) -> dict:
    res = {}
    for spec in specs:
        prof = load_profiler(spec)
        rows = []
        for band, text, ctx, override in TASKS:
            lo, hi = override or BANDS[band]
            p = prof.profile({"text": text, "context": ctx})
            d = p.expected_difficulty()
            rows.append({"band": band, "text": text, "expected_difficulty": round(d, 2), "lo": lo, "hi": hi,
                         "pass": lo <= d <= hi, "category": max(p.category, key=p.category.get)})
        res[spec] = {"pass_rate": sum(r["pass"] for r in rows) / len(rows), "rows": rows}
    return res


def markdown(res: dict) -> str:
    specs = list(res)
    names = [s.split("/")[-1] for s in specs]
    out = ["| band | task | target | " + " | ".join(names) + " |", "|---|---|---|" + "---|" * len(specs)]
    for i, (band, text, _, _) in enumerate(TASKS):
        r0 = res[specs[0]]["rows"][i]
        cells = [f"{res[s]['rows'][i]['expected_difficulty']:.1f} {res[s]['rows'][i]['category']}"
                 f"{'' if res[s]['rows'][i]['pass'] else ' ✗'}" for s in specs]
        short = text if len(text) <= 70 else text[:67] + "..."
        out.append(f"| {band} | {short} | {r0['lo']:g}–{r0['hi']:g} | " + " | ".join(cells) + " |")
    out.append("| | **pass rate** | | " + " | ".join(f"**{res[s]['pass_rate']:.2f}**" for s in specs) + " |")
    return "\n".join(out) + "\n"


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--profilers", nargs="+", required=True)
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    res = run(a.profilers)
    md = markdown(res)
    Path(a.out).write_text(md)
    Path(a.out).with_suffix(".json").write_text(json.dumps(res, indent=2))
    print(md)


if __name__ == "__main__":
    main()
