"""Card matcher: deterministic decision layer of Panda Router (CONTRACTS.md "Matcher")."""

from .cards import DEFAULT_CARDS_DIR, Pool, compile_pool, load_cards, pool_hash, schema_errors, validate_card
from .core import (LAMBDA, ability_moments, axis_weights, difficulty_posterior_after_failure, expected_skills,
                   p_by_level, p_success, success_probabilities)
from .policy import DEFAULTS, MODES, Matcher, default_matcher, escalate, estimate_input_tokens, new_trace_id, route

__all__ = [
    "DEFAULT_CARDS_DIR", "Pool", "compile_pool", "load_cards", "pool_hash", "schema_errors", "validate_card",
    "LAMBDA", "ability_moments", "axis_weights", "difficulty_posterior_after_failure", "expected_skills",
    "p_by_level", "p_success", "success_probabilities",
    "DEFAULTS", "MODES", "Matcher", "default_matcher", "escalate", "estimate_input_tokens", "new_trace_id", "route",
]
