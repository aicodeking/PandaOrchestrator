"""Put IRT parameters on the router's 0..10 skill/difficulty scale and link systems to cards.

Matcher: P = sigmoid(1.2 * (theta_r - b_r)). IRT: P = sigmoid(a_i * (theta - b_i)). With the linear map
x_r = alpha + gamma * x, the two agree for a typical item when 1.2 * gamma = a_typ, so
gamma = median(a) / 1.2 (a = 1 for 1PL). The location alpha is the median over anchor systems of
(card coding theta - gamma * theta_irt): systems whose exact base model has a card. A Theil-Sen fit
(free slope) is reported as a diagnostic only.
"""

from __future__ import annotations

import re

import numpy as np

MATCHER_A = 1.2

# normalised base model -> card id, exact same model (any harness / precision noted in REPORT)
EXACT = {
    "devstral-small-2512": "ollama-devstral-small-2-24b",
    "qwen3-coder-30b-a3b": "ollama-qwen3-coder-30b",
    "gpt-5.6-luna": "codex-gpt-5.6-luna",
    "grok-4.5": "grok-4.5",
    "minimax-m3": "openrouter-minimax-m3",
    "deepseek-v4-pro": "openrouter-deepseek-v4-pro",
    "qwen3.6-27b": "ollama-qwen3.6-27b",
    "qwen3.6-35b-a3b": "ollama-qwen3.6-35b",
}
# normalised base model -> card id of a clear successor in the same line (lower-bound evidence only)
PREDECESSOR = {
    "claude-opus-5": "claude-opus-5.5",
    "claude-sonnet-5": "claude-sonnet-5.5",
    "claude-fable-5": "claude-fable-5.1",
    "gpt-5.6-sol": "openrouter-gpt-6-sol",
    "glm-5.2": "openrouter-glm-5.3",
    "mimo-v2.5-pro": "openrouter-mimo-v2.6-pro",
    "qwen3.5-35b-a3b": "ollama-qwen3.6-35b",
    "glm-4.6": "glm-4.7",
    "gemini-3.5-flash": "openrouter-gemini-3.8-flash",
}


def norm_model(raw: str) -> str:
    """'claude-4-5-opus' / 'claude-opus-4-5-20251101' -> 'claude-opus-4.5'; '' or 'a|b' (mixed) -> ''."""
    if not raw or "|" in raw:
        return ""
    m = raw.strip().lower().rstrip("/").split("/")[-1]
    m = re.sub(r"[-_](\d{8}|\d{4}-\d{2}-\d{2})$", "", m)
    m = re.sub(r"-(instruct|preview|latest|reasoner|thinking|high)$", "", m)
    m = re.sub(r"^claude-(\d)[.-](\d)-(opus|sonnet|haiku)", r"claude-\3-\1-\2", m)
    m = re.sub(r"^claude-(\d)-(opus|sonnet|haiku|fable)", r"claude-\2-\1", m)
    m = re.sub(r"^(fable|opus|sonnet)-", r"claude-\1-", m)
    m = re.sub(r"(\d)-(\d)(?=$|-)", r"\1.\2", m)  # version dashes -> dots: gpt-5-2 -> gpt-5.2
    m = m.replace("minimax-2.5", "minimax-m2.5").replace("deepseek-3.2", "deepseek-v3.2")
    return m


def link_slope(a: np.ndarray) -> float:
    return float(np.median(a)) / MATCHER_A


def fit_link(theta_irt: np.ndarray, theta_card: np.ndarray, gamma: float, card_se: np.ndarray | None = None) -> dict:
    """alpha (+ se) for x_r = alpha + gamma * x, plus a Theil-Sen free-slope diagnostic.

    alpha_se = max(bootstrap se of the median, median(card_se) / sqrt(n)): with few anchors the bootstrap
    understates how uncertain the hand-set card thetas themselves are."""
    from scipy.stats import theilslopes

    theta_irt, theta_card = np.asarray(theta_irt, float), np.asarray(theta_card, float)
    resid = theta_card - gamma * theta_irt
    alpha = float(np.median(resid))
    rng = np.random.default_rng(0)
    boots = [np.median(rng.choice(resid, len(resid))) for _ in range(2000)]
    se = float(np.std(boots))
    if card_se is not None:
        se = max(se, float(np.median(card_se)) / np.sqrt(len(resid)))
    out = {"alpha": alpha, "gamma": gamma, "alpha_se": se, "n_anchors": len(resid),
           "anchor_resid_mad": float(np.median(np.abs(resid - alpha)))}
    if len(resid) >= 3:
        ts = theilslopes(theta_card, theta_irt)
        out.update(theilsen_slope=float(ts[0]), theilsen_intercept=float(ts[1]),
                   theilsen_slope_ci=[float(ts[2]), float(ts[3])])
    return out


def to_router(x: np.ndarray, alpha: float, gamma: float) -> np.ndarray:
    """Monotone (gamma > 0) linear map of IRT theta/b onto the router scale (unclipped)."""
    if gamma <= 0:
        raise ValueError("link slope must be positive")
    return alpha + gamma * np.asarray(x, float)


def to_1_10(x_r: np.ndarray) -> np.ndarray:
    return np.clip(x_r, 1.0, 10.0)
