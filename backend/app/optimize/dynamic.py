"""
Dynamic reoptimization (Section 30): adjust expected returns using bounded
event-impact scores from the news agents, then compare the resulting
recommended allocation against a "current" allocation the user supplies
(or an equal-weight baseline if they don't have one yet).

This is intentionally a small, transparent adjustment — mu_adjusted =
mu * (1 + adjustment), where `adjustment` is already clamped to
[-max_adjustment, +max_adjustment] by the news-agent layer (Section 28's
safeguard against one article dominating the portfolio).
"""
from __future__ import annotations

import pandas as pd


def adjust_expected_returns(mu: pd.Series, adjustments: dict[str, float]) -> pd.Series:
    adj = pd.Series(adjustments).reindex(mu.index).fillna(0.0)
    return mu * (1 + adj)


def build_reason(symbol: str, adjustment: float, weight_before: float, weight_after: float) -> str:
    direction = "increased" if adjustment > 0 else "reduced" if adjustment < 0 else "unchanged"
    magnitude = "high-impact" if abs(adjustment) > 0.08 else "moderate" if abs(adjustment) > 0.03 else "low-impact"
    delta = weight_after - weight_before
    weight_move = "raised" if delta > 1e-6 else "lowered" if delta < -1e-6 else "kept steady"
    return (
        f"Expected return {direction} by recent {magnitude} news (adjustment "
        f"{adjustment:+.3f}); recommended allocation {weight_move} from "
        f"{weight_before*100:.1f}% to {weight_after*100:.1f}%."
    )
