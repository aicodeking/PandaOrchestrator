import json
import statistics
import time
from pathlib import Path

import numpy as np
import pytest

from panda_router.matcher import (DEFAULT_CARDS_DIR, Matcher, load_cards, schema_errors, success_probabilities)
from panda_router.profile import TaskProfile
from panda_router.taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES


def point(center: int, n: int, start: int) -> list[float]:
    v = [0.0] * n
    v[center - start] = 1.0
    return v


def make_profile(skills=None, diff=5, flags=None, out_p50=3.0) -> TaskProfile:
    skills = {"coding": 6} if skills is None else skills
    d = point(diff, 10, 1) if isinstance(diff, int) else list(diff)
    return TaskProfile(
        category={c: (1.0 if c == "implementation" else 0.0) for c in CATEGORIES},
        difficulty=d,
        skills={a: point(int(skills.get(a, 0)), 11, 0) for a in SKILL_AXES},
        flags={f: 0.0 for f in FLAGS} | (flags or {}),
        checklist={c: 0.0 for c in CHECKLIST_IDS},
        out_tokens_log10={"p10": out_p50 - 0.4, "p50": out_p50, "p90": out_p50 + 0.4},
    )


def mk_card(id, theta, se=0.3, cin=1.0, cout=5.0, ctx=200_000, tools=True, image=True, local=False, a=1.2):
    return {"id": id, "description": f"test card {id}", "skills": {ax: {"theta": theta, "se": se} for ax in SKILL_AXES},
            "discrimination": a, "modalities": {"input": ["text", "image"] if image else ["text"], "output": ["text"]},
            "features": {"tools": tools}, "limits": {"context_tokens": ctx},
            "cost": {"input_per_mtok": cin, "output_per_mtok": cout},
            "latency": {"ttft_ms_p50": 1000, "tokens_per_sec": 50}, "local": local}


STRONG = mk_card("strong", 9.0, cin=10, cout=50)
MID = mk_card("mid", 7.0, cin=1, cout=5)
WEAK = mk_card("weak", 4.0, cin=0.1, cout=0.5)
POOL = [STRONG, MID, WEAK]


def req(pool=POOL, **kw):
    r = {"task": {"text": "do the thing", "context": {"estimated_input_tokens": 2000}}, "pool": pool,
         "preferences": {"mode": "cheapest_above_threshold"}}  # these tests exercise the threshold policy
    r.update(kw)
    return r


@pytest.fixture(scope="module")
def m():
    return Matcher(calibration=False, policy="v3", success_head=None)  # v3 card policy; v4: tests/test_router_v4.py


# ----------------------------------------------------------------------------- cards / schemas
def test_all_cards_validate_against_schema():
    files = sorted(Path(DEFAULT_CARDS_DIR).glob("*.json"))
    assert len(files) >= 17
    for f in files:
        card = json.loads(f.read_text())
        assert schema_errors(card, "model_card") == [], f.name
        assert f.stem == card["id"]
        if card.get("provenance") == "estimated":
            assert max(s["se"] for s in card["skills"].values()) >= 1.5, card["id"]


def test_roster_complete_and_local_card():
    cards = load_cards()
    expected = {"claude-opus-5.5", "claude-sonnet-5.5", "claude-haiku-5.5", "claude-fable-5.1", "codex-gpt-6-luna",
                "codex-gpt-5.6-terra", "codex-gpt-5.6-luna", "kimi-k3", "kimi-k2.7-code", "kimi-k2.7-code-highspeed",
                "glm-5.1", "glm-5-turbo", "glm-4.7", "glm-4.5-air", "grok-4.6", "grok-4.5", "ollama-gemma4-26b"}
    assert expected <= set(cards)
    local = [c for c in cards.values() if c.get("local")]
    assert "ollama-gemma4-26b" in {c["id"] for c in local}
    assert all(c["cost"]["input_per_mtok"] == 0 and c["cost"]["output_per_mtok"] == 0 for c in local)
    assert not any(c["model"].endswith(":free") for c in cards.values())  # free tiers live in cards/optional/


def test_invalid_card_rejected(m):
    bad = dict(MID)
    bad.pop("limits")
    with pytest.raises(ValueError):
        m.route(req(pool=[bad]), make_profile())


# ----------------------------------------------------------------------------- P(success) math
def _p(theta, se=0.3, diff=5, skills=None, a=1.2):
    prof = make_profile(skills=skills, diff=diff)
    th = np.full((1, len(SKILL_AXES)), float(theta))
    s = np.full((1, len(SKILL_AXES)), float(se))
    return float(success_probabilities(prof.skills, prof.difficulty, th, s, np.array([a]))[0][0])


def test_p_monotonic_in_theta():
    ps = [_p(t) for t in np.linspace(0, 10, 21)]
    assert all(b > a for a, b in zip(ps, ps[1:]))
    assert ps[0] < 0.05 and ps[-1] > 0.95


def test_p_decreasing_in_difficulty():
    ps = [_p(7.0, diff=d) for d in range(1, 11)]
    assert all(b < a for a, b in zip(ps, ps[1:]))


def test_matches_closed_form_without_uncertainty():
    # se -> 0, no bottleneck (skill need below theta): P = sigmoid(a (theta - b)).
    p = _p(7.0, se=1e-6, diff=5, skills={"coding": 3})
    assert p == pytest.approx(1 / (1 + np.exp(-1.2 * 2.0)), abs=1e-6)


def test_bottleneck_penalty_lowers_p():
    assert _p(6.0, skills={"coding": 9}, diff=4) < _p(6.0, skills={"coding": 3}, diff=4)


def test_larger_se_pulls_toward_middle():
    hi = [_p(8.0, se=s, diff=5, skills={"coding": 3}) for s in (0.1, 1.0, 2.0, 4.0)]
    lo = [_p(3.0, se=s, diff=5, skills={"coding": 3}) for s in (0.1, 1.0, 2.0, 4.0)]
    assert all(b < a for a, b in zip(hi, hi[1:])) and hi[-1] > 0.5
    assert all(b > a for a, b in zip(lo, lo[1:])) and lo[-1] < 0.5


def test_zero_skills_uses_reasoning_axis():
    prof = make_profile(skills={})
    th = np.full((1, len(SKILL_AXES)), 2.0)
    th[0, SKILL_AXES.index("reasoning")] = 9.0
    p = success_probabilities(prof.skills, prof.difficulty, th, np.full_like(th, 0.3), np.array([1.2]))[0][0]
    assert p > 0.9


def test_deterministic(m):
    a = m.route(req(), make_profile(), trace_id="r_x")
    b = m.route(req(), make_profile(), trace_id="r_x")
    a["router"].pop("latency_ms"), b["router"].pop("latency_ms")
    assert a == b


# ----------------------------------------------------------------------------- filters
def reasons(resp):
    return {f["model_id"]: f["reason"] for f in resp["filtered_out"]}


def test_filters(m):
    pool = [mk_card("notools", 8, tools=False), mk_card("noimg", 8, image=False), mk_card("small", 8, ctx=10_000),
            mk_card("pricey", 8, cin=100, cout=500), mk_card("local", 8, cin=0, cout=0, local=True), MID]
    r = m.route(req(pool=pool, constraints={"max_cost_usd": 0.5, "exclude": ["mid"]}),
                make_profile(flags={"needs_tools": 0.9, "needs_vision": 0.8}))
    rs = reasons(r)
    assert rs["notools"] == "profile:needs_tools"
    assert rs["noimg"] == "profile:needs_vision"
    assert rs["pricey"] == "constraint:max_cost_usd"
    assert rs["mid"] == "constraint:exclude"
    assert "small" not in rs  # 2000 * 1.2 < 10k
    big = req(pool=pool)
    big["task"]["context"]["estimated_input_tokens"] = 9000
    assert "limit:context" in reasons(m.route(big, make_profile()))["small"]
    r = m.route(req(pool=pool, constraints={"local_only": True, "require": ["tools"]}), make_profile())
    assert r["choice"]["model_id"] == "local"
    assert reasons(r)["notools"] == "constraint:local_only;constraint:require=tools"
    assert all(x["model_id"] not in reasons(r) for x in r["ranking"])


def test_flags_below_half_do_not_filter(m):
    r = m.route(req(pool=[mk_card("notools", 8, tools=False)]), make_profile(flags={"needs_tools": 0.4}))
    assert r["choice"]["model_id"] == "notools"


def test_unknown_pool_id_reported(m):
    r = m.route(req(pool=["claude-opus-5.5", "no-such-model"]), make_profile())
    assert reasons(r)["no-such-model"] == "unknown_model"
    assert r["choice"]["model_id"] == "claude-opus-5.5"


# ----------------------------------------------------------------------------- modes / floor / fallback
def test_cheapest_above_threshold_picks_mid(m):
    r = m.route(req(), make_profile())
    assert r["choice"]["model_id"] == "mid"
    assert r["choice"]["decided_by"] == "policy:cheapest_above_threshold"
    assert r["choice"]["confidence"] >= 0.75


def test_max_quality_picks_strong(m):
    r = m.route(req(preferences={"mode": "max_quality"}), make_profile())
    assert r["choice"]["model_id"] == "strong"


def test_max_utility_tradeoff(m):
    cheap = m.route(req(preferences={"mode": "max_utility", "weights": {"quality": 1, "cost": 1.0, "latency": 0}}),
                    make_profile())
    assert cheap["choice"]["model_id"] == "mid"
    best = m.route(req(preferences={"mode": "max_utility", "weights": {"quality": 1, "cost": 0, "latency": 0}}),
                   make_profile())
    assert best["choice"]["model_id"] == "strong"


def test_threshold_relaxes_when_none_above(m):
    r = m.route(req(preferences={"mode": "cheapest_above_threshold", "min_p_success": 0.999}), make_profile())
    assert r["choice"]["model_id"] == "strong"
    assert r["choice"]["decided_by"].endswith("relaxed_to_max_quality")
    assert not r["fallback"]["triggered"]


def test_floor_fallback_default_model(m):
    pool = [MID, WEAK, mk_card("claude-opus-5.5", 6.0, cin=4, cout=20)]
    r = m.route(req(pool=pool), make_profile(diff=10, skills={"coding": 9}))
    assert r["fallback"]["triggered"]
    assert r["choice"]["model_id"] == "claude-opus-5.5"
    assert r["choice"]["decided_by"] == "fallback:default_model"


def test_floor_fallback_best_available_when_default_missing(m):
    r = m.route(req(pool=[MID, WEAK]), make_profile(diff=10, skills={"coding": 9}))
    assert r["fallback"]["triggered"] and r["fallback"]["default_model"] is None
    assert r["choice"]["model_id"] == "mid"
    assert r["choice"]["decided_by"] == "fallback:best_available"


def test_all_filtered(m):
    r = m.route(req(constraints={"local_only": True}), make_profile())
    assert r["choice"]["model_id"] is None and r["fallback"]["triggered"]
    assert schema_errors(r, "route_response") == []


def test_response_schema_and_ranking(m):
    r = m.route(req(return_top_k=2, questions=["choice", "profile"]), make_profile())
    assert schema_errors(r, "route_response") == []
    assert len(r["ranking"]) == 2 and r["ranking"][0]["model_id"] == r["choice"]["model_id"]
    assert "profile" in r
    assert r["router"]["pool_hash"]


def test_expected_cost_uses_out_tokens_p50(m):
    r = m.route(req(pool=[MID], return_top_k=1), make_profile(out_p50=3.0))
    assert r["ranking"][0]["est_cost_usd"] == pytest.approx((2000 * 1 + 1000 * 5) / 1e6)
    assert r["ranking"][0]["est_latency_ms"] == pytest.approx(1000 + 1000 / 50 * 1000)


# ----------------------------------------------------------------------------- escalation
def test_escalate_shifts_difficulty_up_and_excludes_failed(m):
    prof = make_profile(diff=[0, 0, 0.05, 0.2, 0.5, 0.2, 0.05, 0, 0, 0])
    first = m.route(req(), prof)
    failed = first["choice"]["model_id"]
    assert failed == "mid"
    second = m.escalate(req(), prof, first, failed)
    prior, post = np.array(second["escalation"]["prior_difficulty"]), np.array(second["escalation"]["posterior_difficulty"])
    lv = np.arange(1, 11)
    assert post @ lv > prior @ lv
    assert second["difficulty"]["expected"] > first["difficulty"]["expected"]
    assert second["choice"]["model_id"] != failed
    assert reasons(second)[failed] == "escalation:failed"
    assert second["escalation"]["failed_models"] == ["mid"]
    assert second["escalation"]["parent_trace_id"] == first["trace_id"]
    assert schema_errors(second, "route_response") == []
    # Second failure compounds.
    third = m.escalate(req(), prof, second, second["choice"]["model_id"])
    assert set(third["escalation"]["failed_models"]) == {"mid", second["choice"]["model_id"]}


def test_escalate_unknown_failed_model(m):
    with pytest.raises(ValueError):
        m.escalate(req(), make_profile(), m.route(req(), make_profile()), "nope")


# ----------------------------------------------------------------------------- exploration
def test_exploration_logs_propensity(m):
    pool = [mk_card("a", 8.0), mk_card("b", 8.0), mk_card("c", 8.0)]
    seen, props = set(), []
    for seed in range(60):
        r = m.route(req(pool=pool, preferences={"mode": "max_utility", "explore_epsilon": 0.5, "seed": seed}),
                    make_profile())
        seen.add(r["choice"]["model_id"])
        props.append(r["choice"]["propensity"])
        assert 0 < r["choice"]["propensity"] <= 1
    assert len(seen) > 1
    r0 = m.route(req(pool=pool, preferences={"mode": "max_utility"}), make_profile())
    assert r0["choice"]["propensity"] == 1.0 and not r0["choice"]["explored"]


# ----------------------------------------------------------------------------- latency
def test_latency_under_2ms_for_20_cards(m):
    extra = [mk_card(f"x{i}", 5 + i * 0.3) for i in range(3)]
    pool = list(load_cards().values())[:17] + extra
    assert len(pool) >= 20
    r = req(pool=pool)
    prof = make_profile()
    for _ in range(20):
        m.route(r, prof)
    times = []
    for _ in range(200):
        t = time.perf_counter()
        m.route(r, prof)
        times.append((time.perf_counter() - t) * 1000)
    assert statistics.median(times) < 2.0, statistics.median(times)


def test_pool_aliases_resolve_and_echo_caller_ids(m):
    pool = ["claude/sonnet-5-5", "anthropic/claude-sonnet-5.5", "claude-sonet-5.5-latest-typo", "deepseek/deepseek-v4-flash",
            "Gemma4:26B", "gpt-6-sol", "gpt-9-sol", "totally-unknown-model"]
    resp = m.route(req(pool=pool, return_top_k=50), make_profile())
    got = {r["model_id"]: r["card_id"] for r in resp["ranking"]}
    assert got["claude/sonnet-5-5"] == "claude-sonnet-5.5"          # caller's string echoed, real card used
    assert got["deepseek/deepseek-v4-flash"] == "openrouter-deepseek-v4-flash"
    assert got["Gemma4:26B"] == "ollama-gemma4-26b"
    assert got["gpt-6-sol"] == "openrouter-gpt-6-sol"               # not gpt-6.1-sol
    assert "anthropic/claude-sonnet-5.5" not in got                 # same card as the first alias
    unknown = {f["model_id"] for f in resp["filtered_out"] if f["reason"] == "unknown_model"}
    assert {"gpt-9-sol", "totally-unknown-model"} <= unknown        # wrong version / nothing close


def test_alias_shared_key_needs_exact_model_or_prefix():
    from panda_router.matcher.policy import _alias_index, resolve_alias
    cards = load_cards()
    idx = _alias_index(cards)
    assert resolve_alias("qwen3.8:27b", cards, idx) == "ollama-qwen3.8-27b"          # exact pull name
    assert resolve_alias("qwen/qwen3.8-27b", cards, idx) == "openrouter-qwen3.8-27b"  # exact slug
    assert resolve_alias("ollama/qwen3.8-27b", cards, idx) == "ollama-qwen3.8-27b"    # vendor prefix
    assert resolve_alias("qwen3.8-27b", cards, idx) is None                           # truly ambiguous


def test_newer_version_wins_older_only_when_alone(m):
    easy = make_profile(diff=2)
    both = m.route(req(pool=["grok-4.5", "grok-4.6"]), easy)
    assert both["choice"]["model_id"] == "grok-4.6"
    assert {"model_id": "grok-4.5", "reason": "superseded_by:grok-4.6"} in both["filtered_out"]
    assert m.route(req(pool=["grok-4.5"]), easy)["choice"]["model_id"] == "grok-4.5"
    # successor filtered out (excluded) -> the older version is allowed back in
    excl = m.route(req(pool=["grok-4.5", "grok-4.6"], constraints={"exclude": ["grok-4.6"]}), easy)
    assert excl["choice"]["model_id"] == "grok-4.5"
    # works with caller aliases too, and the reason names the caller's string
    alias = m.route(req(pool=["x-ai/grok-4-5", "grok/4.6"]), easy)
    assert alias["choice"]["model_id"] == "grok/4.6"
    assert {"model_id": "x-ai/grok-4-5", "reason": "superseded_by:grok/4.6"} in alias["filtered_out"]


def test_supersedes_links_point_to_real_cards():
    cards = load_cards()
    for c in cards.values():
        for old in c.get("supersedes", ()):
            assert old in cards and old != c["id"], (c["id"], old)


def test_pricier_successor_competes_normally(m):
    easy = make_profile(diff=2)
    r = m.route(req(pool=["glm-4.7", "glm-5.1"]), easy)   # 5.1 costs ~2x: no automatic win
    assert not any(f["reason"].startswith("superseded_by") for f in r["filtered_out"])
    assert r["choice"]["model_id"] == "glm-4.7"            # cheaper and good enough for an easy task
