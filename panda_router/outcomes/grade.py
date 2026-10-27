"""Attempt-and-grade: OpenRouter calls, blind rubric judging, a sandboxed Python run check, Cohen's kappa.

The OpenRouter key is read at call time from opencode's auth file into memory only. It is never logged,
printed or written; errors are reported without request headers.
"""

from __future__ import annotations

import json
import os
import random
import re
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path

URL = "https://openrouter.ai/api/v1/chat/completions"
AUTH = Path.home() / ".local" / "share" / "opencode" / "auth.json"

ATTEMPT_SYSTEM = ("You are answering a user's request in a single reply. You have no tools, no internet and no access "
                  "to any repository or files the user mentions: work from the text alone. Where the request needs "
                  "code, write the code. Where it refers to files you cannot see, state brief assumptions and still "
                  "deliver the concrete artefact. Be complete but concise (at most ~1,000 words).")

RUBRIC_PROMPT = """You will write a strict grading checklist for answers to the task below. Answers are single replies \
from an assistant with no tools and no repository access, so do not require running code, browsing or seeing files; \
require what a single expert reply could deliver.

List 3-6 acceptance criteria. Use the task's explicit acceptance criteria when present, otherwise infer what a \
demanding user would check. Mark the 1-3 criteria without which the answer is useless as "critical".

TASK:
<<<
{task}
>>>

Reply with JSON only: {{"criteria": [{{"id": 1, "text": "...", "critical": true}}, ...]}}"""

JUDGE_PROMPT = """You are a strict grader. Decide whether the ANSWER satisfies the TASK. You do not know which model \
wrote it. The answerer had no tools or file access, so judge the reply on its own merits.

PASS only if every critical criterion is met, no more than one non-critical criterion is missed, and the answer \
contains no material factual, mathematical or code error. A truncated, evasive, generic or mostly-placeholder answer \
FAILS. Check math and code yourself.

TASK:
<<<
{task}
>>>

CRITERIA:
{criteria}

ANSWER:
<<<
{answer}
>>>

Reply with JSON only: {{"met": [criterion ids met], "errors": "short note on material errors or ''", "pass": true|false}}"""


STRICT_JUDGE_PROMPT = """You are a strict, sceptical grader. Assume the ANSWER fails until it proves otherwise. You do \
not know which model wrote it. The answerer had no tools or file access.

For EACH criterion, quote the exact part of the answer that satisfies it, or write "" if none. Generic statements, \
restating the request, placeholders ("...", "TODO", "implement here"), or claims without the concrete content do NOT \
satisfy a criterion. Then list every material error: wrong facts, wrong math or numbers, code that would not compile \
or run or is logically wrong, contradictions, or the answer being cut off. Recompute any math yourself.

TASK:
<<<
{task}
>>>

CRITERIA:
{criteria}

ANSWER:
<<<
{answer}
>>>

Reply with JSON only:
{{"criteria": [{{"id": 1, "evidence": "quote or ''", "met": true|false}}, ...], "material_errors": ["..."]}}"""


def strict_verdict(j: dict, criteria: list[dict]) -> bool | None:
    """Pass = every critical criterion met with non-empty evidence, at most one other criterion missed, and no material
    error. Computed here, not by the judge, so a lenient judge cannot wave an answer through."""
    rows = j.get("criteria")
    if not isinstance(rows, list):
        return None
    met = {r.get("id") for r in rows if isinstance(r, dict) and r.get("met") is True and str(r.get("evidence") or "").strip()}
    crit = [c["id"] for c in criteria if c.get("critical")]
    missed = [c["id"] for c in criteria if c["id"] not in met]
    errs = [e for e in (j.get("material_errors") or []) if str(e).strip()]
    return all(c in met for c in crit) and len([m for m in missed if m not in crit]) <= 1 and not errs


def _key() -> str:
    return json.loads(AUTH.read_text())["openrouter"]["key"]


def chat(model: str, messages: list[dict], max_tokens: int, reasoning: dict | None = None, retries: int = 6,
         timeout: float = 240.0, temperature: float | None = None) -> dict:
    """One completion. Returns {text, finish, usage{prompt,completion,reasoning}, cost, error}. Backs off on 429/5xx."""
    body = {"model": model, "messages": messages, "max_tokens": max_tokens, "usage": {"include": True}}
    if reasoning is not None:
        body["reasoning"] = reasoning
    if temperature is not None:
        body["temperature"] = temperature
    data = json.dumps(body).encode()
    err = ""
    for attempt in range(retries):
        req = urllib.request.Request(URL, data=data, headers={"Authorization": f"Bearer {_key()}",
                                                              "Content-Type": "application/json",
                                                              "X-Title": "panda-router outcomes"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                out = json.loads(r.read())
            if "error" in out:
                raise RuntimeError(str(out["error"])[:300])
            ch = out["choices"][0]
            u = out.get("usage") or {}
            det = u.get("completion_tokens_details") or {}
            return {"text": (ch.get("message") or {}).get("content") or "", "finish": ch.get("finish_reason"),
                    "usage": {"prompt": u.get("prompt_tokens", 0), "completion": u.get("completion_tokens", 0),
                              "reasoning": det.get("reasoning_tokens", 0)},
                    "cost": float(u.get("cost") or 0.0), "provider": out.get("provider"), "error": ""}
        except urllib.error.HTTPError as e:
            err = f"http {e.code}: {e.read()[:200].decode(errors='replace')}"
            if e.code not in (408, 429, 500, 502, 503, 504, 529):
                break
        except Exception as e:  # network / timeout / malformed provider reply
            err = f"{type(e).__name__}: {str(e)[:200]}"
        time.sleep(min(60.0, 2.0 ** attempt + random.random() * 2))
    return {"text": "", "finish": "error", "usage": {"prompt": 0, "completion": 0, "reasoning": 0}, "cost": 0.0,
            "provider": None, "error": err}


def parse_json(text: str) -> dict | None:
    """First JSON object in a reply (tolerates ```json fences and prose around it)."""
    m = re.search(r"\{.*\}", text or "", re.S)
    if not m:
        return None
    try:
        return json.loads(m.group(0))
    except json.JSONDecodeError:
        return None


def format_criteria(criteria: list[dict]) -> str:
    return "\n".join(f"{c['id']}. {'[critical] ' if c.get('critical') else ''}{c['text']}" for c in criteria)


def python_blocks(answer: str) -> list[str]:
    return re.findall(r"```(?:python|py)\s*\n(.*?)```", answer or "", re.S)


def run_python(code: str, timeout: float = 10.0) -> tuple[bool, str]:
    """Run code in a throwaway dir with `python -I` and a timeout. Returns (ok, stderr tail)."""
    with tempfile.TemporaryDirectory() as d:
        p = Path(d) / "answer.py"
        p.write_text(code)
        env = {"PATH": os.environ.get("PATH", ""), "HOME": d, "PYTHONDONTWRITEBYTECODE": "1"}
        try:
            r = subprocess.run([sys.executable, "-I", str(p)], cwd=d, env=env, capture_output=True, text=True,
                               timeout=timeout, stdin=subprocess.DEVNULL)
        except subprocess.TimeoutExpired:
            return False, "timeout"
        return r.returncode == 0, r.stderr[-300:]


def code_check(answer: str) -> dict | None:
    """Programmatic gate for self-contained Python answers: the (single, stdlib-only) block must run cleanly,
    including any asserts/examples the answer ships. None when not applicable (no block, several blocks, or
    third-party imports we cannot run offline)."""
    blocks = python_blocks(answer)
    if len(blocks) != 1:
        return None
    code = blocks[0]
    mods = set(re.findall(r"^\s*(?:from|import)\s+([A-Za-z_]\w*)", code, re.M))
    if mods - set(sys.stdlib_module_names) or "input(" in code or re.search(r"\b(socket|requests|urllib)\b", code):
        return None
    ok, tail = run_python(code)
    return {"ran": ok, "stderr": tail}


def cohen_kappa(x: list[bool], y: list[bool]) -> float:
    n = len(x)
    po = sum(a == b for a, b in zip(x, y)) / n
    px, py = sum(x) / n, sum(y) / n
    pe = px * py + (1 - px) * (1 - py)
    return 1.0 if pe == 1 else (po - pe) / (1 - pe)


if __name__ == "__main__":
    assert parse_json('```json\n{"pass": true}\n```') == {"pass": True}
    assert cohen_kappa([True, False, True, False], [True, False, True, False]) == 1.0
    assert abs(cohen_kappa([True, True, False, False], [True, False, True, False])) < 1e-9
    assert code_check("```python\nassert 1 + 1 == 2\n```") == {"ran": True, "stderr": ""}
    assert code_check("```python\nassert 1 + 1 == 3\n```")["ran"] is False
    assert code_check("```python\nimport numpy\n```") is None
    cr = [{"id": 1, "text": "x", "critical": True}, {"id": 2, "text": "y"}, {"id": 3, "text": "z"}]
    assert strict_verdict({"criteria": [{"id": 1, "evidence": "q", "met": True}], "material_errors": []}, cr) is False
    assert strict_verdict({"criteria": [{"id": 1, "evidence": "q", "met": True}, {"id": 2, "evidence": "q", "met": True}],
                           "material_errors": []}, cr) is True
    assert strict_verdict({"criteria": [{"id": 1, "evidence": "", "met": True}, {"id": 2, "evidence": "q", "met": True}],
                           "material_errors": []}, cr) is False
    assert strict_verdict({"criteria": [{"id": 1, "evidence": "q", "met": True}, {"id": 2, "evidence": "q", "met": True}],
                           "material_errors": ["wrong"]}, cr) is False
    print("ok")
