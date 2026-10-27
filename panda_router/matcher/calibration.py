"""Outcome calibration of the matcher's P(success) (fitted by scripts/outcomes/calibrate_matcher.py).

core.py stays untouched (the training soft matcher uses it raw). The calibration rescales the difficulty
axis and the discrimination and shifts ability per provider tier:

    P = E_{b, z} sigmoid(a * a_mult * (z + shift_tier - (slope * b + delta)))

which equals core's sigmoid(a' (z' - b)) with z' = (z + shift_tier - delta) / slope, a' = a * a_mult * slope.
So it is applied as a transform of (mu, sd, a) right before `p_by_level`. OPT-IN: enable with
PANDA_ROUTER_CALIBRATION=on or `Matcher(calibration=True)`. It is off by default because, fitted on five
cheap single-turn OpenRouter models, it pushes the default policy to the strongest model on every task
(78.6 success/100 at $1.06 vs 67.9 at $0.16 uncalibrated max_utility; data/outcomes/REPORT_calibration.md).
"""

from __future__ import annotations

import json
import os
from functools import lru_cache
from pathlib import Path

import numpy as np

ENV = "PANDA_ROUTER_CALIBRATION"
DEFAULT_PATH = Path(__file__).with_name("calibration.json")
IDENTITY = {"delta": 0.0, "slope": 1.0, "a_mult": 1.0, "tier_shift": {}}


def _validated(params: dict) -> dict:
    p = {**IDENTITY, **params}
    if not (p["slope"] > 0 and p["a_mult"] > 0):
        raise ValueError(f"calibration slope and a_mult must be > 0, got {p['slope']}, {p['a_mult']}")
    if not all(np.isfinite([p["delta"], p["slope"], p["a_mult"], *p["tier_shift"].values()])):
        raise ValueError("calibration parameters must be finite")
    return p


@lru_cache(maxsize=8)
def _read(path: str) -> dict:
    return _validated(json.loads(Path(path).read_text())["params"])


def load_calibration(spec: bool | str | Path | dict | None = None) -> dict | None:
    """None -> off unless PANDA_ROUTER_CALIBRATION=on; True -> shipped file; False -> off; path/dict -> that."""
    if spec is False or (spec is None and os.environ.get(ENV, "").strip().lower() not in ("on", "1", "true", "yes")):
        return None
    if isinstance(spec, dict):
        return _validated(spec.get("params", spec))
    return _read(str(DEFAULT_PATH if spec in (None, True) else Path(spec).resolve()))


def card_tier(card: dict) -> str | None:
    return next((t.split(":", 1)[1] for t in card.get("tags", ()) if t.startswith("tier:")), None)


def tier_shifts(cal: dict | None, cards) -> np.ndarray:
    shifts = (cal or IDENTITY)["tier_shift"]
    return np.array([float(shifts.get(card_tier(c), 0.0)) for c in cards])


def transform(mu: np.ndarray, sd: np.ndarray, a: np.ndarray, shift: np.ndarray,
              cal: dict | None) -> tuple[np.ndarray, np.ndarray, np.ndarray]:
    """(mu, sd, a) -> calibrated inputs for core.p_by_level. Identity when cal is None."""
    if cal is None:
        return mu, sd, a
    s = cal["slope"]
    return (mu + shift - cal["delta"]) / s, sd / s, a * cal["a_mult"] * s
