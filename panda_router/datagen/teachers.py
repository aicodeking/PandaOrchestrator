"""Async wrappers around the teacher CLIs with caching, retries, concurrency limits and a call log.

Every successful raw response is cached under data/cache/calls/<teacher>/<sha>.txt keyed by the
prompt, so re-running any stage never pays twice for the same prompt.
"""

import asyncio
import hashlib
import json
import os
import random
import time
import urllib.error
import urllib.request
from typing import Any, Awaitable, Callable

from . import paths
from .jsonio import append_jsonl, extract_json

CODEX_MODEL = os.environ.get("PANDA_CODEX_MODEL", "gpt-5.6-luna")
OLLAMA_MODEL = os.environ.get("PANDA_OLLAMA_MODEL", "gemma4:26b")
OLLAMA_URL = os.environ.get("PANDA_OLLAMA_URL", "http://localhost:11434/api/generate")
TIMEOUT_S = int(os.environ.get("PANDA_TEACHER_TIMEOUT", "1200"))
GROK_MODEL = os.environ.get("PANDA_GROK_MODEL", "grok-4.7-build-fast")
DEEPSEEK_MODEL = os.environ.get("PANDA_DEEPSEEK_MODEL", "deepseek/deepseek-v4.1-flash")  # OpenRouter slug, direct API
OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
OPENROUTER_AUTH = os.path.expanduser("~/.local/share/opencode/auth.json")
DEEPSEEK_REASONING = os.environ.get("PANDA_DEEPSEEK_REASONING", "off")  # off | low | default
USAGE_LOG = paths.CACHE / "deepseek_usage.jsonl"
# $/Mtok, used only when the API response carries no usage.cost
DEEPSEEK_PRICE = (0.02, 1.00)
CONCURRENCY = {
    "codex": int(os.environ.get("PANDA_CODEX_CONC", "6")),
    "kimi": int(os.environ.get("PANDA_KIMI_CONC", "6")),
    "grok": int(os.environ.get("PANDA_GROK_CONC", "4")),
    "deepseek": int(os.environ.get("PANDA_DEEPSEEK_CONC", "6")),
    "ollama": int(os.environ.get("PANDA_OLLAMA_CONC", "1")),
}
_RATE_HINTS = ("rate limit", "429", "quota", "too many requests", "usage limit")

_sems: dict[str, asyncio.Semaphore] = {}


class TeacherError(RuntimeError):
    pass


def _sem(teacher: str) -> asyncio.Semaphore:
    if teacher not in _sems:
        _sems[teacher] = asyncio.Semaphore(CONCURRENCY[teacher])
    return _sems[teacher]


def _key(teacher: str, prompt: str) -> str:
    model = {"codex": CODEX_MODEL, "ollama": OLLAMA_MODEL, "grok": GROK_MODEL, "deepseek": DEEPSEEK_MODEL}.get(teacher, "")
    return hashlib.sha1(f"{teacher}|{model}|{prompt}".encode()).hexdigest()


def _cache_path(teacher: str, key: str):
    d = paths.CALLS / teacher
    d.mkdir(parents=True, exist_ok=True)
    return d / f"{key}.txt"


def _cwd() -> str:
    d = paths.CACHE / "teacher_cwd"  # empty dir so agentic CLIs see no repo files
    d.mkdir(parents=True, exist_ok=True)
    return str(d)


async def _run_cli(argv: list[str]) -> tuple[int, str, str]:
    proc = await asyncio.create_subprocess_exec(
        *argv, cwd=_cwd(), stdin=asyncio.subprocess.DEVNULL,
        stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE,
    )
    try:
        out, err = await asyncio.wait_for(proc.communicate(), timeout=TIMEOUT_S)
    except asyncio.TimeoutError:
        proc.kill()
        await proc.wait()
        raise TeacherError("timeout")
    return proc.returncode, out.decode(errors="replace"), err.decode(errors="replace")


def _ollama_sync(prompt: str) -> str:
    body = json.dumps({
        "model": OLLAMA_MODEL, "prompt": prompt, "stream": False, "format": "json", "think": False,
        "options": {"temperature": 0.2, "num_ctx": 32768},
    }).encode()
    req = urllib.request.Request(OLLAMA_URL, data=body, headers={"Content-Type": "application/json"})
    with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
        return json.loads(r.read())["response"]


_or_key: str | None = None


def _openrouter_key() -> str:
    global _or_key  # read once at runtime, held in memory only
    if _or_key is None:
        _or_key = json.load(open(OPENROUTER_AUTH))["openrouter"]["key"]
    return _or_key


def openrouter_chat(prompt: str, model: str | None = None, retries: int = 6) -> str:
    """Blocking chat completion with 429/5xx backoff; appends token usage and cost to USAGE_LOG."""
    body = {"model": model or DEEPSEEK_MODEL, "messages": [{"role": "user", "content": prompt}],
            "temperature": 0.2, "usage": {"include": True}}
    if DEEPSEEK_REASONING == "off":
        body["reasoning"] = {"enabled": False}
    elif DEEPSEEK_REASONING == "low":
        body["reasoning"] = {"effort": "low"}
    data = json.dumps(body).encode()
    for attempt in range(retries):
        req = urllib.request.Request(OPENROUTER_URL, data=data, headers={
            "Content-Type": "application/json", "Authorization": f"Bearer {_openrouter_key()}"})
        try:
            with urllib.request.urlopen(req, timeout=TIMEOUT_S) as r:
                j = json.loads(r.read())
            break
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503, 529) and attempt < retries - 1:
                time.sleep(min(120, 5 * 2 ** attempt) + random.random() * 3)
                continue
            raise TeacherError(f"{'ratelimit' if e.code == 429 else 'http'}:{e.code}:{e.read()[-200:]!r}")
        except (urllib.error.URLError, TimeoutError, ConnectionError) as e:
            if attempt < retries - 1:
                time.sleep(5 * 2 ** attempt)
                continue
            raise TeacherError(f"net:{e}")
    u = j.get("usage") or {}
    cost = u.get("cost")
    if cost is None:
        cost = (u.get("prompt_tokens", 0) * DEEPSEEK_PRICE[0] + u.get("completion_tokens", 0) * DEEPSEEK_PRICE[1]) / 1e6
    append_jsonl(USAGE_LOG, [{"ts": round(time.time(), 1), "model": body["model"], "prompt_tokens": u.get("prompt_tokens"),
                              "completion_tokens": u.get("completion_tokens"),
                              "reasoning_tokens": (u.get("completion_tokens_details") or {}).get("reasoning_tokens"),
                              "cost": cost}])
    try:
        return j["choices"][0]["message"]["content"] or ""
    except (KeyError, IndexError):
        raise TeacherError(f"bad response: {str(j)[:200]}")


async def _raw_call(teacher: str, prompt: str) -> str:
    if teacher == "codex":
        code, out, err = await _run_cli(["codex", "exec", "--skip-git-repo-check", "-m", CODEX_MODEL, prompt])
    elif teacher == "kimi":
        code, out, err = await _run_cli(["kimi", "-p", prompt])
    elif teacher == "grok":
        code, out, err = await _run_cli(["grok", "-m", GROK_MODEL, "--disable-web-search", "-p", prompt])
    elif teacher == "deepseek":
        return await asyncio.to_thread(openrouter_chat, prompt)
    elif teacher == "ollama":
        return await asyncio.to_thread(_ollama_sync, prompt)
    else:
        raise ValueError(teacher)
    if code != 0 or not out.strip():
        low = (out + err).lower()
        kind = "ratelimit" if any(h in low for h in _RATE_HINTS) else "exit"
        raise TeacherError(f"{kind}:{code}:{err.strip()[-300:]}")
    return out


async def call(teacher: str, prompt: str, parse: Callable[[Any], Any], purpose: str,
               retries: int = 3) -> Any:
    """Call a teacher, extract JSON, run `parse` (raise to reject), cache the raw text.

    Returns parse(json) or raises TeacherError after `retries` failed attempts.
    """
    key = _key(teacher, prompt)
    cp = _cache_path(teacher, key)
    if cp.exists():
        try:
            return parse(extract_json(cp.read_text()))
        except Exception:
            cp.unlink(missing_ok=True)
    last = None
    for attempt in range(retries):
        async with _sem(teacher):
            t0 = time.time()
            ok, err_s, raw = False, None, None
            try:
                raw = await _raw_call(teacher, prompt)
                try:
                    result = parse(extract_json(raw))
                except Exception:
                    fd = cp.parent / "failed"
                    fd.mkdir(exist_ok=True)
                    (fd / f"{key}.{attempt}.txt").write_text(raw)
                    raise
                cp.write_text(raw)
                ok = True
            except Exception as e:  # noqa: BLE001 - any failure is retried
                last, err_s = e, f"{type(e).__name__}: {str(e)[:200]}"
            append_jsonl(paths.CALL_LOG, [{
                "ts": round(t0, 1), "teacher": teacher, "purpose": purpose, "ok": ok,
                "secs": round(time.time() - t0, 1), "prompt_chars": len(prompt), "attempt": attempt,
                "err": err_s,
            }])
        if ok:
            return result
        wait = (60 if "ratelimit" in str(last) else 5) * (2 ** attempt) + random.random() * 5
        await asyncio.sleep(wait)
    raise TeacherError(f"{teacher} failed after {retries} attempts: {last}")


async def gather_limited(coros: list[Awaitable], on_done: Callable[[Any], None] | None = None) -> list:
    """Run coroutines (concurrency is enforced per teacher); swallow per-item failures as None."""

    async def wrap(c):
        try:
            r = await c
        except Exception as e:  # noqa: BLE001
            print(f"[warn] task failed: {str(e)[:300]}", flush=True)
            return None
        if on_done:
            on_done(r)
        return r

    return await asyncio.gather(*(wrap(c) for c in coros))
