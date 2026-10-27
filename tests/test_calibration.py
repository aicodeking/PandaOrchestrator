import json

import numpy as np
import pytest

from panda_router.matcher import Matcher as _Matcher
from panda_router.matcher.calibration import DEFAULT_PATH, load_calibration, transform
from panda_router.matcher.core import p_by_level
from panda_router.profile import TaskProfile
from panda_router.taxonomy import CATEGORIES, CHECKLIST_IDS, FLAGS, SKILL_AXES


def Matcher(**kw) -> _Matcher:
    """Card-P calibration is a v3-policy feature; the v4 head replaces P for the cards it was trained on."""
    return _Matcher(policy="v3", success_head=None, **kw)

POOL = ["openrouter-qwen3.8-flash", "openrouter-deepseek-v4.1-flash", "openrouter-gpt-6.1-sol"]


def profile(diff: int) -> TaskProfile:
    one = lambda i, n: [1.0 if j == i else 0.0 for j in range(n)]  # noqa: E731
    return TaskProfile(category={c: float(c == "implementation") for c in CATEGORIES}, difficulty=one(diff - 1, 10),
                       skills={a: one(6 if a == "coding" else 0, 11) for a in SKILL_AXES},
                       flags={f: 0.0 for f in FLAGS}, checklist={c: 0.0 for c in CHECKLIST_IDS})


def p_of(m: _Matcher, diff: int) -> dict[str, float]:
    r = m.route({"task": {"text": "x", "context": {}}, "pool": POOL, "return_top_k": 5}, profile(diff))
    return {row["model_id"]: row["p_success"] for row in r["ranking"]}


def test_shipped_calibration_loads_with_provenance(monkeypatch):
    monkeypatch.delenv("PANDA_ROUTER_CALIBRATION", raising=False)
    blob = json.loads(DEFAULT_PATH.read_text())
    assert {"data", "date", "n_cells", "profiler"} <= set(blob["provenance"])
    cal = load_calibration(True)
    assert cal["slope"] > 0 and cal["a_mult"] > 0 and Matcher(calibration=True).calibration == cal
    assert Matcher().calibration is None  # opt-in: off by default
    monkeypatch.setenv("PANDA_ROUTER_CALIBRATION", "on")
    assert Matcher().calibration == cal


def test_off_switch_env_and_arg(monkeypatch):
    raw = Matcher(calibration=False)
    assert raw.calibration is None
    monkeypatch.setenv("PANDA_ROUTER_CALIBRATION", "off")
    assert Matcher().calibration is None
    assert p_of(Matcher(), 5) == p_of(raw, 5)
    assert p_of(Matcher(calibration=True), 5) != p_of(raw, 5)  # explicit arg beats env


def test_identity_params_reproduce_raw_matcher():
    assert p_of(Matcher(calibration={"delta": 0.0, "slope": 1.0, "a_mult": 1.0}), 6) == p_of(Matcher(calibration=False), 6)


def test_calibrated_p_in_unit_interval_and_monotone():
    m = Matcher(calibration=True)
    ps = [p_of(m, d) for d in range(1, 11)]
    for model in POOL:
        seq = [p[model] for p in ps]
        assert all(0.0 <= x <= 1.0 for x in seq)
        assert all(a >= b for a, b in zip(seq, seq[1:])), (model, seq)  # harder task -> lower P
    for p in ps:  # stronger card -> higher P at every difficulty
        assert p["openrouter-gpt-6.1-sol"] >= p["openrouter-qwen3.8-flash"]


def test_transform_matches_rescaled_difficulty():
    """P_cal(b) must equal sigmoid(a * a_mult * (z + shift - slope*b - delta)) for a point-mass ability."""
    cal = {"delta": 1.5, "slope": 0.8, "a_mult": 0.5, "tier_shift": {}}
    mu, sd, a, shift = np.array([7.0]), np.array([1e-9]), np.array([1.2]), np.array([-0.3])
    got = p_by_level(*transform(mu, sd, a, shift, cal))[0]
    b = np.arange(1, 11)
    want = 1 / (1 + np.exp(-1.2 * 0.5 * (7.0 - 0.3 - 0.8 * b - 1.5)))
    assert np.allclose(got, want, atol=1e-9)


def test_invalid_calibration_rejected():
    with pytest.raises(ValueError):
        load_calibration({"delta": 0.0, "slope": -1.0, "a_mult": 1.0})


def test_calibrated_route_is_fast():
    import time
    m = Matcher(calibration=True)
    p_of(m, 5)
    t0 = time.perf_counter()
    for _ in range(50):
        p_of(m, 5)
    assert (time.perf_counter() - t0) / 50 < 0.002
