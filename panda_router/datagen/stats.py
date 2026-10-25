"""data/STATS.md: counts, teacher agreement, minimal-pair checks, throughput and known issues."""

import math
import time
from collections import Counter, defaultdict

from . import label as L
from . import paths
from .common import CHECKLIST_IDS, FLAGS
from .jsonio import read_jsonl
from .teachers import CODEX_MODEL, GROK_MODEL, OLLAMA_MODEL

KNOWN_ISSUES_FILE = paths.ROOT / "scripts" / "datagen" / "known_issues.md"  # hand notes merged into STATS.md


def _kappa(x: list[int], y: list[int]) -> float | None:
    n = len(x)
    if not n:
        return None
    po = sum(a == b for a, b in zip(x, y)) / n
    px, py = sum(x) / n, sum(y) / n
    pe = px * py + (1 - px) * (1 - py)
    return None if pe >= 1 else round((po - pe) / (1 - pe), 3)


def teacher_agreement(ids: list[str], t1: str = "codex", t2: str = "grok") -> dict:
    from scipy.stats import spearmanr

    cx, km = L.load_answers(t1), L.load_answers(t2)
    both = [i for i in ids if i in cx and i in km]
    if not both:
        return {"n": 0}
    a, b = [cx[i] for i in both], [km[i] for i in both]
    out = {
        "n": len(both),
        "category_acc": round(sum(x["cat"] == y["cat"] for x, y in zip(a, b)) / len(both), 4),
        "difficulty_spearman": round(float(spearmanr([x["diff"] for x in a], [y["diff"] for y in b])[0]), 4),
        "difficulty_mae": round(sum(abs(x["diff"] - y["diff"]) for x, y in zip(a, b)) / len(both), 3),
        "difficulty_mean": {t1: round(sum(x["diff"] for x in a) / len(a), 2), t2: round(sum(y["diff"] for y in b) / len(b), 2)},
        "strong_disagreement_rate": round(sum(L.strong_disagreement(x, y) for x, y in zip(a, b)) / len(both), 4),
        "out_tokens_log10_spearman": round(float(spearmanr([math.log10(x["out_tokens"]) for x in a], [math.log10(y["out_tokens"]) for y in b])[0]), 4),
        "flag_kappa": {f: _kappa([x["flags"][f] for x in a], [y["flags"][f] for y in b]) for f in FLAGS},
        "checklist_kappa": {c: _kappa([x["check"][c] for x in a], [y["check"][c] for y in b]) for c in CHECKLIST_IDS},
        "skill_spearman": {},
    }
    for ax in a[0]["skills"]:
        out["skill_spearman"][ax] = round(float(spearmanr([x["skills"][ax] for x in a], [y["skills"][ax] for y in b])[0]), 3)
    ks = [v for v in out["flag_kappa"].values() if v is not None]
    out["flag_kappa_mean"] = round(sum(ks) / len(ks), 3) if ks else None
    ks = [v for v in out["checklist_kappa"].values() if v is not None]
    out["checklist_kappa_mean"] = round(sum(ks) / len(ks), 3) if ks else None
    return out


def _agreement_md(t1: str, t2: str, ids: list[str]) -> list[str]:
    agr = teacher_agreement(ids, t1, t2)
    if not agr.get("n"):
        return [f"### {t1} vs {t2}", "", "- no overlap", ""]
    return [
        f"### {t1} vs {t2}", "",
        f"- n = {agr.get('n')}",
        f"- Primary category accuracy: **{agr.get('category_acc')}**",
        f"- Difficulty Spearman: **{agr.get('difficulty_spearman')}**, MAE {agr.get('difficulty_mae')}, means {agr.get('difficulty_mean')}",
        f"- Strong disagreement (|Δdiff| ≥ 3 or different primary category) rate: {agr.get('strong_disagreement_rate')}",
        f"- Flag Cohen's κ mean: **{agr.get('flag_kappa_mean')}**; checklist κ mean: {agr.get('checklist_kappa_mean')}",
        f"- out_tokens (log10) Spearman: {agr.get('out_tokens_log10_spearman')}",
        "", "| flag | κ |", "|---|---|", *[f"| {k} | {v} |" for k, v in agr["flag_kappa"].items()], "",
        "| checklist id | κ |", "|---|---|", *[f"| {k} | {v} |" for k, v in agr["checklist_kappa"].items()], "",
        "| skill axis | Spearman |", "|---|---|", *[f"| {k} | {v} |" for k, v in agr["skill_spearman"].items()], "",
    ]


def _exp_diff(r):
    return sum((i + 1) * p for i, p in enumerate(r["labels"]["difficulty"]))


def pair_checks(all_recs: dict[str, dict]) -> dict:
    """Does the merged label of the edited task move in the expected direction vs its original?"""
    res = defaultdict(lambda: [0, 0])
    for r in all_recs.values():
        if r["source"] != "minimal-pair" or r["pair_of"] not in all_recs:
            continue
        o, e = all_recs[r["pair_of"]], r["meta"]["edit"]
        for k, v in r["meta"]["expected_delta"].items():
            if k == "difficulty":  # teacher means only (BT calibration is applied to originals, not to pairs)
                d_e, d_o = r["meta"]["difficulty_teacher_mean"], o["meta"]["difficulty_teacher_mean"]
                ok = d_e > d_o if v == "+" else d_e < d_o
            else:
                grp, name = k.split(".")
                lab = r["labels"]["flags" if grp == "flags" else "checklist"][name]
                olab = o["labels"]["flags" if grp == "flags" else "checklist"][name]
                ok = lab > olab or lab == v if v == 1 else lab < olab or lab == v
            res[f"{e}: {k}"][0] += ok
            res[f"{e}: {k}"][1] += 1
    return {k: f"{a}/{n} ({a / n:.0%})" for k, (a, n) in sorted(res.items())}


def throughput() -> dict:
    log = read_jsonl(paths.CALL_LOG)
    out = {}
    for (t, p), rows in sorted(_group(log).items()):
        ok = [r for r in rows if r["ok"]]
        out[f"{t}/{p}"] = {"calls": len(rows), "ok": len(ok), "mean_secs_ok": round(sum(r["secs"] for r in ok) / max(1, len(ok)), 1)}
    if log:
        span = max(r["ts"] + r["secs"] for r in log) - min(r["ts"] for r in log)
        out["_wall_clock_hours_first_to_last_call"] = round(span / 3600, 2)
        out["_total_calls"] = len(log)
        out["_failed_calls"] = sum(not r["ok"] for r in log)
    return out


def _group(log):
    g = defaultdict(list)
    for r in log:
        g[(r["teacher"], r["purpose"])].append(r)
    return g


def _table(counter: Counter, total: int) -> str:
    lines = ["| key | n | % |", "|---|---|---|"]
    for k, v in sorted(counter.items(), key=lambda kv: (-kv[1], str(kv[0]))):
        lines.append(f"| {k} | {v} | {100 * v / max(1, total):.1f} |")
    return "\n".join(lines)


def write_stats(splits: dict[str, list[dict]], report: dict) -> None:
    allr = [r for rows in splits.values() for r in rows]
    by_id = {r["id"]: r for r in allr}
    n = len(allr)
    src = Counter(r["source"] for r in allr)
    origin_src = Counter(r["source"] if r["source"] != "minimal-pair" else "minimal-pair(" + r["meta"].get("orig_source", "?") + ")" for r in allr)
    real = sum(v for k, v in src.items() if k in ("swe-rebench", "swe-smith", "wildchat"))
    originals = n - src.get("minimal-pair", 0)
    cat = Counter(max(r["labels"]["category"].items(), key=lambda kv: kv[1])[0] for r in allr)
    diff = Counter(int(round(_exp_diff(r))) for r in allr)
    split_src = {s: Counter(r["source"] for r in rows) for s, rows in splits.items()}
    agrees = [r["meta"]["agreement"] for r in allr if r["meta"].get("agreement") is not None]
    mean_agree = sum(agrees) / max(1, len(agrees))
    third = sum("ollama" in r["meta"]["teachers"] for r in allr)
    teacher_sets = Counter("+".join(t for t in r["meta"]["teachers"] if t != "ollama") for r in allr)
    tp = throughput()
    edits = Counter(r["meta"]["edit"] for r in allr if r["source"] == "minimal-pair")
    md = [
        "# Panda Router training data: statistics",
        "",
        f"Generated {time.strftime('%Y-%m-%d %H:%M')} by `scripts/datagen/run.py build`. Format: `schemas/CONTRACTS.md`.",
        "",
        "## Totals",
        "",
        f"- Labelled records: **{n}** (originals {originals}, minimal pairs {src.get('minimal-pair', 0)})",
        f"- Real-seed share of originals: **{100 * real / max(1, originals):.1f}%** ({real}/{originals})",
        f"- Splits: " + ", ".join(f"{s} {len(rows)}" for s, rows in splits.items()),
        f"- Records with a third (Ollama {OLLAMA_MODEL}) opinion: {third}",
        f"- Mean per-record agreement (meta.agreement, over full-label teachers): {mean_agree:.3f}",
        f"- Minimal pairs labelled by a single teacher (meta.single_teacher=true, kept so pairs reach the target): {report.get('single_teacher_pairs', 0)}",
        f"- Records per full-label teacher set: " + ", ".join(f"{k} {v}" for k, v in sorted(teacher_sets.items())),
        f"- Near-duplicates dropped (cos > {report['dedup']['dup_threshold']}): {report['dedup']['near_dup_dropped']};"
        f" clusters: {report['dedup']['clusters']}; pool tasks not (yet) labelled by enough teachers (excluded): {report['missing_teacher']}",
        "",
        "## Per source", "", _table(src, n), "",
        "## Per source incl. minimal-pair origin", "", _table(origin_src, n), "",
        "## Per split and source", "",
        "| split | " + " | ".join(sorted(src)) + " |", "|---|" + "---|" * len(src),
        *[f"| {s} | " + " | ".join(str(c.get(k, 0)) for k in sorted(src)) + " |" for s, c in split_src.items()], "",
        "## Per primary category (argmax of soft label)", "", _table(cat, n), "",
        "## Per difficulty (rounded expected difficulty of the final soft label)", "", _table(diff, n), "",
        "## Teacher agreement (raw point answers, per teacher pair)", "",
        f"Teachers: codex = {CODEX_MODEL}, kimi = Kimi CLI default, grok = {GROK_MODEL}, ollama = {OLLAMA_MODEL} (tie-break: category + difficulty only).", "",
        *[line for t1, t2 in (("codex", "grok"), ("codex", "kimi"), ("kimi", "grok")) for line in _agreement_md(t1, t2, [r["id"] for r in allr])],
        "## Pairwise difficulty (Bradley-Terry)", "",
        f"- {report['bt']}",
        "- Pairs are sampled within the primary category (half random, half |Δ teacher diff| ≤ 2). Codex judges each pair in",
        "  both presentation orders in different batches. BT is fitted by penalised gradient ascent (ties = half wins).",
        "- Calibration: per category, a monotone quantile map sends the i-th ranked BT score to the i-th ranked teacher mean",
        "  difficulty of the same tasks (so the marginal matches the teachers, the ordering follows the pairwise judgments).",
        f"- Final `labels.difficulty` for BT-scored tasks = 0.5 × teacher soft label + 0.5 × Gaussian(σ=0.6) at the calibrated value.",
        "  Raw values are kept in `meta.difficulty_teacher_mean`, `meta.difficulty_bt.{score,calibrated}`;",
        "  all scores in `data/cache/pairwise/bt_scores.json`.",
        "",
        "## Minimal pairs", "",
        "Edits: " + ", ".join(f"{k} {v}" for k, v in sorted(edits.items())), "",
        "Fraction where the merged teacher label of the edited task moved as expected vs its original:", "",
        "| edit: expected delta | ok |", "|---|---|", *[f"| {k} | {v} |" for k, v in pair_checks(by_id).items()], "",
        "## Throughput and teacher calls", "",
        "| teacher/purpose | calls | ok | mean secs (ok) |", "|---|---|---|---|",
        *[f"| {k} | {v['calls']} | {v['ok']} | {v['mean_secs_ok']} |" for k, v in tp.items() if not k.startswith("_")], "",
        f"- Total calls {tp.get('_total_calls')}, failed {tp.get('_failed_calls')}, wall clock first→last call {tp.get('_wall_clock_hours_first_to_last_call')} h",
        "- Batch sizes: generation 20 tasks/call, labelling 15 tasks/call (Ollama 4), pairwise 40 judgments/call, minimal pairs 20 edits/call.",
        "",
        "## Label construction", "",
        "- Soft labels: each teacher's point answer → discretised Gaussian (σ=0.6 levels) for difficulty and every skill axis,",
        "  averaged over teachers; category = mean of teacher distributions (primary 1.0, or 0.75/0.25 with a secondary);",
        "  flags/checklist = mean of 0/1 answers; out_tokens_log10 = mean of log10 estimates.",
        "- Ollama is added as an equal third teacher only where codex and kimi strongly disagree.",
        "- `meta.agreement` = mean over (primary-category match, 1-|Δdiff|/9, 1-mean|Δskill|/10, matching flag+checklist bits) for codex vs kimi.",
        "- Gold exclusion: real records with int(sha1(id),16) % 10 == 0 (instance_id / conversation_hash) are never used.",
        "",
    ]
    if KNOWN_ISSUES_FILE.exists():
        md += ["## Known issues", "", KNOWN_ISSUES_FILE.read_text().strip(), ""]
    (paths.DATA / "STATS.md").write_text("\n".join(md))
