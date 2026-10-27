"""v4 router: shipped success head, conservative failure-aware policy, vague-task handling."""

import statistics
import time

import numpy as np
import pytest

from panda_router.matcher import Matcher, load_cards
from panda_router.matcher.policy import DEFAULT_HEAD
from panda_router.router_v4 import policy as v4
from panda_router.serve.router import DEFAULT_ARTIFACTS, Router, load_profiler

MODES = ("cheapest_above_threshold", "max_utility", "max_quality")
PROBES = ("a model trainer", "What does HTTP 418 mean?")

pytestmark = pytest.mark.skipif(not (DEFAULT_ARTIFACTS / "model.int8.onnx").exists() or not DEFAULT_HEAD.exists(),
                                reason="artifacts/panda-router-v4 not present")


@pytest.fixture(scope="module")
def router():
    r = Router(profiler=load_profiler(DEFAULT_ARTIFACTS), log_routes=False)
    r.route({"task": {"text": "warm up"}})
    return r


def route(router, text, **prefs):
    """Full ranking over the default pool (the HTTP schema caps return_top_k at 50, so call the matcher)."""
    task = {"text": text}
    return router.matcher.route({"task": task, "preferences": prefs, "return_top_k": 100}, router.profiler.profile(task))


def test_head_loads_by_default(router):
    m = Matcher()
    assert m.policy == "v4" and m.success_head is not None
    assert {"claude-sonnet-5.5", "openrouter-gpt-6.1-sol"} <= set(m.success_head.cards)
    r = route(router, "Fix the off-by-one in pagination")
    assert r["router"]["success_head"] == m.success_head.name and r["router"]["policy"] == "v4"
    src = {x["card_id"]: x["p_source"] for x in r["ranking"]}
    assert src["openrouter-gpt-6.1-sol"] == "success_head" and src["ollama-gpt-oss-20b"] == "card_prior"


def test_unknown_cards_fall_back_to_conservative_prior(router):
    card = {**load_cards()["claude-opus-5.5"], "id": "my-new-model", "provenance": "estimated",
            "field_provenance": {"skills": "estimated"}}
    pool = [card, "claude-haiku-5.5", "claude-sonnet-5.5", "openrouter-gpt-6.1-sol"]
    r = router.route({"task": {"text": "Write a SQL migration that adds an index"}, "pool": pool, "return_top_k": 4})
    rows = {x["model_id"]: x for x in r["ranking"]}
    assert rows["my-new-model"]["p_source"] == "card_prior"
    assert rows["my-new-model"]["p_success"] < max(rows[c]["p_success"] for c in pool[1:])


@pytest.mark.parametrize("text", PROBES)
@pytest.mark.parametrize("mode", MODES)
def test_no_free_pick_unless_close_to_best_paid(router, text, mode):
    r = route(router, text, mode=mode)
    rows = {x["model_id"]: x for x in r["ranking"]}
    pick = rows[r["choice"]["model_id"]]
    best_paid = max(x["p_success"] for x in rows.values() if x["est_cost_usd"] > 0)
    assert pick["est_cost_usd"] > 0 or pick["p_success"] >= best_paid - 0.05
    assert pick["card_id"] != "ollama-gpt-oss-20b"


def test_vague_request_widens_difficulty(router):
    vague = route(router, "a model trainer")["difficulty"]
    assert vague["raw_expected"] >= 4.0 and vague["expected"] >= vague["raw_expected"] and vague["vagueness"] > 0.5
    assert route(router, "train a model")["difficulty"]["raw_expected"] >= 4.0
    easy = route(router, "What does HTTP 418 mean?")["difficulty"]
    assert easy["raw_expected"] <= 2.0 and easy["vagueness"] < 0.3


def test_latency_under_30ms_total(router):
    texts = ["What does HTTP 418 mean?", "a model trainer", "Refactor the auth middleware and add tests"]
    times = []
    for i in range(30):
        t0 = time.perf_counter()
        router.route({"task": {"text": texts[i % 3]}})
        times.append((time.perf_counter() - t0) * 1000)
    assert statistics.median(times) <= 30.0


@pytest.mark.parametrize("text", ["a model trainer", "Fix the flaky test in CI", "Summarise this paragraph"])
def test_monotone_in_cost_weight(router, text):
    costs = []
    for w in (0.0, 0.02, 0.1, 0.3, 1.0, 3.0, 10.0):
        r = route(router, text, mode="max_utility", weights={"quality": 1.0, "cost": w, "latency": 0.0})
        costs.append(next(x["expected_cost_usd"] for x in r["ranking"] if x["model_id"] == r["choice"]["model_id"]))
    assert all(b <= a + 1e-9 for a, b in zip(costs, costs[1:])), costs


def test_escalation_excludes_failed_and_keeps_head(router):
    req = {"task": {"text": "Debug the race condition in the job scheduler"}, "pool": ["claude-haiku-5.5",
           "claude-sonnet-5.5", "openrouter-gpt-6.1-sol", "openrouter-deepseek-v4.1-flash"]}
    first = router.route(req)
    failed = first["choice"]["model_id"]
    second = router.escalate(req, first, failed)
    assert second["choice"]["model_id"] not in (None, failed)
    assert second["escalation"]["failed_models"] == [failed]
    assert all(x["p_source"] == "success_head" for x in second["ranking"])


# ----------------------------------------------------------------------------- pure policy rules
def test_expected_cost_and_free_guard():
    p, cost, strength = np.array([0.9, 0.5, 0.88]), np.array([0.01, 0.0, 0.0]), np.array([9.0, 5.0, 6.0])
    assert list(v4.free_guard(p, cost)) == [True, False, True]
    e = v4.expected_cost(p, cost, strength, penalty_usd=0.05)
    assert e[0] == pytest.approx(0.01 + 0.1 * (0.0 + 0.05))
    k, by, *_ = v4.choose("cheapest_above_threshold", p, cost, np.zeros(3), strength, 0.5, 0.05)
    assert k in (0, 2) and by == "policy:cheapest_above_threshold"


def test_equal_p_goes_cheaper_exact_cost_ties_go_stronger():
    p, cost, strength = np.array([0.6, 0.6]), np.array([0.001, 0.02]), np.array([6.0, 9.0])
    for mode in MODES:  # roughly equal calibrated P -> never the pricier card
        assert v4.choose(mode, p, cost, np.zeros(2), strength, 0.9, 0.0, eq_margin=0.05)[0] == 0
    # clearly better P is not traded away for price
    assert v4.choose("max_quality", np.array([0.5, 0.7]), cost, np.zeros(2), strength, 0.9, 0.0, eq_margin=0.05)[0] == 1
    # expected cost within the tie tolerance -> stronger
    p, cost = np.array([0.5, 0.5]), np.array([0.010, 0.0101])
    assert v4.choose("cheapest_above_threshold", p, cost, np.zeros(2), strength, 0.4, 0.0)[0] == 1


def test_anchor_is_best_evidence_card_unless_cheaper_is_clearly_safe():
    p, cost, strength = np.array([0.40, 0.55, 0.50]), np.array([0.001, 0.015, 0.03]), np.array([7.0, 8.7, 8.4])
    prior = np.array([0.35, 0.61, 0.55])
    k, by, *_ = v4.choose("max_quality", p, cost, np.zeros(3), strength, 0.8, 0.0, prior=prior)
    assert k == 1 and by.endswith("anchor")
    p2 = np.array([0.85, 0.55, 0.50])
    assert v4.choose("cheapest_above_threshold", p2, cost, np.zeros(3), strength, 0.8, 0.0, prior=prior)[0] == 0


def test_ladder_cheap_safe_first_then_stronger():
    p, cost, strength = np.array([0.5, 0.6, 0.3]), np.array([0.0005, 0.015, 0.0002]), np.array([7.5, 8.7, 6.0])
    lad = v4.ladder(p, cost, strength, np.zeros((3, 3)), lam=3.0)
    assert lad[:2] == [0, 1] and sorted(lad) == [0, 1, 2]


def test_anchored_prior_never_exceeds_best_covered():
    ref_q, ref_p = np.array([0.6, 0.8, 0.9]), np.array([0.2, 0.35, 0.4])
    out = v4.anchored_card_p(np.array([0.99, 0.7, 0.1]), ref_q, ref_p, np.array([0.0, 0.0, 0.0]))
    assert out[0] == pytest.approx(0.4) and 0.2 < out[1] < 0.35 and out[2] == pytest.approx(0.2)


# ----------------------------------------------------------------------------- calibrated P, review probes
def test_head_is_calibrated_on_train_val():
    head = Matcher().success_head.params
    cal = head["calibration"]["calibrated_nested_cv"]
    assert cal["ece"] <= 0.03 and abs(cal["mean_p"] - head["calibration"]["pass_rate"]) <= 0.02
    assert 0.02 <= cal["mean_margin"] <= 0.10  # modest explicit over-estimation margin
    assert set(head["platt"]) == set(head["cards"]) == set(head["base_rate"])


@pytest.mark.parametrize("mode", MODES)
def test_review_probes(router, mode):
    cards = load_cards()
    for text in ("What does HTTP status 418 mean?", "What does HTTP 418 mean?"):
        r = route(router, text, mode=mode)
        pick = next(x for x in r["ranking"] if x["model_id"] == r["choice"]["model_id"])
        assert pick["est_cost_usd"] < 0.002 and r["difficulty"]["raw_expected"] <= (2.0 if "status" not in text else 2.5)
        assert 0 < pick["p_success_lower"] <= pick["p_success"] == r["choice"]["confidence"] < 1
    r = route(router, "a model trainer", mode=mode)
    pick = next(x for x in r["ranking"] if x["model_id"] == r["choice"]["model_id"])
    assert pick["est_cost_usd"] > 0 and r["difficulty"]["expected"] >= 4.0
    r = route(router, "Implement a lock-free MPMC queue in Rust and write a linearizability proof", mode=mode)
    card = cards[next(x["card_id"] for x in r["ranking"] if x["model_id"] == r["choice"]["model_id"])]
    assert card["skills"]["coding"]["theta"] >= 8.5, card["id"]
    assert "strict grading" in r["router"]["p_success_note"]


def test_escalation_ladder_and_escalate_follows_it(router):
    req = {"task": {"text": "Write a Python function that parses ISO-8601 durations"}}
    first = router.route(req)
    lad = [x["model_id"] for x in first["escalation_ladder"]]
    assert len(lad) == 3 == len(set(lad))
    cards = load_cards()
    assert cards[lad[0]]["cost"]["output_per_mtok"] > 0  # $0 guard on the first rung
    failed = first["choice"]["model_id"]
    second = router.escalate(req, first, failed)
    assert second["choice"]["model_id"] == next(m for m in lad if m != failed)
    assert second["choice"]["decided_by"] == "escalation_ladder"
