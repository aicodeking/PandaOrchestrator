"""End-to-end orchestration: label -> tie-break -> pairwise BT -> merge -> dedup/split -> validate -> stats."""

import asyncio
import json

from . import label as L
from . import merge, pairwise, paths
from .jsonio import read_jsonl, write_jsonl

TEACHERS = ("codex", "kimi", "grok", "deepseek")  # full-label teacher families; any >= 2 make a record
DEFAULT_LABELLERS = ("codex", "grok")
BT_WEIGHT = 0.5  # weight of the calibrated BT point in the final difficulty soft label


def load_pool(include_pairs: bool = True) -> tuple[list[dict], list[dict]]:
    originals, seen = [], set()
    for name in ("real.jsonl", "synthetic.jsonl"):
        for r in read_jsonl(paths.POOL / name):
            if r["id"] not in seen:
                seen.add(r["id"])
                originals.append(r)
    pairs = []
    if include_pairs:
        ids = {r["id"] for r in originals}
        pseen = set()
        for r in read_jsonl(paths.POOL / "minimal_pairs.jsonl"):
            if r["pair_of"] in ids and r["id"] not in pseen:
                pseen.add(r["id"])
                pairs.append(r)
    return originals, pairs


async def label_all(tasks: list[dict], seed: int = 0, teachers_=DEFAULT_LABELLERS) -> None:
    await asyncio.gather(*(L.label(tasks, t, seed) for t in teachers_))


def _dispute(answers: list[dict]) -> float:
    return max(abs(x["diff"] - y["diff"]) + 3 * (x["cat"] != y["cat"]) for i, x in enumerate(answers) for y in answers[i + 1:])


def _disputed(answers: list[dict]) -> bool:
    return any(L.strong_disagreement(x, y) for i, x in enumerate(answers) for y in answers[i + 1:])


async def tiebreak(tasks: list[dict], limit: int | None = None) -> int:
    """Ollama third opinion (category + difficulty) where full-label teachers strongly disagree, most-disputed first."""
    ans = load_all_answers()
    need = []
    for t in tasks:
        full = [ans[n][t["id"]] for n in TEACHERS if t["id"] in ans.get(n, {})]
        if len(full) >= 2 and _disputed(full):
            need.append((t, _dispute(full)))
    need = [t for t, _ in sorted(need, key=lambda x: -x[1])]
    need = need[:limit] if limit else need
    if need:
        await L.tiebreak(need)
    return len(need)


def answers_for(tid: str, ans: dict[str, dict[str, dict]]) -> tuple[list[str], list[dict], list[dict]]:
    """(teacher names, full answers from codex/kimi/grok, partial Ollama tie-break answers)."""
    names = [t for t in TEACHERS if tid in ans.get(t, {})]
    out = [ans[t][tid] for t in names]
    extra = []
    if len(out) >= 2 and _disputed(out) and tid in ans.get("ollama", {}):
        names.append("ollama")
        extra.append(ans["ollama"][tid])
    return names, out, extra


def load_all_answers() -> dict[str, dict[str, dict]]:
    return {t: L.load_answers(t) for t in (*TEACHERS, "ollama")}


def teacher_mean_diff(answers: list[dict]) -> float:
    return sum(a["diff"] for a in answers) / len(answers)


async def run_pairwise(originals: list[dict], n_pairs: int, seed: int = 0) -> None:
    ans = load_all_answers()
    items = []
    for r in originals:
        names, a, extra = answers_for(r["id"], ans)
        if len(a) >= 2:
            cat = max(merge.category_dist(a + extra).items(), key=lambda kv: kv[1])[0]
            items.append({"id": r["id"], "category": cat, "diff_mean": teacher_mean_diff(a + extra)})
    pairs = pairwise.sample_pairs(items, n_pairs, seed)
    texts = {r["id"]: r["task"]["text"] for r in originals}
    await pairwise.judge(pairs, texts, seed)


def bt_calibration(records_answers: dict[str, list[dict]]) -> tuple[dict[str, float], dict[str, float], dict]:
    js = [j for j in read_jsonl(pairwise.OUT) if j["a"] in records_answers and j["b"] in records_answers]
    if not js:
        return {}, {}, {"judgments": 0}
    scores = pairwise.fit_bt(js)
    tmean = {k: teacher_mean_diff(records_answers[k]) for k in scores}
    cats = {k: max(merge.category_dist(records_answers[k]).items(), key=lambda kv: kv[1])[0] for k in scores}
    cal = pairwise.calibrate(scores, tmean, cats)
    pairwise.dump_scores(paths.PAIRWISE / "bt_scores.json", scores, cal, tmean)
    rep = pairwise.consistency(js)
    rep["tasks_with_bt"] = len(scores)
    try:
        from scipy.stats import spearmanr
        ks = list(scores)
        rep["spearman_bt_vs_teacher"] = round(float(spearmanr([scores[k] for k in ks], [tmean[k] for k in ks])[0]), 4)
    except Exception:  # noqa: BLE001
        pass
    return scores, cal, rep


def assemble(originals: list[dict], pairs: list[dict], single_teacher_pairs: bool = False) -> tuple[list[dict], list[dict], dict]:
    """Originals need >= 2 full-label teachers. With `single_teacher_pairs`, minimal pairs labelled
    by only one teacher are kept too (meta.single_teacher=true, meta.agreement=null)."""
    ans = load_all_answers()
    report = {"missing_teacher": 0, "single_teacher_pairs": 0}
    per_task = {}
    pair_ids = {r["id"] for r in pairs}
    for r in originals + pairs:
        names, a, extra = answers_for(r["id"], ans)
        if len(a) >= 2 or (single_teacher_pairs and len(a) == 1 and r["id"] in pair_ids):
            per_task[r["id"]] = (names, a, extra)
            report["single_teacher_pairs"] += len(a) == 1
        else:
            report["missing_teacher"] += 1
    bt_scores, bt_cal, bt_rep = bt_calibration({k: v[1] + v[2] for k, v in per_task.items() if not k.startswith("mp-")})
    report["bt"] = bt_rep

    def build(r):
        names, a, extra = per_task[r["id"]]
        cd = a + extra  # answers that carry category + difficulty
        override = None
        meta = dict(r.get("meta") or {})
        meta["teachers"] = names
        meta["agreement"] = merge.agreement(a) if len(a) >= 2 else None
        if len(a) == 1:
            meta["single_teacher"] = True
        meta["difficulty_teacher_mean"] = round(teacher_mean_diff(cd), 3)
        meta["teacher_points"] = {n: {"cat": x["cat"], "cat2": x["cat2"], "diff": x["diff"]} for n, x in zip(names, cd)}
        if r["id"] in bt_cal:
            teacher_dist = merge.smooth_points([x["diff"] for x in cd], 1, 10)
            bt_dist = merge.gaussian_dist(bt_cal[r["id"]], 1, 10)
            override = [(1 - BT_WEIGHT) * t + BT_WEIGHT * b for t, b in zip(teacher_dist, bt_dist)]
            meta["difficulty_bt"] = {"score": round(bt_scores[r["id"]], 4), "calibrated": bt_cal[r["id"]]}
        return {"id": r["id"], "source": r["source"], "pair_of": r.get("pair_of"), "task": r["task"],
                "labels": merge.merge(a, override, extra), "meta": meta}

    out_o = [build(r) for r in originals if r["id"] in per_task]
    ok_ids = {r["id"] for r in out_o}
    out_p = [build(r) for r in pairs if r["id"] in per_task and r["pair_of"] in ok_ids]
    return out_o, out_p, report


def finalize(seed: int = 0, single_teacher_pairs: bool = False) -> dict:
    from . import dedup_split, stats, validate

    originals, pairs = load_pool()
    recs_o, recs_p, rep = assemble(originals, pairs, single_teacher_pairs)
    splits, drep = dedup_split.run(recs_o, recs_p, seed=seed)
    rep["dedup"] = drep
    for s, rows in splits.items():
        rows.sort(key=lambda r: r["id"])
        write_jsonl(paths.DATA / f"{s}.jsonl", rows)
    vrep = validate.validate_splits(paths.DATA)
    rep["validation"] = {s: {"n": v["n"], "errors": len(v["errors"])} for s, v in vrep.items()}
    (paths.CACHE / "build_report.json").write_text(json.dumps(rep, indent=1))
    stats.write_stats(splits, rep)
    return rep
