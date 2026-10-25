"""Seed grid (category x primary axis x difficulty band x stack x flag combo) and self-made personas."""

import itertools
import random

from ..taxonomy import CATEGORIES

# 40 self-written personas (PersonaHub is CC-BY-NC, so it is not used).
PERSONAS = [
    "vague product manager who describes outcomes, not implementation",
    "terse SRE paging at 3am, writes in fragments",
    "junior developer, unsure of terminology, over-explains",
    "academic researcher who writes precise but long requests",
    "product designer who thinks in screens and Figma frames",
    "data scientist working in notebooks",
    "non-native English speaker (Spanish L1), small grammar mistakes",
    "non-native English speaker (Chinese L1), short sentences",
    "non-native English speaker (German L1), formal tone",
    "staff engineer writing a crisp technical spec with acceptance criteria",
    "startup founder in a hurry, mixes business and tech asks",
    "QA engineer who pastes reproduction steps",
    "security engineer focused on threat models",
    "open-source maintainer triaging an issue",
    "student doing a homework-style exercise",
    "technical writer asking for docs",
    "mobile developer (iOS/Android)",
    "game developer using Unity or Godot",
    "embedded firmware engineer",
    "DevOps engineer automating CI/CD",
    "database administrator",
    "ML engineer training and serving models",
    "frontend developer obsessed with accessibility",
    "backend developer at a fintech",
    "healthcare IT analyst with compliance concerns",
    "orchestrator agent delegating a sub-task to a worker agent, structured bullet format",
    "engineering manager asking for a plan or estimate",
    "customer-support engineer escalating a customer bug",
    "hobbyist programmer on a weekend project",
    "quant analyst who wants math and code",
    "legacy-code maintainer (COBOL/Java 6 era)",
    "copy-pasting user who dumps a stack trace with one line of text",
    "solo consultant writing for a client deliverable",
    "accessibility auditor",
    "performance engineer chasing p99 latency",
    "bioinformatician",
    "marketing analyst with spreadsheets and SQL",
    "teacher preparing course material",
    "code reviewer leaving review requests",
    "lawyer-turned-developer, very literal and careful wording",
]

STACKS = [
    "Python / Django", "Python / FastAPI", "TypeScript / React", "TypeScript / Node.js + Express",
    "Next.js", "Go microservices", "Rust CLI / library", "Java / Spring Boot", "Kotlin / Android",
    "Swift / iOS", "C++ / embedded", "C# / .NET", "Ruby on Rails", "PHP / Laravel",
    "Terraform / AWS", "Kubernetes / Helm", "SQL / PostgreSQL", "pandas / Jupyter",
    "PyTorch / ML", "Bash / shell scripting", "Elixir / Phoenix", "LaTeX / academic writing",
    "spreadsheets / business analytics", "no specific stack (general knowledge)",
]

# Primary skill axes that make sense for each category.
CATEGORY_AXES = {
    "implementation": ["coding", "planning", "ui_frontend", "data_analysis", "reasoning"],
    "bugfix": ["debugging", "coding", "reasoning"],
    "refactor": ["coding", "review", "planning"],
    "test_writing": ["coding", "debugging", "reasoning"],
    "code_review": ["review", "coding", "writing"],
    "research": ["research", "writing", "reasoning"],
    "planning": ["planning", "reasoning", "writing"],
    "docs_writing": ["writing", "coding", "research"],
    "ui_frontend": ["ui_frontend", "coding", "debugging"],
    "data_analysis": ["data_analysis", "math", "coding"],
    "devops_infra": ["coding", "debugging", "planning"],
    "math_reasoning": ["math", "reasoning", "coding"],
    "chat_simple": ["writing", "reasoning", "research"],
}

BANDS = [(1, 2), (3, 4), (5, 6), (7, 8), (9, 10)]

FLAG_COMBOS = [
    [], [], ["needs_tools"], ["needs_tools", "multi_file"], ["needs_vision"], ["long_context"],
    ["ambiguous_spec"], ["needs_web"], ["needs_review"], ["needs_tools", "long_context"],
]

LENGTHS = [
    "one line (40-150 chars)", "one or two short sentences (80-300 chars)", "a short paragraph (300-700 chars)",
    "two or three paragraphs (700-1600 chars)",
    "multi-paragraph with a code snippet, log excerpt or file paths (1500-3500 chars)",
]


def all_cells() -> list[dict]:
    """Every (category, axis, band) base cell; stack/flags/persona/length are sampled per draw."""
    return [
        {"category": c, "axis": a, "band": list(b)}
        for c in CATEGORIES for a in CATEGORY_AXES[c] for b in BANDS
    ]


def sample_cells(n: int, seed: int) -> list[dict]:
    """Even sampling: cycle through shuffled base cells, attach stack/flags/persona/length."""
    rng = random.Random(seed)
    base = all_cells()
    out = []
    order = list(range(len(base)))
    rng.shuffle(order)
    stacks, personas = itertools.cycle(rng.sample(STACKS, len(STACKS))), itertools.cycle(rng.sample(PERSONAS, len(PERSONAS)))
    for i in range(n):
        if i % len(base) == 0 and i:
            rng.shuffle(order)
        cell = dict(base[order[i % len(base)]])
        cell["stack"] = next(stacks)
        cell["flags"] = rng.choice(FLAG_COMBOS)
        cell["persona"] = next(personas)
        cell["length"] = rng.choice(LENGTHS)
        out.append(cell)
    return out
