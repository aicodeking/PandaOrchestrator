"""Write data/outcomes/REPORT_v4_attempts.md from the graded cells (run after attempts_v4.py + build_attempts.py).
Usage: .venv/bin/python scripts/outcomes/report_v4.py
"""

import json
import sys
from collections import Counter, defaultdict
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))
sys.path.insert(0, str(ROOT / "scripts" / "outcomes"))

from attempts import RAW, read_jsonl, tasks  # noqa: E402
from build_attempts import CARDS, CLAUDE_MODELS, CODEX_MODELS, MODELS, OLD_MODELS, load_cells  # noqa: E402

from panda_router.outcomes.grade import ATTEMPT_SYSTEM, cohen_kappa  # noqa: E402

OUT = ROOT / "data" / "outcomes"
SUB = [*CLAUDE_MODELS, *CODEX_MODELS]


def boot_ci(a, b, n=2000):
    rng = np.random.default_rng(0)
    a, b = np.array(a), np.array(b)
    ks = [cohen_kappa(list(a[i]), list(b[i])) for i in rng.integers(0, len(a), (n, len(a)))]
    return np.percentile(ks, [2.5, 97.5])


def parity() -> str:
    by = defaultdict(dict)
    for r in read_jsonl(RAW / "grades.jsonl"):
        if r.get("pass") is not None:
            by[(r["task_id"], r["model"])][r["judge"]] = r["pass"]
    out = []
    for x, y in (("dsh", "ds-think"), ("dsh", "kimi"), ("codex-terra", "ds-think"), ("codex-terra", "kimi"),
                 ("ds-think", "kimi")):
        ks = sorted(k for k, v in by.items() if {x, y, "ds-think", "kimi"} <= v.keys())
        a, b = [by[k][x] for k in ks], [by[k][y] for k in ks]
        lo, hi = boot_ci(a, b)
        out.append(f"| {x} vs {y} | {len(ks)} | {np.mean(np.array(a) == np.array(b)):.3f} | {cohen_kappa(a, b):.3f} "
                   f"({lo:.2f}-{hi:.2f}) | {np.mean(a):.2f} / {np.mean(b):.2f} |")
    return ("| pair | n gold cells | agreement | Cohen kappa (95% CI) | pass rate (first / second) |\n|---|---|---|---|---|\n"
            + "\n".join(out))


def prices() -> dict:
    return {m: json.loads((CARDS / f"{m}.json").read_text())["cost"] for m in MODELS}


def cell_cost(row, p, ttext) -> float:
    inp = row.in_tokens if row.model in OLD_MODELS else (len(ATTEMPT_SYSTEM) + len(ttext[row.task_id])) / 4
    return (inp * p[row.model]["input_per_mtok"] + row.out_tokens * p[row.model]["output_per_mtok"]) / 1e6


def main():
    cells = load_cells()
    p, ttext = prices(), {t["id"]: t["text"] for t in tasks()}
    cells["usd"] = [cell_cost(r, p, ttext) for r in cells.itertuples()]
    gold, tv = cells[cells.split == "gold"], cells[cells.split != "gold"]
    cov = []
    for m in MODELS:
        cov.append(f"| {m} | {tv[tv.model == m].task_id.nunique()} | {gold[gold.model == m].task_id.nunique()} | "
                   f"{gold[gold.model == m]['pass'].mean() * 100:.1f} | {(tv[tv.model == m]['pass'].mean() * 100):.1f} | "
                   f"{(gold[gold.model == m].finish == 'length').mean() * 100:.0f}% |")
    pv_pass = gold.pivot_table(index="task_id", columns="model", values="pass", aggfunc="first")
    pv_usd = gold.pivot_table(index="task_id", columns="model", values="usd", aggfunc="first")

    def table(pool, label):
        d = pv_pass[pool].dropna()
        u = pv_usd[pool].loc[d.index]
        n = len(d)
        lines = [f"**{label}: {n} gold tasks with every model graded.**\n", "| strategy | success / 100 | est. $ / 100 |", "|---|---|---|"]
        for m in pool:
            lines.append(f"| always {m} | {d[m].mean() * 100:.1f} | {u[m].mean() * 100:.3f} |")
        ok = d.astype(bool).to_numpy()
        usd = u.to_numpy()
        best = np.where(ok, usd, np.inf).argmin(axis=1)
        cheap = usd.argmin(axis=1)
        pick = np.where(ok.any(axis=1), best, cheap)  # a task nobody passes costs the cheapest model's attempt
        lines.append(f"| ORACLE (cheapest passing model) | {ok.any(axis=1).mean() * 100:.1f} | "
                     f"{usd[np.arange(n), pick].mean() * 100:.3f} |")
        return "\n".join(lines)

    mix = cells.groupby(['label', cells.split.eq('gold').map({True: 'gold', False: 'train/val'})]).size()
    judge_mix = ', '.join(f'{a[0]} {a[1]}: {n}' for a, n in mix.items())
    nine = [m for m in MODELS if m in pv_pass]
    props = json.loads((OUT / "card_deltas_attempts.json").read_text())
    drows = [f"| {q['card']} | {q['card_mean']} | {q['fitted_mean']} (+-{q['se']}) | {q['delta_mean']:+.2f} | "
             + (", ".join(f"{a} {v['current']}->{v['fitted']} (n={v['n_items']})" for a, v in q['axes'].items() if v['apply']) or "none")
             + " |" for q in props]
    md = f"""# v4 attempt-and-grade: dsh judge and subscription attempters (2026-10-27)

No OpenRouter calls were made. Judges: stored ds-think labels where they exist, `dsh --profile headless` (DeepSeek) for
930 cells before its balance ran out, and `gpt-5.6-terra` via `codex exec` for the other 3,191. Claude models ran through
`claude -p` (no tools, own system prompt, `--effort low`), and gpt-6-luna through `codex exec` (read-only, bare
CODEX_HOME, reasoning effort low). The attempt system prompt is the one used for the OpenRouter attempters.
Thinking budgets are **not** capped for the Claude models (neither flag nor env var limited it in a test), unlike the
1,500-token cap on the OpenRouter models. Code: `panda_router/outcomes/cli_chat.py`, `scripts/outcomes/attempts_v4.py`,
`build_attempts.py` (9 models), `report_v4.py`.

## Judge parity

Same fixed 100-answer gold validation sample (cells with both stored ds-think and kimi-k3.1-pro grades) for all pairs;
n differs slightly where a judge returned no parseable verdict. The dsh harness judge (`dsh --profile headless`, same
JUDGE_PROMPT and rubric) reached kappa 0.745 vs ds-think, just under the 0.75 bar, but 0.77 vs the neutral kimi judge.
It then ran out of balance ("QUOTA: Insufficient Balance") after 1,029 train/val+gold cells; the 3,133 failed dsh calls are
error rows and are not counted. The remaining cells were graded by `gpt-5.6-terra` through `codex exec` (not an attempter,
so no self-grading), 10 items per prompt with the same rubric, bar kappa >= 0.7 vs kimi (`scripts/outcomes/judge_terra.py`).

{parity()}

Judge mix of the labels used (train/val | gold): {judge_mix}

Label rule: ds-think > dsh > codex-terra. Only cells with a valid grade enter the fit.

## Coverage and gold pass rates

| model | train/val tasks graded | gold tasks graded | gold pass % | train/val pass % | gold answers cut at length |
|---|---|---|---|---|---|
{chr(10).join(cov)}

## Baselines on the gold pool

$ is estimated from card prices x tokens: logged prompt/completion tokens for the OpenRouter models, and
(system + task chars)/4 input plus logged output tokens (thinking included) for the subscription models (no cache
discount, so Claude/luna costs are upper-ish bounds).

{table(nine, "9-model pool")}

{table(SUB, "4 subscription models only")}

## Card updates (applied, provenance 'verified (attempt-grade v4)')

IRT: 1PL, {len(cells)} graded cells, joint over 9 models, link anchored on the 9 cards' own mean thetas (so deltas are
relative to the cards' consensus, not absolute). An axis is updated only with >= 25 items on that axis and a delta above the
combined uncertainty; for the 5 OpenRouter models the direction must also hold under gpt-6.1-sol grading (not available for
the 4 subscription models). `supersedes` is untouched.

| card | card mean | fitted mean | delta | axes updated |
|---|---|---|---|---|
{chr(10).join(drows)}

Caveats: the three judges differ (kappa 0.68-0.75 pairwise vs ds-think), so cross-judge pass rates carry a few points of
noise; train/val cells of the 4 new models cover 400 tasks (opus 150), so their axis evidence is thinner; Claude models
ran with uncapped thinking, which favours them against the 1,500-token-capped OpenRouter models. Haiku-5.5 moved up by
~1.4 theta (card was seeded low); opus moved down (-0.7 coding, only 31 items). The oracle (94.0 on 9 models, 91.3 on
the 4 subscription models) is an upper bound on routing and uses the judge labels as truth.

Files: `data/outcomes/{{attempts,tasks_attempts,gold_attempts,success_cells}}.jsonl`, `fit_attempts.json`,
`card_deltas_attempts.json`. `success_cells.jsonl`: task_id, split (train/val/gold; gold = evaluation only), text,
card_id, pass, judge.
"""
    (OUT / "REPORT_v4_attempts.md").write_text(md)
    print(md)


if __name__ == "__main__":
    main()
