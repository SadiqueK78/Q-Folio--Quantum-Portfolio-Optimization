"""
Unit tests for risk metrics — run with: pytest tests/test_risk.py -v
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from app.analytics import risk as riskmod


def _sample_returns():
    rng = np.random.default_rng(0)
    dates = pd.date_range("2020-01-01", periods=60, freq="ME")
    data = {
        "A": rng.normal(0.01, 0.05, 60),
        "B": rng.normal(0.008, 0.03, 60),
        "C": rng.normal(0.012, 0.06, 60),
    }
    return pd.DataFrame(data, index=dates)


def test_portfolio_variance_matches_manual_calc():
    returns = _sample_returns()
    cov = riskmod.covariance_matrix(returns).to_numpy()
    w = np.array([0.5, 0.3, 0.2])
    var = riskmod.portfolio_variance(w, cov)
    assert var == pytest.approx(float(w @ cov @ w))


def test_portfolio_volatility_nonnegative():
    returns = _sample_returns()
    cov = riskmod.covariance_matrix(returns).to_numpy()
    w = np.array([0.34, 0.33, 0.33])
    assert riskmod.portfolio_volatility(w, cov) >= 0


def test_sharpe_zero_vol_returns_zero():
    assert riskmod.sharpe_ratio(0.1, 0.0, 0.06) == 0.0


def test_max_drawdown_is_nonpositive():
    cum = pd.Series([1.0, 1.1, 0.9, 1.05, 0.8, 1.2])
    dd = riskmod.max_drawdown(cum)
    assert dd <= 0


def test_max_drawdown_matches_known_case():
    # Peak 1.1 at idx1, trough 0.8 at idx4 -> drawdown = 0.8/1.1 - 1
    cum = pd.Series([1.0, 1.1, 0.9, 1.05, 0.8, 1.2])
    expected = 0.8 / 1.1 - 1
    assert riskmod.max_drawdown(cum) == pytest.approx(expected)


def test_historical_var_is_positive_loss_fraction():
    returns = pd.Series(np.random.default_rng(1).normal(-0.01, 0.05, 500))
    var95 = riskmod.historical_var(returns, 0.95)
    assert var95 > 0


def test_cvar_is_at_least_var():
    returns = pd.Series(np.random.default_rng(1).normal(-0.01, 0.05, 500))
    var95 = riskmod.historical_var(returns, 0.95)
    cvar95 = riskmod.historical_cvar(returns, 0.95)
    assert cvar95 >= var95 - 1e-9


def test_risk_contribution_sums_to_one():
    returns = _sample_returns()
    cov = riskmod.covariance_matrix(returns).to_numpy()
    w = np.array([0.5, 0.3, 0.2])
    contrib = riskmod.risk_contribution(w, cov)
    assert contrib.sum() == pytest.approx(1.0, abs=1e-6)


def test_diversification_score_perfect_correlation_is_zero():
    corr = np.array([[1, 1], [1, 1]])
    score = riskmod.diversification_score(np.array([0.5, 0.5]), corr)
    assert score == pytest.approx(0.0, abs=1e-9)


def test_beta_of_asset_against_itself_is_one():
    returns = _sample_returns()["A"]
    b = riskmod.beta(returns, returns)
    assert b == pytest.approx(1.0, abs=1e-6)
