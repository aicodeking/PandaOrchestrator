"""Stage 2: real seed tasks from SWE-rebench (CC-BY-4.0), SWE-smith (MIT) and WildChat-1M (ODC-BY).

Raw parquet shards are fetched with huggingface_hub into data/raw/hf/ (the installed `datasets`
package is incompatible with pyarrow>=21). The GOLD EXCLUSION RULE drops every record whose
int(sha1(id), 16) % 10 == 0 (id = instance_id or conversation_hash).
"""

import random
import re
from pathlib import Path

import pyarrow.parquet as pq

from . import paths
from .common import is_gold_reserved, short_hash
from .jsonio import write_jsonl

SHARDS = {
    "swe-rebench": ("nebius/SWE-rebench", ["data/filtered-00000-of-00001.parquet"]),
    "swe-smith": ("SWE-bench/SWE-smith", ["data/train-00000-of-00011.parquet"]),
    "wildchat": ("allenai/WildChat-1M", ["data/train-00000-of-00014.parquet", "data/train-00001-of-00014.parquet"]),
}
PREFIX = {"swe-rebench": "reb", "swe-smith": "smi", "wildchat": "wil"}
MAX_TEXT = 5000

_EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
_PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{8,}\d)(?!\w)")
_IP = re.compile(r"\b(?:\d{1,3}\.){3}\d{1,3}\b")
_KEY = re.compile(r"\b(?:sk-[A-Za-z0-9_-]{16,}|AKIA[0-9A-Z]{16}|ghp_[A-Za-z0-9]{20,}|xox[bp]-[A-Za-z0-9-]{10,})")
_GENERIC_KEY = re.compile(r"\b(?=[A-Za-z0-9_\-]*\d)(?=[A-Za-z0-9_\-]*[A-Z])(?=[A-Za-z0-9_\-]*[a-z])[A-Za-z0-9_\-]{32,}\b")
_URL_CRED = re.compile(r"(https?://)[^/\s:@]+:[^/\s@]+@")
_TECH = re.compile(
    r"(```|\bdef |\bclass |\bimport |#include|\bfunction\b|=>|\bSELECT\b|\bpython\b|\bjava(script)?\b|\bc\+\+|\brust\b|"
    r"\bgolang\b|\bsql\b|\bapi\b|\bbug\b|\berror\b|exception|traceback|\bcode\b|(python|bash|shell|powershell|vba|js|lua) script|docker|kubernetes|\bregex\b|"
    r"\bhtml\b|\bcss\b|\breact\b|\bnode\b|\balgorithm\b|\bdatabase\b|\bexcel\b|\blinux\b|\bgit\b|\bunity\b|\bjson\b|"
    r"\bcompile|\bdebug|\bfunction|\bvariable|\bserver\b|\bdeploy|\bequation|\bprove\b|\bcalculate\b)", re.I)
_TASKY = re.compile(r"^(write|explain|create|make|how|what|why|fix|help|give|generate|summari[sz]e|rewrite|translate|"
                    r"design|implement|build|convert|calculate|solve|list|compare|analy[sz]e|review|optimi[sz]e|plan|draft|can you|i need|i want|please)", re.I)
_BAD = re.compile(r"(\broleplay\b|\bstory\b|\bfanfic|\bnsfw\b|\bsex|\bpoem\b|\blyrics\b|\bjoke\b|continue the|freedom planet|"
                  r"\bdan\b|jailbreak|ignore (all|previous)|pretend you|midjourney|prompt generator|\bkiss|\bnaked|\bgirlfriend|script about|day \d+ script|\bepisode\b|\bcharacters?:|\bscene\b|"
                  r"\bwaifu|\bmonika\b|\bsayori\b|\bnatsuki\b|\byuri\b|\bhentai|\bfeet\b)", re.I)


def download() -> None:
    from huggingface_hub import hf_hub_download

    for repo, files in SHARDS.values():
        for f in files:
            hf_hub_download(repo, f, repo_type="dataset", local_dir=str(paths.RAW / "hf" / repo.replace("/", "__")))


def _shard_paths(source: str) -> list[Path]:
    repo, files = SHARDS[source]
    return [paths.RAW / "hf" / repo.replace("/", "__") / f for f in files]


def scrub_pii(text: str, aggressive: bool = False) -> str:
    """Mask emails, credentials, API keys, IPs and phone numbers. `aggressive` also masks long
    mixed-case alphanumeric tokens (likely keys) and is used for chat logs."""
    text = _URL_CRED.sub(r"\1<cred>@", text)
    text = _EMAIL.sub("<email>", text)
    text = _KEY.sub("<redacted_key>", text)
    if aggressive:
        text = _GENERIC_KEY.sub("<redacted_key>", text)
        text = _IP.sub("<ip>", text)
        text = _PHONE.sub(lambda m: "<phone>" if sum(c.isdigit() for c in m.group(0)) >= 10 and "." not in m.group(0) else m.group(0), text)
    return text


def _clip(text: str) -> str:
    text = text.strip()
    if len(text) > MAX_TEXT:
        text = text[:MAX_TEXT - 300] + "\n[...truncated...]\n" + text[-250:]
    return text


_NON_EN = re.compile(r"\b(el|la|los|las|que|para|este|como|und|der|die|das|ist|nicht|est|les|pour|une|dans)\b", re.I)


def _englishish(text: str) -> bool:
    letters = [c for c in text if c.isalpha()]
    if not letters or sum(ord(c) > 127 for c in letters) / len(letters) > 0.03:
        return False
    words = max(1, len(text.split()))
    return len(_NON_EN.findall(text)) / words < 0.04


_URL = re.compile(r"https?://\S+")
_PATH = re.compile(
    r"(?<![\w./-])((?:[\w.-]+/)*[\w-]+\.(?:py|pyx|pyi|js|jsx|ts|tsx|c|h|cc|cpp|hpp|rs|go|rb|java|php|rst|md|txt|cfg|toml|ini|ya?ml|json|html|css|sh))\b")
_FROM_IMPORT = re.compile(r"^\s*(?:from|import)\s+([A-Za-z_][\w]*(?:\.[A-Za-z_]\w*)+)", re.M)
REPO_CONTEXT_TOKENS = 4000  # fixed allowance for the repo files an agent reads on top of the issue text


def issue_files_in_scope(text: str, repo: str | None = None) -> int | None:
    """Routing-time estimate of files in scope: distinct file paths / repo-internal modules named in the
    issue text (never the patch). None when the text names no file at all."""
    text = _URL.sub(" ", text or "")
    found = {m.group(1).rsplit("/", 1)[-1] for m in _PATH.finditer(text)}
    pkg = re.sub(r"[^a-z0-9]", "", (repo or "").rsplit("/", 1)[-1].lower())
    for m in _FROM_IMPORT.finditer(text):
        mod = m.group(1)
        if pkg and re.sub(r"[^a-z0-9]", "", mod.split(".")[0].lower()) == pkg:
            found.add(mod.rsplit(".", 1)[0] + ".py")
    return len(found) or None


def issue_context(text: str, repo: str | None = None) -> dict:
    """task.context for a real SWE row, derived from the issue text only (no patch information)."""
    ctx = {"repo_languages": ["python"], "estimated_input_tokens": int(len(text) / 4 + REPO_CONTEXT_TOKENS),
           "has_images": _has_images(text), "requires_tools": True}
    if (n := issue_files_in_scope(text, repo)) is not None:
        ctx["files_in_scope"] = n
    return ctx


def _has_images(text: str) -> bool:
    return bool(re.search(r"!\[[^\]]*\]\(|\.(png|jpe?g|gif|webp)\b|screenshot", text, re.I))


def _swe_rows(source: str, limit: int, rng: random.Random) -> list[dict]:
    cols = ["instance_id", "repo", "problem_statement"]
    rows = []
    for p in _shard_paths(source):
        rows += pq.read_table(p, columns=cols).to_pylist()
    rows = [r for r in rows if not is_gold_reserved(r["instance_id"]) and 80 <= len(r["problem_statement"] or "") <= 20000]
    seen, uniq = set(), []
    for r in rows:  # SWE-smith has many instances per repo with near-identical text
        k = (r["problem_statement"] or "")[:300]
        if k not in seen:
            seen.add(k)
            uniq.append(r)
    rng.shuffle(uniq)
    out = []
    for r in uniq[:limit]:
        text = _clip(scrub_pii(r["problem_statement"]))
        out.append({
            "id": f"{PREFIX[source]}-{short_hash(r['instance_id'])}", "source": source, "pair_of": None,
            "task": {"text": f"Repository: {r['repo']}\n\n{text}", "context": issue_context(text, r["repo"])},
            "meta": {"raw_id": r["instance_id"], "repo": r["repo"], "persona": None},
        })
    return out


def _wild_rows(limit: int, rng: random.Random, tech_frac: float = 0.8) -> list[dict]:
    cols = ["conversation_hash", "conversation", "language", "toxic", "redacted"]
    tech, other, seen = [], [], set()
    for p in _shard_paths("wildchat"):
        if not p.exists():
            continue
        for r in pq.read_table(p, columns=cols).to_pylist():
            if r["language"] != "English" or r["toxic"] or r["redacted"] or is_gold_reserved(r["conversation_hash"]):
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
            rec = (r["conversation_hash"], text)
            if _TECH.search(text):
                tech.append(rec)
            elif _TASKY.search(text):
                other.append(rec)
    rng.shuffle(tech)
    rng.shuffle(other)
    n_tech = int(limit * tech_frac)
    picked = tech[:n_tech] + other[:limit - n_tech]
    out = []
    for h, text in picked:
        text = _clip(scrub_pii(text, aggressive=True))
        out.append({
            "id": f"{PREFIX['wildchat']}-{short_hash(h)}", "source": "wildchat", "pair_of": None,
            "task": {"text": text, "context": {"estimated_input_tokens": int(len(text) / 4) + 50,
                                               "has_images": False, "requires_tools": False}},
            "meta": {"raw_id": h, "persona": None},
        })
    return out


def build(n_rebench: int, n_smith: int, n_wild: int, seed: int = 0) -> dict[str, int]:
    """Write data/raw/<source>.jsonl (selected originals) and data/cache/pool/real.jsonl (tasks)."""
    paths.ensure()
    rng = random.Random(seed)
    reb = _swe_rows("swe-rebench", n_rebench, rng)
    smi = _swe_rows("swe-smith", n_smith, rng)
    wil = _wild_rows(n_wild, rng)
    for name, rows in (("swe_rebench", reb), ("swe_smith", smi), ("wildchat", wil)):
        write_jsonl(paths.RAW / f"{name}.jsonl", [{"id": r["id"], "raw_id": r["meta"]["raw_id"], "text": r["task"]["text"]} for r in rows])
    allrows = reb + smi + wil
    write_jsonl(paths.POOL / "real.jsonl", allrows)
    return {"swe-rebench": len(reb), "swe-smith": len(smi), "wildchat": len(wil)}


def issue_body(text: str) -> str:
    return text.partition("\n\n")[2] or text if text.startswith("Repository: ") else text


def refresh_contexts() -> dict[str, int]:
    """Rewrite files_in_scope / estimated_input_tokens of SWE pool rows (and their minimal pairs) from the
    issue text only. Idempotent; labels are keyed by id so existing teacher answers stay valid."""
    from .jsonio import read_jsonl

    reals = read_jsonl(paths.POOL / "real.jsonl")
    repo_of = {r["id"]: r["meta"].get("repo") for r in reals if r["source"] != "wildchat"}
    for r in reals:
        if r["id"] in repo_of:
            r["task"]["context"] = issue_context(issue_body(r["task"]["text"]), repo_of[r["id"]])
    write_jsonl(paths.POOL / "real.jsonl", reals)
    pairs = read_jsonl(paths.POOL / "minimal_pairs.jsonl")
    npairs = 0
    for r in pairs:
        if r["pair_of"] in repo_of:
            old = r["task"].get("context") or {}
            new = issue_context(issue_body(r["task"]["text"]), repo_of[r["pair_of"]])
            if (old.get("estimated_input_tokens") or 0) >= 80000:  # long_context edit sets the count on purpose
                new["estimated_input_tokens"] = old["estimated_input_tokens"]
            r["task"]["context"] = new
            npairs += 1
    write_jsonl(paths.POOL / "minimal_pairs.jsonl", pairs)
    return {"originals": len(repo_of), "pairs": npairs}
