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


def test_modes_differ_and_max_quality_takes_highest_lower_bound():
    # strong pricey card above every cheaper one: no anchor restriction hides it
    p, cost, strength = np.array([0.52, 0.57, 0.65, 0.40]), np.array([0.0006, 0.005, 0.012, 0.0002]), \
        np.array([7.0, 7.5, 8.7, 6.0])
    picks = {m: v4.choose(m, p, cost, np.zeros(4), strength, 0.5, 0.02, eq_margin=0.05, p_mean=p + 0.1)
             for m in MODES}
    assert picks["max_quality"][0] == 2 and picks["max_quality"][1] == "policy:max_quality"
    assert picks["cheapest_above_threshold"][0] == 0
    assert len({k for k, *_ in picks.values()}) >= 2
    # within Q_TIE of the best lower bound -> the cheaper card
    assert v4.choose("max_quality", np.array([0.65, 0.645]), np.array([0.012, 0.005]), np.zeros(2),
                     np.array([9.0, 7.0]), 0.5, 0.0)[0] == 1


@pytest.mark.parametrize("eq", [0.0, 0.05])
def test_cheapest_respects_min_p_when_any_meets_it(eq):
    p, cost, strength = np.array([0.74, 0.76, 0.60]), np.array([0.001, 0.02, 0.0005]), np.array([7.0, 9.0, 6.0])
    k, by, *_ = v4.choose("cheapest_above_threshold", p, cost, np.zeros(3), strength, 0.75, 0.02, eq_margin=eq,
                          p_mean=np.array([0.80, 0.80, 0.70]))
    assert k == 1 and p[k] >= 0.75 and by.startswith("policy:cheapest_above_threshold")
    # nobody meets it -> highest lower bound, flagged relaxed
    k, by, *_ = v4.choose("cheapest_above_threshold", p - 0.2, cost, np.zeros(3), strength, 0.75, 0.02)
    assert k == 1 and by.endswith(":relaxed")


def test_max_utility_equal_p_never_drops_far_below_pick():
    p, cost, strength = np.array([0.70, 0.55]), np.array([0.01, 0.0001]), np.array([9.0, 6.0])
    k, *_ = v4.choose("max_utility", p, cost, np.zeros(2), strength, 0.5, 0.0, w_cost=0.0, eq_margin=0.05,
                      p_mean=np.array([0.80, 0.79]))  # calibrated P equal, lower bound 0.15 apart -> keep stronger
    assert k == 0


@pytest.mark.parametrize("mode", MODES)
def test_train_a_model_min_p_075(router, mode):
    r = route(router, "train a model", mode=mode, min_p_success=0.75)
    rows = {x["model_id"]: x for x in r["ranking"]}
    pick = rows[r["choice"]["model_id"]]
    best = max(x["p_success_lower"] for x in rows.values())
    if best >= 0.75:
        assert pick["p_success_lower"] >= 0.75
    elif mode != "max_utility":  # nobody clears it -> the highest lower bound (ties within 0.01 -> cheaper)
        assert pick["p_success_lower"] >= best - 0.01
    assert pick["est_cost_usd"] > 0


def test_untrained_cards_get_task_dependent_estimates(router):
    rows = route(router, "train a model")["ranking"]
    unc = [x for x in rows if x["p_source"] == "card_prior"]
    cov_max = max(x["p_success"] for x in rows if x["p_source"] == "success_head")
    assert all(x["p_success"] <= cov_max + 1e-9 for x in unc)
    strong = ["openrouter-gemini-4-argon", "openrouter-kimi-k3.1-pro", "claude-fable-5.1", "openrouter-gpt-6-astra"]
    by_id = {x["card_id"]: (x["p_success"], x["p_success_lower"]) for x in unc}
    assert len({by_id[c] for c in strong if c in by_id}) > 1  # no single flat prior
    other = {x["card_id"]: x["p_success"] for x in route(router, "What does HTTP 418 mean?")["ranking"]}
    assert any(abs(other[c] - by_id[c][0]) > 0.05 for c in strong if c in by_id)  # moves with the task


def test_ladder_cheap_safe_first_then_stronger():
    p, cost, strength = np.array([0.5, 0.6, 0.3]), np.array([0.0005, 0.015, 0.0002]), np.array([7.5, 8.7, 6.0])
    lad = v4.ladder(p, cost, strength, np.zeros((3, 3)), lam=3.0)
    assert lad[:2] == [0, 1] and sorted(lad) == [0, 1, 2]


def test_shrunk_prior_never_exceeds_best_covered():
    ref_q, ref_p = np.array([0.6, 0.8, 0.9]), np.array([0.2, 0.35, 0.4])
    out = v4.shrunk_card_p(np.array([0.999, 0.95, 0.7, 0.1]), ref_q, ref_p, np.zeros(4), -0.94, 0.28)
    assert out[0] <= 0.4 + 1e-12 and out[1] > out[2] > out[3] and out[3] < 0.35
    assert (v4.shrunk_card_p(np.array([0.95]), ref_q, ref_p, np.array([1.0]), -0.94, 0.28) < out[1]).all()


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
        # v4.2: may take the best lower bound (gpt-6.1-sol, ~$0.003, > eq_margin above deepseek); still cheap
        assert 0 < pick["est_cost_usd"] < 0.005 and r["difficulty"]["raw_expected"] <= (2.0 if "status" not in text else 2.5)
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
