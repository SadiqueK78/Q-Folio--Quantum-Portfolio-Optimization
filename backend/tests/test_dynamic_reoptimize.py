"""Tests for dynamic reoptimization (Section 30) — event-adjusted expected
returns and the diff/reason generation."""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest

from app.optimize.dynamic import adjust_expected_returns, build_reason


def test_adjust_expected_returns_scales_by_adjustment():
    mu = pd.Series({"A": 0.10, "B": 0.20})
    adjustments = {"A": 0.10, "B": -0.05}
    adjusted = adjust_expected_returns(mu, adjustments)
    assert adjusted["A"] == pytest.approx(0.11)
    assert adjusted["B"] == pytest.approx(0.19)


def test_adjust_expected_returns_missing_symbol_defaults_to_zero():
    mu = pd.Series({"A": 0.10, "B": 0.20})
    adjusted = adjust_expected_returns(mu, {"A": 0.10})
    assert adjusted["B"] == pytest.approx(0.20)


def test_build_reason_mentions_direction_and_magnitude():
    reason = build_reason("A", 0.10, 0.10, 0.20)
    assert "increased" in reason
    assert "high-impact" in reason
    assert "raised" in reason


def test_build_reason_negative_adjustment():
    reason = build_reason("A", -0.02, 0.10, 0.08)
    assert "reduced" in reason
    assert "low-impact" in reason
    assert "lowered" in reason
