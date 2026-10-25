import pytest

from panda_router.heuristic import HeuristicProfiler
from panda_router.profile import TaskProfile
from panda_router.taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, N_DIFFICULTY, N_SKILL_LEVELS, SKILL_AXES

H = HeuristicProfiler()

TASKS = [
    "Fix the typo in README.md",
    "What is a monad?",
    "Refactor the auth middleware to support JWT rotation and add tests across 6 files; there is a race "
    "condition in token refresh that only shows up in production under load.",
    "Build a responsive React settings page matching the attached Figma screenshot.",
    "Prove that the halting problem is undecidable.",
    "",
]


@pytest.mark.parametrize("text", TASKS)
def test_profile_is_valid(text):
    p = H.profile({"text": text})
    assert isinstance(p, TaskProfile)
    assert set(p.category) == set(CATEGORIES) and sum(p.category.values()) == pytest.approx(1.0)
    assert len(p.difficulty) == N_DIFFICULTY and sum(p.difficulty) == pytest.approx(1.0)
    assert set(p.skills) == set(SKILL_AXES)
    for dist in p.skills.values():
        assert len(dist) == N_SKILL_LEVELS and sum(dist) == pytest.approx(1.0)
    assert set(p.flags) == set(FLAGS) and all(0 <= v <= 1 for v in p.flags.values())
    assert set(p.checklist) == set(CHECKLIST_IDS) and all(0 <= v <= 1 for v in p.checklist.values())
    o = p.out_tokens_log10
    assert o["p10"] < o["p50"] < o["p90"]
    TaskProfile.from_dict(p.to_dict())


def test_hard_task_harder_than_easy():
    easy = H.profile({"text": TASKS[0]})
    hard = H.profile({"text": TASKS[2], "context": {"files_in_scope": 6}})
    assert hard.expected_difficulty() > easy.expected_difficulty() + 2
    assert hard.flags["multi_file"] > 0.5


def test_categories():
    assert H.profile({"text": "Fix the crash: TypeError traceback when saving"}).top_category()[0] == "bugfix"
    assert H.profile({"text": TASKS[1]}).top_category()[0] == "chat_simple"
    assert H.profile({"text": TASKS[4]}).top_category()[0] == "math_reasoning"
    assert H.profile({"text": "hello", "kind_hint": "research"}).top_category()[0] == "research"


def test_context_drives_flags():
    p = H.profile({"text": "update the layout", "context": {"has_images": True, "requires_tools": True,
                                                            "estimated_input_tokens": 120_000}})
    assert p.flags["needs_vision"] > 0.5 and p.flags["needs_tools"] > 0.5 and p.flags["long_context"] > 0.5
    assert p.checklist["input_gt_50k_tokens"] > 0.5
    plain = H.profile({"text": "What is a monad?"})
    assert plain.flags["needs_vision"] < 0.5 and plain.flags["long_context"] < 0.5
