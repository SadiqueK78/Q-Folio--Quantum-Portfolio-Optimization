"""
Unit tests for constraint feasibility validation (Section 50) and portfolio
construction validation (Section 51).
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from app.optimize.constraints import PortfolioConstraints, validate_feasibility
from app.optimize.portfolio import construct_portfolio


def test_feasible_default_constraints():
    c = PortfolioConstraints(max_weight=0.20, min_holdings=5, max_holdings=10)
    result = validate_feasibility(c, n_assets=10)
    assert result.feasible


def test_infeasible_max_weight_too_small_for_holdings():
    # 5% cap needs >=20 holdings to reach 100%, but max_holdings=10
    c = PortfolioConstraints(max_weight=0.05, min_holdings=5, max_holdings=10)
    result = validate_feasibility(c, n_assets=10)
    assert not result.feasible
    assert any("max allocation" in r for r in result.reasons)


def test_infeasible_min_greater_than_max_holdings():
    c = PortfolioConstraints(min_holdings=8, max_holdings=5)
    result = validate_feasibility(c, n_assets=10)
    assert not result.feasible


def test_infeasible_sector_minimums_exceed_budget():
    c = PortfolioConstraints(sector_bounds={"Tech": (0.6, 0.8), "Fin": (0.5, 0.7)})
    result = validate_feasibility(c, n_assets=10)
    assert not result.feasible


def test_budget_must_be_positive():
    c = PortfolioConstraints(budget=0)
    result = validate_feasibility(c, n_assets=5)
    assert not result.feasible


def test_construct_portfolio_never_exceeds_budget():
    weights = pd.Series({"A": 0.5, "B": 0.3, "C": 0.2})
    c = PortfolioConstraints(budget=100_000, max_weight=0.5, transaction_cost_pct=0.001)
    result = construct_portfolio(weights, 100_000, c, latest_prices={"A": 100, "B": 50, "C": 200})
    assert result.total_invested + result.transaction_cost <= 100_000 + 1e-6
    assert result.validation["budget_constraint"]
    assert result.validation["no_negative_allocation"]
    assert result.validation["no_nan_values"]


def test_construct_portfolio_whole_shares_leaves_leftover_cash():
    weights = pd.Series({"A": 1.0})
    c = PortfolioConstraints(budget=1000, max_weight=1.0, transaction_cost_pct=0.0)
    result = construct_portfolio(weights, 1000, c, latest_prices={"A": 300}, whole_shares=True)
    assert result.holdings[0].shares == 3  # floor(1000/300)
    assert result.remaining_cash == pytest.approx(100.0, abs=1e-6)
