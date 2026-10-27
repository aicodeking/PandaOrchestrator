"""Subscription-harness backends for attempt-and-grade (no OpenRouter): dsh (DeepSeek judge), Claude Code, Codex.

Each call returns the same dict shape as grade.chat(): {text, finish, usage{prompt,completion,reasoning}, cost, error}
plus `secs` and `quota` (True when the harness reports a usage/rate limit, so callers can stop using it).
cost is always 0.0 here (flat subscription); `list_cost` carries the harness-reported list price when it has one.
"""

from __future__ import annotations

import json
import os
import random
import shutil
import subprocess
import tempfile
import time
from pathlib import Path

WORK = Path(tempfile.gettempdir()) / "panda_cli_cwd"  # empty cwd: agentic CLIs see no repo files
CODEX_HOME = Path(tempfile.gettempdir()) / "panda_codexhome"  # bare config (no user skills/MCP), auth copied at runtime
CLAUDE_MODELS = {"claude-haiku-5.5": "haiku", "claude-sonnet-5.5": "sonnet", "claude-opus-5.5": "opus"}
CODEX_MODELS = {"codex-gpt-6-luna": "gpt-6-luna"}
CODEX_JUDGES = {"codex-terra": "gpt-5.6-terra"}  # judge-only: not attempters, so never listed as a card/model
QUOTA_HINTS = ("rate limit", "usage limit", "quota", "too many requests", "429", "limit reached", "overloaded")
EMPTY = {"prompt": 0, "completion": 0, "reasoning": 0}


def _run(argv: list[str], stdin: str | None, env: dict | None, timeout: float) -> tuple[int, str, str]:
    WORK.mkdir(exist_ok=True)
    try:
        p = subprocess.run(argv, input=stdin, cwd=WORK, env=env, capture_output=True, text=True, timeout=timeout)
    except subprocess.TimeoutExpired:
        return -9, "", "timeout"
    return p.returncode, p.stdout, p.stderr


def _retry(fn, retries: int) -> dict:
    """fn() -> dict with `error` ('' on success) and `quota`. Backs off on transient errors, stops on quota."""
    out = {}
    for k in range(retries):
        t0 = time.time()
        out = fn()
        out["secs"] = round(time.time() - t0, 1)
        if not out["error"] or out.get("quota"):
            break
        time.sleep(min(60.0, 3.0 * 2 ** k + random.random() * 3))
    return out


def _fail(err: str) -> dict:
    return {"text": "", "finish": "error", "usage": dict(EMPTY), "cost": 0.0, "provider": None, "error": err[-300:],
            "quota": any(h in err.lower() for h in QUOTA_HINTS)}


def dsh_chat(prompt: str, retries: int = 3, timeout: float = 900.0) -> dict:
    def go():
        code, out, err = _run(["dsh", "--profile", "headless", prompt], None, None, timeout)
        if code != 0 or not out.strip():
            return _fail(f"exit {code}: {err.strip()[-200:]}")
        return {"text": out, "finish": "stop", "usage": {"prompt": len(prompt) // 4, "completion": len(out) // 4,
                                                          "reasoning": len(err) // 4},
                "cost": 0.0, "provider": "dsh", "error": "", "quota": False}

    return _retry(go, retries)


def claude_chat(model_id: str, system: str, prompt: str, retries: int = 3, timeout: float = 600.0) -> dict:
    argv = ["claude", "-p", "--model", CLAUDE_MODELS[model_id], "--output-format", "json", "--tools", "",
            "--system-prompt", system, "--no-session-persistence", "--strict-mcp-config", "--setting-sources", "",
            "--disable-slash-commands", "--effort", "low"]

    def go():
        code, out, err = _run(argv, prompt, None, timeout)  # thinking budget is not controllable via flags/env (tested)
        try:
            j = json.loads(out)
        except json.JSONDecodeError:
            return _fail(f"exit {code}: {(err or out).strip()[-200:]}")
        if code != 0 or j.get("is_error") or not (j.get("result") or "").strip():
            return _fail(f"exit {code}: {str(j.get('result') or err)[-200:]}")
        u = j.get("usage") or {}
        mu = next(iter((j.get("modelUsage") or {}).values()), {})
        return {"text": j["result"], "finish": "length" if j.get("stop_reason") == "max_tokens" else "stop",
                "usage": {"prompt": u.get("input_tokens", 0) + u.get("cache_read_input_tokens", 0)
                                    + u.get("cache_creation_input_tokens", 0),
                          "completion": u.get("output_tokens", 0), "reasoning": mu.get("thinkingTokens", 0)},
                "cost": 0.0, "list_cost": j.get("total_cost_usd"), "provider": "claude-code", "error": "", "quota": False}

    return _retry(go, retries)


def codex_chat(model_id: str, system: str, prompt: str, retries: int = 3, timeout: float = 900.0) -> dict:
    if not (CODEX_HOME / "auth.json").exists():
        CODEX_HOME.mkdir(exist_ok=True)
        shutil.copy(Path.home() / ".codex" / "auth.json", CODEX_HOME / "auth.json")
        (CODEX_HOME / "config.toml").write_text('model_reasoning_effort = "low"\n')
    env = {**os.environ, "CODEX_HOME": str(CODEX_HOME)}
    argv = ["codex", "exec", "--skip-git-repo-check", "--ephemeral", "-s", "read-only", "-m", {**CODEX_MODELS, **CODEX_JUDGES}[model_id],
            "--json", "-"]
    full = f"{system}\n\n--- REQUEST ---\n{prompt}"

    def go():
        code, out, err = _run(argv, full, env, timeout)
        text, usage, errs = "", {}, []
        for line in out.splitlines():
            try:
                e = json.loads(line)
            except json.JSONDecodeError:
                continue
            if e.get("type") == "item.completed" and e["item"].get("type") == "agent_message":
                text = e["item"].get("text", "")
            elif e.get("type") == "turn.completed":
                usage = e.get("usage") or {}
            elif e.get("type") in ("error", "turn.failed"):
                errs.append(json.dumps(e)[:200])
        if code != 0 or not text.strip():
            return _fail(f"exit {code}: {' '.join(errs) or err.strip()[-200:]}")
        return {"text": text, "finish": "stop", "usage": {"prompt": usage.get("input_tokens", 0),
                                                          "completion": usage.get("output_tokens", 0),
                                                          "reasoning": usage.get("reasoning_output_tokens", 0)},
                "cost": 0.0, "provider": "codex", "error": "", "quota": False}

    return _retry(go, retries)


if __name__ == "__main__":
    assert _fail("429 Too Many Requests")["quota"] and not _fail("exit 1: boom")["quota"]
    print("ok")
