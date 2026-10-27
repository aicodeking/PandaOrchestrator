#!/usr/bin/env python
"""Underspecified-request dataset (vague-v4): short request + spelled-out twin, dual-teacher labelled.

  .venv/bin/python scripts/datagen/vague_v4.py gen [--calls N]      # pairs -> data/vague_v4/pairs.jsonl
  .venv/bin/python scripts/datagen/vague_v4.py label [--teachers codex,deepseek]
  .venv/bin/python scripts/datagen/vague_v4.py build                # merge, split, validate, STATS.md
All stages resume (teacher calls cached in data/cache/calls; labels in data/vague_v4/labels/).
"""
import argparse
import asyncio
import collections
import json
import random
import re
import sys
import time
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT))

from panda_router.datagen import label as L  # noqa: E402
from panda_router.datagen import merge, teachers, validate  # noqa: E402
from panda_router.datagen.common import norm_context, sha_int, short_hash  # noqa: E402
from panda_router.datagen.jsonio import append_jsonl, read_jsonl, write_jsonl  # noqa: E402

OUT = ROOT / "data" / "vague_v4"
LABELS = OUT / "labels"
RUBRIC = ("The task will be executed by an autonomous coding/agent model inside a real project. Rate difficulty for the work "
          "most plausibly intended; if the request is underspecified, rate the expected scope and set ambiguous_spec high, "
          "unless the request is clearly trivial. If you are uncertain between two difficulty levels, choose the higher one; "
          "under-estimating is worse than over-estimating. Clearly trivial tasks (tiny, fully specified) must still be rated honestly low.")
CATS = ["implementation", "bugfix", "refactor", "test_writing", "devops_infra", "data_analysis", "ui_frontend",
        "planning", "docs_writing", "research", "code_review", "math_reasoning"]
SCOPES = {"small": "an hour or less of work (one function or file)", "medium": "half a day (a feature touching a few files)",
          "large": "several days (a subsystem, multi-component, needs design decisions)",
          "very_large": "weeks (a platform, a research-grade or distributed system, a large migration)"}
TRIVIAL_CATS = ["refactor", "implementation", "bugfix", "docs_writing", "chat_simple", "math_reasoning", "devops_infra", "data_analysis"]
FLAVOURS = ["web backend", "ML/AI", "mobile app", "data pipeline", "CLI tooling", "game dev", "embedded/IoT", "fintech", "e-commerce",
            "devtools", "security", "scientific computing", "frontend SPA", "infra/SRE", "databases", "browser extension",
            "desktop app", "bots/automation", "healthcare software", "education software"]
GEN = """You write test data for a router that estimates how hard a request is for an autonomous coding agent working inside a real project.
Produce {n} PAIRS. Each pair: "short" = a terse or underspecified request exactly as a busy human might type it to an orchestrator
({short_rule}), and "full" = the SAME request spelled out with the concrete requirements, stack, constraints and acceptance criteria that
the author most plausibly intended ({full_rule}). Both must describe the same job.
Category: {cat}. True intended scope: {scope}. Flavour/domain hint: {flavour}.
{extra}
Style examples of short requests: "a model trainer", "auth", "make the dashboard faster", "fix the tests", "migrate to postgres",
"add payments", "k8s setup", "scraper for prices", "train a model". Be varied; do not copy these. No two shorts may share a first word pattern.
"ctx" = a context object for the FULL version: {{"repo_languages": [..], "files_in_scope": int, "estimated_input_tokens": int, "has_images": false, "requires_tools": bool}}.
Answer ONLY with JSON: {{"pairs": [{{"short": "...", "full": "...", "ctx": {{...}}}}, ...]}}. Do not use tools or read files."""
VAGUE = dict(short_rule="1-8 words, missing most details", full_rule="40-120 words, specific",
             extra="The short request should NOT look trivial by wording alone; the real job is of the stated scope.")
TRIV = dict(short_rule="2-10 words, but genuinely trivial and fully specified (e.g. 'rename foo to bar in utils.py', \"what's 2^10\", 'HTTP 418?', 'add a newline at EOF of main.go', 'git undo last commit')",
            full_rule="20-50 words, same trivial job with the exact file/value/command",
            extra="True intended scope: TRIVIAL (under 5 minutes). Short does not mean hard here: the short request is clear and tiny.")


SONNET = "claude-sonnet"
_orig_raw = teachers._raw_call


async def _raw(teacher, prompt):
    if teacher != SONNET:
        return await _orig_raw(teacher, prompt)
    code, out, err = await teachers._run_cli(["claude", "-p", "--model", "sonnet", "--output-format", "json", prompt])
    if code != 0 or not out.strip():
        low = (out + err).lower()
        raise teachers.TeacherError(f"{'ratelimit' if any(h in low for h in teachers._RATE_HINTS) else 'exit'}:{code}:{(err or out).strip()[-300:]}")
    try:
        env = json.loads(out)
    except json.JSONDecodeError:
        return out
    if env.get("is_error"):
        raise teachers.TeacherError(f"claude:{str(env.get('result'))[:200]}")
    return env.get("result") or ""


teachers._raw_call = _raw
teachers.CONCURRENCY[SONNET] = 7
L.BATCH[SONNET] = 15


def norm(t: str) -> str:
    return re.sub(r"[^a-z0-9]+", " ", t.lower()).strip()


def known_texts() -> set[str]:
    s = set()
    for f in [*(ROOT / "data").glob("*.jsonl"), *(ROOT / "data" / "gold").glob("*.jsonl")]:
        for r in read_jsonl(f):
            t = r.get("task") if isinstance(r.get("task"), dict) else r
            if isinstance(t, dict) and isinstance(t.get("text"), str):
                s.add(norm(t["text"]))
    return s


def _gen_parser(obj):
    ps = obj.get("pairs") if isinstance(obj, dict) else None
    ok = [p for p in ps or [] if isinstance(p.get("short"), str) and isinstance(p.get("full"), str) and p["short"].strip() and len(p["full"].split()) >= 12]
    if len(ok) < 5:
        raise ValueError("too few pairs")
    return ok


def gen_jobs(calls: int, seed=0):
    rng = random.Random(seed)
    jobs = []
    cells = [(c, s) for c in CATS for s in SCOPES]
    for i in range(calls):
        if i % 4 == 3:  # ~25% of calls are trivial -> ~200+ of 800 pairs
            cat, scope, kw = rng.choice(TRIVIAL_CATS), "trivial", TRIV
        else:
            cat, scope = cells[(i - i // 4) % len(cells)]
            kw = VAGUE
        n = 12
        p = GEN.format(n=n, cat=cat, scope=scope if scope == "trivial" else f"{scope} - {SCOPES[scope]}", flavour=rng.choice(FLAVOURS), **kw)
        jobs.append((cat, scope, p + f"\n(batch tag {i})"))
    return jobs


async def gen(calls: int):
    OUT.mkdir(exist_ok=True)
    jobs = gen_jobs(calls)
    names = ["codex"]
    print(f"[gen] {len(jobs)} calls, generators {names}", flush=True)
    rows, seen = read_jsonl(OUT / "pairs_raw.jsonl"), set()
    done = {r["job"] for r in rows}

    async def one(i, cat, scope, p):
        if i in done:
            return
        t = names[i % len(names)]
        ps = await teachers.call(t, p, _gen_parser, purpose="vague-gen")
        append_jsonl(OUT / "pairs_raw.jsonl", [{"job": i, "gen": t, "cat": cat, "scope": scope, "pair": q} for q in ps])
        print(f"[gen] job {i} {t} {scope}/{cat} +{len(ps)}", flush=True)

    await teachers.gather_limited([one(i, *j) for i, j in enumerate(jobs)])
    finish_pairs()


def finish_pairs():
    known, seen, pairs = known_texts(), set(), []
    for r in read_jsonl(OUT / "pairs_raw.jsonl"):
        s, f = r["pair"]["short"].strip(), r["pair"]["full"].strip()
        ns, nf = norm(s), norm(f)
        if not ns or ns in known or nf in known or ns in seen or nf in seen or ns == nf:
            continue
        seen |= {ns, nf}
        pid = "vg" + short_hash(ns)
        pairs.append({"pid": pid, "scope": r["scope"], "cat": r["cat"], "gen": r["gen"], "short": s, "full": f,
                      "ctx": norm_context(r["pair"].get("ctx"))})
    rng = random.Random(0)
    triv = [p for p in pairs if p["scope"] == "trivial"]
    vague = [p for p in pairs if p["scope"] != "trivial"]
    rng.shuffle(triv), rng.shuffle(vague)
    pairs = triv[:200] + vague[:600]
    write_jsonl(OUT / "pairs.jsonl", pairs)
    print(f"[gen] pairs kept {len(pairs)} (trivial {len(triv[:200])}, vague {len(vague[:600])})", flush=True)


def tasks_of(pairs):
    for p in pairs:
        ctx_full = p["ctx"]
        ctx_short = {"repo_languages": ctx_full["repo_languages"]} if ctx_full.get("repo_languages") and sha_int(p["pid"]) % 3 == 0 else {}
        yield {"id": p["pid"] + "-s", "task": {"text": p["short"], "context": ctx_short}}
        yield {"id": p["pid"] + "-f", "task": {"text": p["full"], "context": ctx_full}}


def build_prompt(items):
    return L.build_prompt(items).replace("\nANCHOR EXAMPLES", "\n" + RUBRIC + "\n\nANCHOR EXAMPLES", 1)


async def label_batch(teacher, batch):
    lids = [f"t{i:02d}" for i in range(len(batch))]
    got = await teachers.call(teacher, build_prompt(list(zip(lids, [r["task"] for r in batch]))), L._parser(lids), purpose="vague-label")
    append_jsonl(LABELS / f"{teacher}.jsonl", [{"id": r["id"], "teacher": teacher, "ans": got[l]} for l, r in zip(lids, batch) if l in got])
    print(f"[label] {teacher} +{len(got)}/{len(batch)}", flush=True)


async def label(names):
    tasks = list(tasks_of(read_jsonl(OUT / "pairs.jsonl")))
    teachers.CONCURRENCY.update(codex=10)

    async def one(t):
        for _ in range(2):
            have = {r["id"] for r in read_jsonl(LABELS / f"{t}.jsonl")}
            todo = sorted((x for x in tasks if x["id"] not in have), key=lambda x: sha_int(f"{t}|{x['id']}"))
            if not todo:
                return
            print(f"[label] {t}: {len(todo)} todo", flush=True)
            bs = L.BATCH[t]
            await teachers.gather_limited([label_batch(t, todo[i:i + bs]) for i in range(0, len(todo), bs)])

    await asyncio.gather(*(one(t) for t in names))


def load(t):
    return {r["id"]: r["ans"] for r in read_jsonl(LABELS / f"{t}.jsonl")}


def build():
    pairs = read_jsonl(OUT / "pairs.jsonl")
    ans = {t: load(t) for t in ("codex", SONNET)}
    recs, by_pair = [], {}
    for p in pairs:
        for tid, text_ctx, kind in ((p["pid"] + "-s", None, "short"), (p["pid"] + "-f", None, "full")):
            if all(tid in ans[t] for t in ans):
                by_pair.setdefault(p["pid"], []).append((tid, kind))
    tmap = {t["id"]: t["task"] for t in tasks_of(pairs)}
    meta_of = {p["pid"]: p for p in pairs}
    keep = [pid for pid, v in by_pair.items() if len(v) == 2]
    split_of = {pid: ("val" if sha_int("vsplit|" + pid) % 10 == 0 else "train") for pid in keep}
    out = {"train": [], "val": []}
    for pid in keep:
        p = meta_of[pid]
        for tid, kind in by_pair[pid]:
            a = [ans[t][tid] for t in ("codex", SONNET)]
            other = pid + ("-f" if kind == "short" else "-s")
            names = ["codex", SONNET]
            meta = {"pair_id": pid, "variant": kind, "scope": p["scope"], "gen_category": p["cat"], "teachers": names,
                    "agreement": merge.agreement(a), "difficulty_teacher_mean": round(sum(x["diff"] for x in a) / 2, 3),
                    "teacher_points": {n: {"cat": x["cat"], "cat2": x["cat2"], "diff": x["diff"]} for n, x in zip(names, a)},
                    "ambiguous_spec_teachers": [x["flags"]["ambiguous_spec"] for x in a]}
            out[split_of[pid]].append({"id": "vague-" + tid, "source": "vague-v4", "pair_of": "vague-" + other, "task": tmap[tid],
                                       "labels": merge.merge(a), "meta": meta})
    for s, rows in out.items():
        rows.sort(key=lambda r: r["id"])
        write_jsonl(OUT / f"{s}.jsonl", rows)
    errs = check(OUT)
    write_stats(out, pairs, len(keep), errs)
    print(f"[build] train {len(out['train'])} val {len(out['val'])} validation errors {len(errs)}")


def check(d):
    """Run the stock validator; it predates source 'vague-v4', so allow it and its pair_of links."""
    validate.SOURCES.add("vague-v4")
    errs = []
    for s in ("train", "val"):
        n, e = validate.validate_file(Path(d) / f"{s}.jsonl")
        errs += [x for x in e if "pair_of must be null" not in x]
    return errs


def hist(vals):
    c = collections.Counter(vals)
    return " ".join(f"{k}:{c.get(k, 0)}" for k in range(1, 11))


def write_stats(out, pairs, npairs, errs):
    rows = out["train"] + out["val"]
    pt = lambda r: r["meta"]["difficulty_teacher_mean"]  # noqa: E731
    exp = lambda r: sum((i + 1) * x for i, x in enumerate(r["labels"]["difficulty"]))  # noqa: E731
    L_ = [f"# vague-v4 stats\n", f"- pairs: {npairs} (of {len(pairs)} generated); records: train {len(out['train'])}, val {len(out['val'])}",
          f"- validator errors: {len(errs)} (validate.py extended at runtime with source 'vague-v4')"]
    ag = [r["meta"]["agreement"] for r in rows]
    dd = [abs(r["meta"]["teacher_points"]["codex"]["diff"] - r["meta"]["teacher_points"][SONNET]["diff"]) for r in rows]
    if rows:
        L_ += [f"- teacher agreement mean {sum(ag)/len(ag):.3f}; |Δdiff| mean {sum(dd)/len(dd):.2f}, ≥3: {sum(d >= 3 for d in dd)}"]
    L_ += ["\n## Difficulty histogram (rounded teacher-mean, bins 1-10)"]
    for sc in ["trivial", "small", "medium", "large", "very_large"]:
        for v in ("short", "full"):
            sel = [r for r in rows if r["meta"]["scope"] == sc and r["meta"]["variant"] == v]
            if sel:
                L_.append(f"- {sc:10s} {v:5s} n={len(sel):3d} mean={sum(map(pt, sel))/len(sel):.2f} | {hist([max(1, min(10, round(pt(r)))) for r in sel])}")
    for v in ("short", "full"):
        sel = [r for r in rows if r["meta"]["variant"] == v and r["meta"]["scope"] != "trivial"]
        if sel:
            L_.append(f"- ALL non-trivial {v}: mean {sum(map(pt, sel))/len(sel):.2f} | {hist([max(1, min(10, round(pt(r)))) for r in sel])}")
    sh = [r for r in rows if r["meta"]["variant"] == "short" and r["meta"]["scope"] != "trivial"]
    if sh:
        L_.append(f"- ambiguous_spec mean (non-trivial short): {sum(r['labels']['flags']['ambiguous_spec'] for r in sh)/len(sh):.2f}")
    L_ += ["\n## Counts", "- by scope: " + str(dict(collections.Counter(p["scope"] for p in pairs))),
           "- by generator: " + str(dict(collections.Counter(p["gen"] for p in pairs)))]
    L_ += ["\n## Examples (short -> full, teacher-mean difficulty)"]
    rng = random.Random(1)
    byp = collections.defaultdict(dict)
    for r in rows:
        byp[r["meta"]["pair_id"]][r["meta"]["variant"]] = r
    for pid in rng.sample(sorted(byp), min(14, len(byp))):
        s, f = byp[pid]["short"], byp[pid]["full"]
        L_.append(f"- [{s['meta']['scope']}] \"{s['task']['text']}\" {pt(s):.1f} -> \"{f['task']['text'][:140]}...\" {pt(f):.1f}")
    (OUT / "STATS.md").write_text("\n".join(L_) + "\n")


def main():
    ap = argparse.ArgumentParser()
    sub = ap.add_subparsers(dest="cmd", required=True)
    g = sub.add_parser("gen")
    g.add_argument("--calls", type=int, default=96)
    lb = sub.add_parser("label")
    lb.add_argument("--teachers", default="codex,claude-sonnet")
    sub.add_parser("build")
    sub.add_parser("pairs")
    a = ap.parse_args()
    if a.cmd == "gen":
        asyncio.run(gen(a.calls))
    elif a.cmd == "pairs":
        finish_pairs()
    elif a.cmd == "label":
        asyncio.run(label(a.teachers.split(",")))
    else:
        build()


if __name__ == "__main__":
    main()
