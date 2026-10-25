"""Rule-based TaskProfile: fallback when no trained profiler is available, and the baseline to beat."""

from __future__ import annotations

import math
import re

from .profile import Profiler, TaskProfile
from .taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, N_DIFFICULTY, N_SKILL_LEVELS, SKILL_AXES


def _rx(*words: str) -> re.Pattern:
    return re.compile(r"\b(?:" + "|".join(words) + r")", re.I)


CATEGORY_RX: dict[str, re.Pattern] = {
    "implementation": _rx("implement", "add (?:a |an |the )?(?:new )?(?:feature|endpoint|function|method|class|option|flag|support)",
                          "build", "create", "write (?:a|an) (?:function|script|module|cli|service)", "support for"),
    "bugfix": _rx("fix", "bug", "error", "exception", "crash", "fails?", "failing", "broken", "traceback",
                  "regression", "doesn'?t work", "not working", "stack ?trace", "segfault"),
    "refactor": _rx("refactor", "clean ?up", "restructure", "rename", "extract", "simplify", "deduplicate",
                    "split (?:up|into)", "migrate", "modernize"),
    "test_writing": _rx("unit tests?", "write tests?", "add tests?", "test coverage", "pytest", "jest",
                        "integration tests?", "e2e"),
    "code_review": _rx("review", "critique", "audit", "look over", "feedback on", "pull request", "pr #?\\d"),
    "research": _rx("research", "investigate", "compare", "survey", "find out", "what are the options",
                    "evaluate", "literature", "state of the art"),
    "planning": _rx("plan", "design doc", "roadmap", "architecture", "break (?:it )?down", "milestones",
                    "strategy", "proposal", "rfc"),
    "docs_writing": _rx("document", "docs?\\b", "readme", "docstring", "changelog", "write-?up", "tutorial",
                        "blog post", "explain in writing"),
    "ui_frontend": _rx("ui", "frontend", "css", "react", "vue", "svelte", "tailwind", "component", "layout",
                       "button", "page", "html", "responsive", "figma", "styling"),
    "data_analysis": _rx("dataset", "csv", "dataframe", "pandas", "sql", "query", "metrics", "analy[sz]",
                         "chart", "plot", "statistics", "aggregate", "etl"),
    "devops_infra": _rx("deploy", "docker", "kubernetes", "k8s", "terraform", "ci/?cd", "pipeline", "github actions",
                        "nginx", "helm", "aws", "gcp", "azure", "infra", "ansible"),
    "math_reasoning": _rx("prove", "proof", "theorem", "lemma", "integral", "derivative", "equation",
                          "probability", "combinatori", "complexity of", "big-?o", "undecidab", "halting problem", "asymptotic"),
    "chat_simple": _rx("what is", "what's", "who is", "hello", "hi\\b", "thanks", "define", "quick question",
                       "tl;?dr", "summari[sz]e", "translate"),
}

HARD_RX = _rx("race condition", "concurren", "distributed", "deadlock", "memory leak", "security", "crypto",
              "authenticat", "authori[sz]", "migration", "architecture", "performance", "optimi[sz]",
              "latency", "scal", "compiler", "kernel", "proof", "consensus", "lock-?free", "flaky",
              "intermittent", "root cause", "prove", "undecidab", "np-hard", "production", "zero-?downtime", "backward[s]? compat")
EASY_RX = _rx("typo", "rename", "one-?liner", "hello world", "simple", "trivial", "quick", "spelling",
              "bump (?:the )?version", "small change", "just ", "minor")
TOOLS_RX = _rx("run", "test", "repo", "file", "deploy", "install", "commit", "build", "execute", "terminal",
               "shell", "debug", "reproduce", "ci\\b")
VISION_RX = _rx("screenshot", "image", "png", "jpe?g", "figma", "mockup", "diagram", "picture", "attached design")
WEB_RX = _rx("search the web", "browse", "look up", "latest", "online", "https?://", "google", "news")
LONG_RX = _rx("entire (?:code ?base|repo)", "whole (?:code ?base|repo)", "large log", "huge file", "all files",
              "monorepo", "100k", "long document")
MULTI_RX = _rx("across", "multiple files", "several files", "codebase-?wide", "every module", "all services")
VAGUE_RX = _rx("somehow", "something like", "make it better", "improve", "etc", "whatever", "nice", "clean")
CRITERIA_RX = _rx("should return", "must", "acceptance", "expected output", "so that", "passes?", "given .* when")
SECURITY_RX = _rx("security", "auth", "password", "secret", "token", "crypto", "permission", "oauth", "jwt", "xss",
                  "csrf", "injection")
STAKES_RX = _rx("production", "prod\\b", "customer", "payment", "billing", "data loss", "outage", "money")
CODE_HINT_RX = re.compile(r"`|\bdef |\bclass |\bfunction\b|\.py\b|\.ts\b|\.js\b|\.go\b|\.rs\b|\{|\}|=>|::", re.I)

# Per-category relevant axes with level offsets relative to the difficulty point estimate.
CATEGORY_AXES: dict[str, dict[str, float]] = {
    "implementation": {"coding": 0, "planning": -2, "debugging": -2.5, "reasoning": -1.5},
    "bugfix": {"debugging": 0, "coding": -1, "reasoning": -1},
    "refactor": {"coding": 0, "review": -1.5, "planning": -2},
    "test_writing": {"coding": -0.5, "debugging": -2, "review": -2},
    "code_review": {"review": 0, "coding": -1.5, "reasoning": -1.5},
    "research": {"research": 0, "reasoning": -1, "writing": -2},
    "planning": {"planning": 0, "reasoning": -0.5, "writing": -2},
    "docs_writing": {"writing": 0, "coding": -3, "research": -3},
    "ui_frontend": {"ui_frontend": 0, "coding": -1},
    "data_analysis": {"data_analysis": 0, "coding": -1.5, "math": -2.5},
    "devops_infra": {"coding": -0.5, "debugging": -1, "planning": -2},
    "math_reasoning": {"math": 0, "reasoning": -0.5},
    "chat_simple": {"writing": -1, "reasoning": -1.5},
}
OUT_P50: dict[str, float] = {
    "implementation": 3.3, "bugfix": 3.0, "refactor": 3.4, "test_writing": 3.3, "code_review": 2.9,
    "research": 3.1, "planning": 3.0, "docs_writing": 3.1, "ui_frontend": 3.4, "data_analysis": 3.0,
    "devops_infra": 3.0, "math_reasoning": 2.9, "chat_simple": 2.3,
}


def _discrete_gaussian(center: float, sigma: float, n: int, start: int) -> list[float]:
    w = [math.exp(-0.5 * ((start + i - center) / sigma) ** 2) for i in range(n)]
    s = sum(w)
    return [x / s for x in w]


def _sigmoid(x: float) -> float:
    return 1.0 / (1.0 + math.exp(-x))


class HeuristicProfiler(Profiler):
    name = "heuristic"

    def profile(self, task: dict) -> TaskProfile:
        text = task.get("text") or ""
        ctx = task.get("context") or {}
        words = len(text.split())
        files = int(ctx.get("files_in_scope") or 0)
        tokens = int(ctx.get("estimated_input_tokens") or (len(text) // 4))
        codey = bool(CODE_HINT_RX.search(text)) or bool(ctx.get("repo_languages"))

        # Category: keyword hits -> softmax.
        raw = {c: 0.0 for c in CATEGORIES}
        for c, rx in CATEGORY_RX.items():
            raw[c] += 2.0 * min(len(rx.findall(text)), 3)
        if hint := task.get("kind_hint"):
            if hint in raw:
                raw[hint] += 3.0
        if max(raw.values()) == 0:
            raw["implementation" if codey else "chat_simple"] += 2.5
        if codey:
            raw["chat_simple"] -= 1.0
        exps = {c: math.exp(v) for c, v in raw.items()}
        z = sum(exps.values())
        category = {c: v / z for c, v in exps.items()}

        # Difficulty point estimate.
        d = 3.0
        d += 1.0 * (words > 120) + 1.0 * (words > 400)
        d += 1.0 * (files > 3) + 1.0 * (files > 10)
        d += 1.0 * (tokens > 50_000)
        d += min(len(set(m.lower() for m in HARD_RX.findall(text))), 3) * 1.0
        d -= 1.5 * bool(EASY_RX.search(text))
        d -= 1.0 * (category["chat_simple"] > 0.5)
        d += 0.5 * (category["math_reasoning"] > 0.4)
        d = min(max(d, 1.0), 10.0)
        difficulty = _discrete_gaussian(d, 1.1, N_DIFFICULTY, 1)

        # Skills: category-weighted expected level per axis -> discretised Gaussian over 0..10.
        skills = {}
        for axis in SKILL_AXES:
            lvl = sum(p * max(0.0, d + CATEGORY_AXES[c][axis]) for c, p in category.items() if axis in CATEGORY_AXES[c])
            lvl = min(lvl, 10.0)
            skills[axis] = _discrete_gaussian(lvl, 1.2, N_SKILL_LEVELS, 0)

        # Flags.
        has_images = bool(ctx.get("has_images"))
        flags = {
            "needs_tools": 0.95 if ctx.get("requires_tools") else _sigmoid(-1.0 + 1.0 * len(TOOLS_RX.findall(text)) + 1.0 * codey),
            "needs_vision": 0.97 if has_images else (0.7 if VISION_RX.search(text) else 0.03),
            "long_context": 0.95 if tokens > 100_000 else (0.7 if tokens > 50_000 or LONG_RX.search(text) else 0.05),
            "needs_review": min(0.95, 0.15 + 0.3 * bool(SECURITY_RX.search(text)) + 0.3 * bool(STAKES_RX.search(text)) + 0.04 * max(0, d - 5)),
            "ambiguous_spec": 0.7 if (words < 8 and not codey) or VAGUE_RX.search(text) else 0.15,
            "multi_file": 0.9 if files > 3 else (0.65 if MULTI_RX.search(text) else 0.1),
            "needs_web": 0.75 if WEB_RX.search(text) else 0.05,
        }
        assert set(flags) == set(FLAGS)

        cp = category
        code_cats = cp["implementation"] + cp["bugfix"] + cp["refactor"] + cp["test_writing"] + cp["ui_frontend"] + cp["devops_infra"]
        checklist = {
            "edits_code": min(0.98, code_cats + 0.3 * codey),
            "touches_gt3_files": flags["multi_file"],
            "new_feature": cp["implementation"] + 0.5 * cp["ui_frontend"],
            "has_failing_behavior": cp["bugfix"],
            "needs_root_cause": cp["bugfix"] * (0.4 + 0.1 * max(0, d - 4)),
            "needs_run_commands": flags["needs_tools"],
            "needs_browser_or_web": flags["needs_web"],
            "has_images": flags["needs_vision"],
            "input_gt_50k_tokens": 0.95 if tokens > 50_000 else 0.05,
            "concurrency_or_distributed": 0.8 if re.search(r"concurren|distributed|race condition|deadlock|lock-?free", text, re.I) else 0.05,
            "security_sensitive": 0.8 if SECURITY_RX.search(text) else 0.05,
            "formal_math_or_proof": cp["math_reasoning"],
            "domain_expertise": 0.5 if d >= 7 else 0.15,
            "clear_acceptance_criteria": 0.7 if CRITERIA_RX.search(text) else 0.3,
            "undefined_terms": flags["ambiguous_spec"] * 0.7,
            "design_decisions": cp["planning"] + 0.3 * (d >= 7),
            "visual_ui_work": cp["ui_frontend"],
            "writes_prose": cp["docs_writing"] + cp["research"] * 0.6 + cp["chat_simple"] * 0.8 + cp["planning"] * 0.5,
            "data_processing": cp["data_analysis"],
            "infra_config": cp["devops_infra"],
            "multi_step_plan": min(0.95, 0.1 + 0.1 * max(0, d - 4) + cp["planning"]),
            "reviews_existing_work": cp["code_review"],
            "trivial_one_liner": 0.8 if d <= 2 else (0.3 if d <= 3 else 0.05),
            "high_stakes": 0.7 if STAKES_RX.search(text) else 0.1,
        }
        checklist = {k: round(min(max(float(checklist[k]), 0.0), 1.0), 4) for k in CHECKLIST_IDS}

        p50 = sum(p * OUT_P50[c] for c, p in cp.items()) + 0.08 * (d - 5)
        out = {"p10": round(p50 - 0.45, 3), "p50": round(p50, 3), "p90": round(p50 + 0.5, 3)}
        return TaskProfile(category=category, difficulty=difficulty, skills=skills,
                           flags={k: round(float(v), 4) for k, v in flags.items()},
                           checklist=checklist, out_tokens_log10=out)
