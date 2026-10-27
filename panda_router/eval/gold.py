"""Held-out GOLD set: candidate selection, three-teacher labelling and soft-label merge.

GOLD PARTITION RULE: a raw record belongs to the gold partition iff
int(sha1(id).hexdigest(), 16) % 10 == 0, with id = instance_id (SWE-rebench, SWE-smith) or
conversation_hash (WildChat). The synthetic/training builder excludes exactly these records.

Label prompt, answer cleaning and soft-label merge are imported from panda_router.datagen so gold
labels use the same definitions as the training labels. Teacher calls and their raw answers are
cached under data/gold/cache/ (never shared with the training cache).
"""

from __future__ import annotations

import asyncio
import hashlib
import json
import os
import random
import re
import time
import urllib.request
from collections import Counter
from pathlib import Path

import numpy as np

ROOT = Path(__file__).resolve().parent.parent.parent
GOLD = ROOT / "data" / "gold"
RAW = GOLD / "raw"
CACHE = GOLD / "cache"
CANDIDATES = GOLD / "candidates.jsonl"
ANSWERS = GOLD / "teacher_answers.jsonl"
GOLD_PATH = GOLD / "gold.jsonl"

TEACHERS = ("codex", "grok", "kimi", "ollama", "deepseek")
EXTRA_TEACHERS = ("ollama",)  # answers kept in meta.teacher_answers but not merged into the soft labels
BATCH = 5
CODEX_MODEL = os.environ.get("PANDA_CODEX_MODEL", "gpt-5.6-luna")
OLLAMA_MODEL = os.environ.get("PANDA_OLLAMA_MODEL", "gemma4:26b")
GROK_MODEL = os.environ.get("PANDA_GROK_MODEL", "grok-4.7-build-fast")
DEEPSEEK_MODEL = os.environ.get("PANDA_DEEPSEEK_MODEL", "deepseek/deepseek-v4.1-flash")  # OpenRouter direct API
OLLAMA_URL = os.environ.get("PANDA_OLLAMA_URL", "http://localhost:11434/api/generate")
TIMEOUT_S = int(os.environ.get("PANDA_TEACHER_TIMEOUT", "1500"))
# gemma4 thinks by default (~3000 thinking tokens per batch at ~26 tok/s); thinking is disabled so the shared
# local GPU can finish 70+ batches. Earlier thinking-mode answers are kept in the file but ignored.
MODEL_TAG = {"codex": CODEX_MODEL, "kimi": "kimi-cli", "ollama": f"{OLLAMA_MODEL}/no-think", "grok": GROK_MODEL,
           "deepseek": DEEPSEEK_MODEL}
CONCURRENCY = {"codex": int(os.environ.get("GOLD_CODEX_CONC", "4")),
               "kimi": int(os.environ.get("GOLD_KIMI_CONC", "4")),
               "ollama": int(os.environ.get("GOLD_OLLAMA_CONC", "1")),
               "grok": int(os.environ.get("GOLD_GROK_CONC", "4")),
               "deepseek": int(os.environ.get("GOLD_DEEPSEEK_CONC", "3"))}

CAREFUL = ("Think carefully about every task before answering. These labels form a held-out GOLD evaluation set "
           "of real tasks, so accuracy matters far more than speed: read each task fully, consider what a competent "
           "assistant would actually have to do, and calibrate difficulty against the anchors.\n\n")


def sha_int(s: str) -> int:
    return int(hashlib.sha1(s.encode()).hexdigest(), 16)


def is_gold(raw_id: str) -> bool:
    return sha_int(raw_id) % 10 == 0


def short_hash(s: str, n: int = 10) -> str:
    return hashlib.sha1(s.encode()).hexdigest()[:n]


def read_jsonl(path) -> list[dict]:
    path = Path(path)
    if not path.exists():
        return []
    out = []
    for line in path.read_text().splitlines():
        if line.strip():
            try:
                out.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    return out


def write_jsonl(path, rows) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")
    tmp.replace(path)


def append_jsonl(path, rows) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("a") as f:
        for r in rows:
            f.write(json.dumps(r, ensure_ascii=False) + "\n")


# --------------------------------------------------------------------------- selection
MAX_TEXT = 5000

_CODE = r"(```|\bdef \w|\bfunction\b|\bclass \w|#include|public static|=>|\bimport \w|\bconst \w|\bSELECT\b|;\s*\n|\{\s*\n)"
_EXCLUDE = re.compile(r"\btranslat|\brephrase|\bparaphras|\bpolished\b|\bpok[eé]|\bact as\b|\bact like\b|\bfanfic|"
                      r"\bwrite (a|an) (story|poem|song|rap|script for a)|\bcharacter\b|\bmidjourney|\bprompt\b", re.I)

_BUCKETS: list[tuple[str, re.Pattern, re.Pattern | None]] = [(k, re.compile(v, re.I), re.compile(c, re.I) if c else None)
                                                              for k, v, c in [
    ("test_writing", r"\bunit tests?\b|\bwrite (some )?tests\b|\bpytest\b|\bjunit\b|\btest cases?\b|\bjest\b|\bmock", None),
    ("code_review", r"\breview\b|\bcritique\b|\bfeedback\b|\bwhat'?s wrong\b|\bimprove (my|this|the) code\b|"
                    r"\b(issues|problems|mistakes) (with|in)\b|\bbest practices?\b|\bis this (code )?(correct|good|ok)", _CODE),
    ("refactor", r"\brefactor|\bclean (up )?(my|this|the) code\b|\brewrite (this|the|my) (code|function|class|script)\b|"
                 r"\bmake (this|my|the) code (more )?(readable|cleaner|efficient|faster|pythonic)\b|\bsimplify\b|\boptimi[sz]e (this|my|the) code", _CODE),
    ("devops_infra", r"\bdocker|\bkubernetes|\bk8s\b|\bnginx\b|\bdeploy|\bci/cd\b|\bgithub actions\b|\bterraform\b|"
                     r"\bansible\b|\baws\b|\bazure\b|\bgcp\b|\bsystemd\b|\bjenkins\b|\bcron\b|\bapache server\b", None),
    ("ui_frontend", r"\bhtml\b|\bcss\b|\breact\b|\bvue\b|\bangular\b|\bfrontend\b|\btailwind\b|\bweb ?page\b|"
                    r"\bbutton\b|\bnavbar\b|\bflexbox\b|\bui\b|\bwebsite\b|\bjavascript\b|\bwpf\b|\btkinter\b|\bswiftui\b", None),
    ("data_analysis", r"\bpandas\b|\bdataframe\b|\bcsv\b|\bsql\b|\bexcel\b|\bdataset\b|\bmatplotlib\b|\bregression\b|"
                      r"\bstatistic|\bpivot\b|\bspreadsheet\b|\bvba\b|\bnumpy\b|\bhistogram\b|\bcorrelation\b|\bmean and\b", None),
    ("math_reasoning", r"\bprove\b|\bproof\b|\bintegral\b|\bderivative\b|\bequation\b|\bprobability\b|\btheorem\b|"
                       r"\bsolve for\b|\bcalculate\b.*\d|\bhow many ways\b|\bbig[- ]o\b|\bpolynomial\b|\bprime\b|\bx\^2\b", None),
    ("planning", r"\bplan\b|\broadmap\b|\bmilestones?\b|\bstep[- ]by[- ]step (plan|guide)\b|\bdesign a system\b|"
                 r"\barchitecture\b|\bbusiness plan\b|\bproject plan\b|\bhow (should|do) i (structure|organi[sz]e|approach)\b|\bstrategy for\b", None),
    ("docs_writing", r"\bdocumentation\b|\breadme\b|\bdocstring|\bcomments? (to|for) (this|my|the) code\b|\buser (guide|manual)\b|"
                     r"\bwrite (a|an|the) (report|article|blog post|summary|email|proposal|description|abstract|introduction|tutorial)\b|"
                     r"\btechnical (report|writing|document)\b|\bchangelog\b", None),
    ("research", r"\bcompare\b|\bdifference between\b|\bpros and cons\b|\bwhich is better\b|\bwhat are the best\b|"
                 r"\bliterature\b|\bresearch\b|\bsources\b|\badvantages and disadvantages\b|\bstate of the art\b|"
                 r"\balternatives? to\b|\bvs\.?\b|\blatest\b|\bfind (me )?(information|papers|studies)\b", None),
    ("bugfix", r"\berror\b|\btraceback\b|\bexception\b|\bnot working\b|\bdoesn'?t work\b|\bbug\b|\bfix\b|\bcrash|\bwarning:", None),
    ("implementation", r"\bwrite (a|an|me a|me an|the) (python|java|c\+\+|c#|javascript|program|function|script|class|code|method|bot|api)\b|"
                       r"\bimplement\b|\bcreate (a|an) (program|function|script|app|bot|class|api|game|tool)\b|\bcode (for|to|that)\b|"
                       r"\bin (python|java|c\+\+|c#|javascript|rust|go|kotlin|php)\b", None),
    ("chat_simple", r"^(what|who|when|where|why|how|explain|define|tell me|is|are|can|does|give me)\b", None),
]]


def wildchat_bucket(text: str) -> str | None:
    if _EXCLUDE.search(text):
        return None
    for name, rx, need in _BUCKETS:
        if rx.search(text) and (need is None or need.search(text)):
            if name == "chat_simple" and len(text) > 300:
                continue
            return name
    return None


_USER_PATH = re.compile(r"(?i)([A-Z]:[\\/]+(?:Users|Documents and Settings)[\\/]+|/(?:Users|home)/)([^\\/\s\"'`]+)")


def scrub(text: str, aggressive: bool = False) -> str:
    """datagen PII scrub (emails, keys, IPs, phones) + user names inside home-directory paths."""
    from ..datagen.real import scrub_pii

    return _USER_PATH.sub(r"\1<user>", scrub_pii(text, aggressive=aggressive))


def _clip(text: str) -> str:
    text = text.strip()
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT - 300] + "\n[...truncated...]\n" + text[-250:]
    return text


def _has_images(text: str) -> bool:
    return bool(re.search(r"!\[[^\]]*\]\(|\.(png|jpe?g|gif|webp)\b|screenshot", text, re.I))


def refresh_contexts() -> int:
    """Rewrite SWE candidates' task.context from the issue text only (idempotent; labels are keyed by id)."""
    from ..datagen.real import issue_body, issue_context

    rows = read_jsonl(CANDIDATES)
    for r in rows:
        if r["source"] != "wildchat":
            r["task"]["context"] = issue_context(issue_body(r["task"]["text"]), r["meta"].get("repo"))
    write_jsonl(CANDIDATES, rows)
    return sum(r["source"] != "wildchat" for r in rows)


def _swe_example(prefix: str, source: str, r: dict, extra_meta: dict | None = None) -> dict:
    from ..datagen.real import issue_context

    text = _clip(scrub(r["problem_statement"]))
    return {
        "id": f"gold-{prefix}-{short_hash(r['instance_id'])}", "source": source, "pair_of": None,
        "task": {"text": f"Repository: {r['repo']}\n\n{text}", "context": issue_context(text, r["repo"])},
        "meta": {"raw_id": r["instance_id"], "repo": r["repo"], **(extra_meta or {})},
    }


def _outcome_instances() -> set[str]:
    import pyarrow.parquet as pq

    ids: set[str] = set()
    for p in (RAW / "openhands-traj" / "outcomes.parquet", RAW / "swe-agent-traj" / "outcomes.parquet"):
        if p.exists():
            ids |= set(pq.read_table(p, columns=["instance_id"]).column(0).to_pylist())
    return ids


def select_swe_rebench(n: int, rng: random.Random) -> list[dict]:
    """Gold-partition SWE-rebench instances; instances with published outcome data come first (anchors)."""
    import pyarrow.parquet as pq

    cols = ["instance_id", "repo", "problem_statement", "license_name", "meta"]
    rows = []
    for p in sorted((RAW / "swe-rebench" / "data").glob("test-*.parquet")):
        rows += pq.read_table(p, columns=cols).to_pylist()
    rows = [r for r in rows if is_gold(r["instance_id"]) and 80 <= len(r["problem_statement"] or "") <= 20000]
    outcome = _outcome_instances()
    with_o = [r for r in rows if r["instance_id"] in outcome]
    without = [r for r in rows if r["instance_id"] not in outcome]
    rng.shuffle(with_o)
    rng.shuffle(without)
    # One instance per repo first, for diversity; then fill.
    picked, seen_repo = [], set()
    for pool in (with_o, without):
        for r in pool:
            if len(picked) < n and r["repo"] not in seen_repo:
                picked.append(r)
                seen_repo.add(r["repo"])
    for r in with_o + without:
        if len(picked) >= n:
            break
        if r not in picked:
            picked.append(r)
    out = []
    for r in picked:
        llm = ((r.get("meta") or {}).get("llm_score") or {})
        out.append(_swe_example("reb", "swe-rebench", r, {
            "repo_license": r.get("license_name"), "has_outcomes": r["instance_id"] in outcome,
            "rebench_llm_difficulty_score": llm.get("difficulty_score")}))
    return out


def select_swe_smith(n: int, rng: random.Random) -> list[dict]:
    import pyarrow.parquet as pq

    rows = []
    for p in sorted((RAW / "swe-smith" / "data").glob("train-*.parquet")):
        rows += pq.read_table(p, columns=["instance_id", "repo", "problem_statement"]).to_pylist()
    rows = [r for r in rows if is_gold(r["instance_id"]) and 80 <= len(r["problem_statement"] or "") <= 20000]
    rng.shuffle(rows)
    picked, seen_repo, seen_text = [], {}, set()
    for r in rows:  # at most 2 per repo, no near-duplicate statements
        k = r["problem_statement"][:300]
        if k in seen_text or seen_repo.get(r["repo"], 0) >= 2:
            continue
        seen_text.add(k)
        seen_repo[r["repo"]] = seen_repo.get(r["repo"], 0) + 1
        picked.append(r)
        if len(picked) >= n:
            break
    return [_swe_example("smi", "swe-smith", r) for r in picked]


def wildchat_pool() -> list[dict]:
    """All gold-partition English, non-toxic, non-redacted first user turns that look like tasks."""
    import pyarrow.parquet as pq

    from ..datagen.real import _BAD, _englishish

    cols = ["conversation_hash", "conversation", "language", "toxic", "redacted"]
    out, seen = [], set()
    for p in sorted((RAW / "wildchat" / "data").glob("train-*.parquet")):
        for r in pq.read_table(p, columns=cols).to_pylist():
            if r["language"] != "English" or r["toxic"] or r["redacted"] or not is_gold(r["conversation_hash"]):
                continue
            turns = [t for t in r["conversation"] if t["role"] == "user"]
            if not turns:
                continue
            text = (turns[0]["content"] or "").strip()
            if not (25 <= len(text) <= 12000) or _BAD.search(text) or not _englishish(text):
                continue
            k = re.sub(r"\W+", " ", text.lower())[:200]
            if k in seen:
                continue
            seen.add(k)
            text = _clip(scrub(text, aggressive=True))
            out.append({"raw_id": r["conversation_hash"], "text": text, "bucket": wildchat_bucket(text)})
    return out


SCREEN_PROMPT = """You screen real user requests (first turns of chats with an AI assistant) for a routing benchmark.
For EACH request decide:
- keep: 1 if it is a genuine, self-contained, safe-for-work task or question that an AI assistant could be asked
  to do (any domain), written mainly in English, without being roleplay/creative fiction, spam, a jailbreak,
  a pasted forum dump or a pure translation/paraphrase job; else 0.
- cat: the single best category among: {cats}.
Answer ONLY with JSON: {{"items": [{{"id": "...", "keep": 0/1, "cat": "..."}}, ...]}} one entry per request.
Do not use tools.

REQUESTS:
{items}
"""
_CJK = re.compile(r"[\u3040-\u30ff\u3400-\u9fff\uac00-\ud7af]")


SCREEN_TEACHERS = tuple(os.environ.get("GOLD_SCREEN_TEACHERS", "kimi,codex").split(","))


async def screen_wildchat(rows: list[dict], batch: int = 40) -> dict[str, dict]:
    """Cheap Kimi pre-screen (keep + rough category) used only to balance candidate selection.

    The screen is NOT a label: selected tasks are labelled independently by all three teachers."""
    from ..datagen.jsonio import extract_json
    from ..taxonomy import CATEGORIES

    sems = {t: asyncio.Semaphore(CONCURRENCY[t]) for t in SCREEN_TEACHERS}
    out: dict[str, dict] = {}

    async def one(chunk):
        items = "\n".join(f"### id={r['raw_id'][:12]}\n{r['text'][:1500]}\n" for r in chunk)
        prompt = SCREEN_PROMPT.format(cats=", ".join(CATEGORIES), items=items)
        for attempt in range(2 * len(SCREEN_TEACHERS)):
            teacher = SCREEN_TEACHERS[attempt % len(SCREEN_TEACHERS)]
            hit = next((c for t in SCREEN_TEACHERS if (c := _cache_path(f"{t}-screen", prompt)).exists()), None)
            cp = hit or _cache_path(f"{teacher}-screen", prompt)
            try:
                if hit:
                    raw = cp.read_text()
                else:
                    async with sems[teacher]:
                        raw = await raw_call(teacher, prompt)
                obj = extract_json(raw)
                got = {str(it.get("id")): it for it in (obj.get("items") if isinstance(obj, dict) else obj)}
                if len(got) < 0.6 * len(chunk):
                    raise ValueError("too few screen items")
                cp.write_text(raw)
                for r in chunk:
                    if (it := got.get(r["raw_id"][:12])) is not None:
                        out[r["raw_id"]] = {"keep": int(it.get("keep") in (1, "1", True)), "cat": it.get("cat")}
                print(f"[screen] +{len(chunk)}", flush=True)
                return
            except Exception as e:  # noqa: BLE001
                cp.unlink(missing_ok=True)
                print(f"[screen] attempt {attempt} failed: {str(e)[:200]}", flush=True)

    await asyncio.gather(*(one(rows[i:i + batch]) for i in range(0, len(rows), batch)))
    return out


EXTRA_SCREEN = {"ui_frontend": 130, "data_analysis": 130}  # under-filled categories after the first screen
WILD_CAP_OVERRIDES = {"bugfix": 8, "implementation": 14}  # code categories are already covered by SWE sources


def select_wildchat(per_cat: int, rng: random.Random, per_bucket_screen: int = 70, n_unbucketed: int = 150) -> list[dict]:
    """Keyword buckets -> Kimi screen -> up to `per_cat` per screened category (balanced as far as data allows)."""
    pool = [r for r in wildchat_pool() if not _CJK.search(r["text"])]
    by: dict[str | None, list[dict]] = {}
    for r in pool:
        by.setdefault(r["bucket"], []).append(r)
    to_screen, extra = [], []
    for b, rows in by.items():
        rng.shuffle(rows)
        to_screen += rows[:n_unbucketed if b is None else per_bucket_screen]
        extra += rows[per_bucket_screen:per_bucket_screen + EXTRA_SCREEN.get(b, 0)]
    to_screen += extra  # appended so earlier screen batches keep their cache keys
    screen = asyncio.run(screen_wildchat(to_screen))
    write_jsonl(GOLD / "wildchat_screen.jsonl", [{"raw_id": r["raw_id"], "bucket": r["bucket"], **screen[r["raw_id"]]}
                                                 for r in to_screen if r["raw_id"] in screen])
    by_cat: dict[str, list[dict]] = {}
    for r in to_screen:
        s = screen.get(r["raw_id"])
        if s and s["keep"] and s.get("cat"):
            by_cat.setdefault(s["cat"], []).append(r)
    out = []
    for cat, rows in sorted(by_cat.items()):
        for r in rows[:WILD_CAP_OVERRIDES.get(cat, per_cat)]:
            text = r["text"]
            out.append({
                "id": f"gold-wil-{short_hash(r['raw_id'])}", "source": "wildchat", "pair_of": None,
                "task": {"text": text, "context": {"estimated_input_tokens": int(len(text) / 4) + 50,
                                                   "has_images": False, "requires_tools": False}},
                "meta": {"raw_id": r["raw_id"], "selection_bucket": r["bucket"], "screen_cat": cat},
            })
    return out


def build_candidates(n_rebench: int = 120, n_smith: int = 25, wild_per_cat: int = 20, seed: int = 0) -> dict:
    rng = random.Random(seed)
    reb = select_swe_rebench(n_rebench, rng)
    smi = select_swe_smith(n_smith, rng)
    wil = select_wildchat(wild_per_cat, rng)
    rows = reb + smi + wil
    assert len({r["id"] for r in rows}) == len(rows), "id collision"
    assert all(is_gold(r["meta"]["raw_id"]) for r in rows), "non-gold record selected"
    write_jsonl(CANDIDATES, rows)
    return {"swe-rebench": len(reb), "swe-smith": len(smi), "wildchat": len(wil),
            "wildchat_screen_cats": dict(Counter(r["meta"]["screen_cat"] for r in wil))}


# --------------------------------------------------------------------------- teachers
def _cache_path(teacher: str, prompt: str) -> Path:
    model = MODEL_TAG.get(teacher, "")
    key = hashlib.sha1(f"{teacher}|{model}|{prompt}".encode()).hexdigest()
    d = CACHE / "calls" / teacher
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.txt"


def _teacher_cwd() -> str:
    d = CACHE / "teacher_cwd"
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


async def _run_cli(argv: list[str]) -> str:
    proc = await asyncio.create_subprocess_exec(*argv, cwd=_teacher_cwd(), stdin=asyncio.subprocess.DEVNULL,
                                                stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE)
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise RuntimeError("timeout")
    out_s = out.decode(errors="replace")
    if proc.returncode != 0 or not out_s.strip():
        raise RuntimeError(f"exit {proc.returncode}: {err.decode(errors='replace')[-300:]}")
    return out_s


def _ollama_sync(prompt: str) -> str:
    body = json.dumps({"model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json", "think": False,
                       "options": {"temperature": 0.2, "num_ctx": 32768, "num_predict": 6000}}).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.loads(r.read())["response"]


async def raw_call(teacher: str, prompt: str) -> str:
    if teacher == "codex":
        return await _run_cli(["codex", "exec", "--skip-git-repo-check", "-m", CODEX_MODEL, prompt])
    if teacher == "kimi":
        return await _run_cli(["kimi", "-p", prompt])
    if teacher == "grok":
        return await _run_cli(["grok", "-m", GROK_MODEL, "--disable-web-search", "-p", prompt])
    if teacher == "deepseek":
        from ..datagen.teachers import openrouter_chat

        return await asyncio.to_thread(openrouter_chat, prompt, DEEPSEEK_MODEL)
    if teacher == "ollama":
        return await asyncio.to_thread(_ollama_sync, prompt)
    raise ValueError(teacher)


def build_prompt(items: list[tuple[str, dict]]) -> str:
    from ..datagen.label import build_prompt as _bp

    return CAREFUL + _bp(items)


def parse_answers(raw: str, lids: list[str]) -> dict[str, dict]:
    from ..datagen.jsonio import extract_json
    from ..datagen.label import clean_answer

    obj = extract_json(raw)
    items = obj.get("labels") if isinstance(obj, dict) else obj
    if not isinstance(items, list):
        raise ValueError("no labels list")
    got = {}
    for it in items:
        lid = str((it or {}).get("id", "")).strip()
        if lid in lids:
            try:
                got[lid] = {"clean": clean_answer(it), "raw": it}
            except (ValueError, TypeError, KeyError):
                continue
    return got


async def _label_batch(teacher: str, batch: list[dict], sem: asyncio.Semaphore, log) -> int:
    lids = [f"t{i:02d}" for i in range(len(batch))]
    prompt = build_prompt(list(zip(lids, [r["task"] for r in batch])))
    cp = _cache_path(teacher, prompt)
    for attempt in range(3):
        raw = None
        try:
            if cp.exists():
                raw = cp.read_text()
            else:
                async with sem:
                    t0 = time.time()
                    raw = await raw_call(teacher, prompt)
                    log(f"[{teacher}] call {time.time() - t0:.0f}s")
            got = parse_answers(raw, lids)
            if not got:
                raise ValueError("no usable labels")
            cp.write_text(raw)
            rows = [{"id": r["id"], "teacher": teacher, "model": MODEL_TAG[teacher],
                     "ans": got[lid]["clean"], "raw": got[lid]["raw"], "ts": round(time.time())}
                    for lid, r in zip(lids, batch) if lid in got]
            append_jsonl(ANSWERS, rows)
            log(f"[{teacher}] +{len(rows)}/{len(batch)}")
            return len(rows)
        except Exception as e:  # noqa: BLE001 - retried
            cp.unlink(missing_ok=True)
            if raw:
                (cp.parent / "failed").mkdir(exist_ok=True)
                (cp.parent / "failed" / f"{cp.stem}.{attempt}.txt").write_text(raw)
            log(f"[{teacher}] attempt {attempt} failed: {str(e)[:200]}")
            await asyncio.sleep(10 * (attempt + 1))
    return 0


def answers_by_teacher() -> dict[str, dict[str, dict]]:
    out: dict[str, dict[str, dict]] = {t: {} for t in TEACHERS}
    for r in read_jsonl(ANSWERS):
        if r.get("model") == MODEL_TAG.get(r["teacher"]):
            out.setdefault(r["teacher"], {})[r["id"]] = r
    return out


async def label(teachers: list[str], passes: int = 2, limit: int | None = None) -> None:
    cands = read_jsonl(CANDIDATES)[:limit]

    def log(msg):
        print(msg, flush=True)

    async def run_teacher(t):
        sem = asyncio.Semaphore(CONCURRENCY[t])
        for p in range(passes):
            have = answers_by_teacher().get(t, {})
            todo = [c for c in cands if c["id"] not in have]
            if not todo:
                return
            random.Random(f"gold-{t}-{p}").shuffle(todo)
            # Tasks with the fewest other-teacher answers first, so every task reaches 2 teachers soonest.
            all_ans = answers_by_teacher()
            todo.sort(key=lambda c: sum(c["id"] in v for v in all_ans.values()))
            log(f"[{t}] pass {p}: {len(todo)} tasks")
            await asyncio.gather(*(_label_batch(t, todo[i:i + BATCH], sem, log) for i in range(0, len(todo), BATCH)))

    await asyncio.gather(*(run_teacher(t) for t in teachers))


# --------------------------------------------------------------------------- merge
def teacher_agreement_stats(per_task: dict[str, dict[str, dict]]) -> dict:
    """Pairwise agreement between teacher families over tasks labelled by both."""
    from scipy.stats import spearmanr

    from ..taxonomy import CHECKLIST_IDS, FLAGS, SKILL_AXES

    names = sorted({t for v in per_task.values() for t in v})
    pairs = {}
    for i, a in enumerate(names):
        for b in names[i + 1:]:
            both = [v for v in per_task.values() if a in v and b in v]
            if not both:
                continue
            da = np.array([v[a]["diff"] for v in both], float)
            db = np.array([v[b]["diff"] for v in both], float)
            bits = [[v[a]["flags"][f] == v[b]["flags"][f] for f in FLAGS] for v in both]
            cbits = [[v[a]["check"][c] == v[b]["check"][c] for c in CHECKLIST_IDS] for v in both]
            sk = [np.mean([abs(v[a]["skills"][k] - v[b]["skills"][k]) for k in SKILL_AXES]) for v in both]
            ka, kb = [v[a]["cat"] for v in both], [v[b]["cat"] for v in both]
            po = float(np.mean([x == y for x, y in zip(ka, kb)]))
            cats = sorted(set(ka) | set(kb))
            pe = sum((ka.count(c) / len(ka)) * (kb.count(c) / len(kb)) for c in cats)
            pairs[f"{a}~{b}"] = {
                "n": len(both),
                "category_agree": round(po, 4),
                "category_kappa": round((po - pe) / (1 - pe), 4) if pe < 1 else 1.0,
                "difficulty_spearman": round(float(spearmanr(da, db).statistic), 4) if len(both) > 2 else None,
                "difficulty_mae": round(float(np.mean(np.abs(da - db))), 4),
                "difficulty_within1": round(float(np.mean(np.abs(da - db) <= 1)), 4),
                "difficulty_mean": [round(float(da.mean()), 3), round(float(db.mean()), 3)],
                "skill_mae": round(float(np.mean(sk)), 4),
                "flag_agree": round(float(np.mean(bits)), 4),
                "checklist_agree": round(float(np.mean(cbits)), 4),
            }
    return pairs


def _norm_text(text: str) -> str:
    return re.sub(r"\W+", " ", text.lower()).strip()


def hygiene(rows: list[dict], data_dir: Path | None = None) -> tuple[list[dict], list[str]]:
    """Drop gold rows whose normalised text duplicates a train/val/test row; flag SWE rows whose repo is in train."""
    data_dir = data_dir or ROOT / "data"
    seen, repos = set(), set()
    for s in ("train", "val", "test"):
        for r in read_jsonl(data_dir / f"{s}.jsonl"):
            seen.add(_norm_text(r["task"]["text"]))
            if r["source"].startswith("swe"):
                repos.add((r.get("meta") or {}).get("repo"))
    kept, dropped = [], []
    for r in rows:
        if _norm_text(r["task"]["text"]) in seen:
            dropped.append(r["id"])
            continue
        if r["source"].startswith("swe"):
            r["meta"]["repo_in_train"] = r["meta"].get("repo") in repos
        kept.append(r)
    return kept, dropped


def merge_gold(min_teachers: int = 2, out: Path | None = None) -> dict:
    from ..datagen.merge import agreement, merge

    cands = read_jsonl(CANDIDATES)
    by_t = answers_by_teacher()
    rows, per_task, dropped = [], {}, 0
    for c in cands:
        got = {t: by_t[t][c["id"]] for t in TEACHERS if c["id"] in by_t.get(t, {})}
        if len(got) < min_teachers:
            dropped += 1
            continue
        names = sorted(got)
        core = [t for t in names if t not in EXTRA_TEACHERS]
        if len(core) < min_teachers:
            dropped += 1
            continue
        answers = [got[t]["ans"] for t in core]
        per_task[c["id"]] = {t: got[t]["ans"] for t in core}
        meta = {**c.get("meta", {}), "teachers": core, "agreement": agreement(answers),
                "teacher_models": {t: got[t].get("model") for t in names},
                "teacher_answers": {t: got[t]["ans"] for t in names}, "split": "gold"}
        rows.append({"id": c["id"], "source": c["source"], "pair_of": None, "task": c["task"],
                     "labels": merge(answers), "meta": meta})
    rows, dup_ids = hygiene(rows)
    per_task = {k: v for k, v in per_task.items() if k not in set(dup_ids)}
    write_jsonl(out or GOLD_PATH, rows)
    top = Counter(max(r["labels"]["category"].items(), key=lambda kv: kv[1])[0] for r in rows)
    exp_d = [sum((i + 1) * p for i, p in enumerate(r["labels"]["difficulty"])) for r in rows]
    return {"n": len(rows), "dropped_lt_min_teachers": dropped, "dropped_duplicate_of_train": dup_ids,
            "swe_repo_in_train": dict(Counter(bool(r["meta"]["repo_in_train"]) for r in rows if "repo_in_train" in r["meta"])),
            "by_source": dict(Counter(r["source"] for r in rows)),
            "teacher_sets": dict(Counter("+".join(r["meta"]["teachers"]) for r in rows)),
            "top_category": dict(top.most_common()),
            "difficulty_expected_hist": dict(Counter(int(round(x)) for x in exp_d)),
            "difficulty_expected_mean": round(float(np.mean(exp_d)), 3) if rows else None,
            "mean_agreement": round(float(np.mean([r["meta"]["agreement"] for r in rows])), 4) if rows else None,
            "pairs": teacher_agreement_stats(per_task)}
