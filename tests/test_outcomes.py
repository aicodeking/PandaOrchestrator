import numpy as np
import pytest
from scipy.stats import spearmanr

from panda_router.outcomes.irt import fit_irt, heldout_metrics
from panda_router.outcomes.scale import fit_link, norm_model, to_1_10, to_router


def _synthetic(two_pl: bool, n_sys=60, n_items=300, seed=0):
    rng = np.random.default_rng(seed)
    th, b = rng.normal(0, 1, n_sys), rng.normal(0, 1.5, n_items)
    a = np.exp(rng.normal(0, 0.4, n_items)) if two_pl else np.ones(n_items)
    s, i = np.meshgrid(np.arange(n_sys), np.arange(n_items), indexing="ij")
    s, i = s.ravel(), i.ravel()
    n = np.full(len(s), 3)
    k = rng.binomial(n, 1 / (1 + np.exp(-a[i] * (th[s] - b[i]))))
    return th, b, a, s, i, k, n


@pytest.mark.parametrize("two_pl", [False, True])
def test_fit_recovers_synthetic_params(two_pl):
    th, b, a, s, i, k, n = _synthetic(two_pl)
    fit = fit_irt(s, i, k, n, len(th), len(b), two_pl=two_pl)
    assert spearmanr(fit.b, b)[0] > 0.9
    assert spearmanr(fit.theta, th)[0] > 0.95
    if two_pl:
        assert spearmanr(fit.a, a)[0] > 0.4
        assert np.abs(fit.b - b).mean() < 0.5  # theta ~ N(0,1) prior matches the generating scale
    assert (fit.se_b > 0).all()


def test_heldout_beats_base_rate():
    th, b, a, s, i, k, n = _synthetic(True, n_sys=40, n_items=150)
    m = heldout_metrics(s, i, k, n, len(th), len(b), two_pl=True)
    assert m["auc"] > 0.75 and m["logloss"] < m["base_rate_logloss"]


def test_mapping_monotone_and_anchored():
    x = np.linspace(-4, 4, 50)
    link = fit_link(np.array([-1.0, 0.0, 1.0]), np.array([5.0, 6.0, 7.0]), gamma=1.0)
    assert link["alpha"] == pytest.approx(6.0)
    y = to_router(x, link["alpha"], link["gamma"])
    assert np.all(np.diff(y) > 0)
    z = to_1_10(y)
    assert np.all(np.diff(z) >= 0) and z.min() >= 1 and z.max() <= 10
    with pytest.raises(ValueError):
        to_router(x, 0.0, -1.0)


def test_norm_model():
    assert norm_model("claude-4-5-opus") == "claude-opus-4.5"
    assert norm_model("claude-opus-4-5-20251101") == "claude-opus-4.5"
    assert norm_model("claude-3.5-sonnet-20241022") == "claude-sonnet-3.5"
    assert norm_model("devstral-small-2512") == "devstral-small-2512"
    assert norm_model("x-ai/grok-4.5") == "grok-4.5"
    assert norm_model("Qwen/Qwen3.6-35B-A3B") == "qwen3.6-35b-a3b"
    assert norm_model("gpt-5|claude-sonnet-4") == ""


def test_fixed_parameter_fits_recover_truth():
    from panda_router.outcomes.irt import fit_b_given_theta, fit_theta_given_b

    th, b, a, s, i, k, n = _synthetic(False, n_sys=60, n_items=200, seed=1)
    bh, se_b = fit_b_given_theta(th[s], a[i], k, n, i, len(b))
    assert spearmanr(bh, b)[0] > 0.9 and (se_b > 0).all()
    thh, se_t = fit_theta_given_b(b[i], a[i], k, n, s, len(th), prior_sd=3.0)
    assert spearmanr(thh, th)[0] > 0.95 and np.abs(thh - th).mean() < 0.3
    # a strong prior pins the estimate at its mean
    th0, _ = fit_theta_given_b(b[i], a[i], k, n, s, len(th), prior_mu=th + 1.0, prior_sd=1e-3)
    assert np.allclose(th0, th + 1.0, atol=0.01)


def test_strict_verdict_and_kappa():
    from panda_router.outcomes.grade import cohen_kappa, strict_verdict

    cr = [{"id": 1, "text": "x", "critical": True}, {"id": 2, "text": "y"}, {"id": 3, "text": "z"}]
    ok = {"criteria": [{"id": 1, "evidence": "q", "met": True}, {"id": 2, "evidence": "q", "met": True}],
          "material_errors": []}
    assert strict_verdict(ok, cr) is True
    assert strict_verdict({**ok, "material_errors": ["off by one"]}, cr) is False
    assert strict_verdict({"criteria": [{"id": 2, "evidence": "q", "met": True}], "material_errors": []}, cr) is False
    assert strict_verdict({}, cr) is None
    assert cohen_kappa([True, False] * 5, [True, False] * 5) == 1.0
