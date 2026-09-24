"""
Backtesting engine tests — the critical property is NO LOOK-AHEAD BIAS:
weights chosen at a rebalance date must be derivable from data strictly
before that date, and the engine must not error/crash on edge cases.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import pandas as pd
import pytest

from app.data.universe import DEFAULT_UNIVERSE, sector_map
from app.data.synthetic import generate_synthetic_prices
from app.optimize.constraints import PortfolioConstraints
from app.backtest.engine import run_backtest


@pytest.fixture(scope="module")
def synthetic_prices():
    return generate_synthetic_prices(DEFAULT_UNIVERSE, years=4, seed=11)


def test_backtest_runs_monthly(synthetic_prices):
    sectors = sector_map(DEFAULT_UNIVERSE)
    constraints = PortfolioConstraints(max_weight=0.20, min_holdings=5, max_holdings=10)
    result = run_backtest(synthetic_prices, sectors, constraints, strategy="max_sharpe",
                           frequency="monthly", lookback_days=252, initial_capital=100_000)
    assert len(result.equity_curve) > 0
    assert result.equity_curve.iloc[0] > 0
    assert "cagr_pct" in result.metrics


def test_equity_curve_never_negative(synthetic_prices):
    sectors = sector_map(DEFAULT_UNIVERSE)
    constraints = PortfolioConstraints(max_weight=0.20, min_holdings=5, max_holdings=10)
    result = run_backtest(synthetic_prices, sectors, constraints, strategy="max_sharpe",
                           frequency="monthly", lookback_days=252, initial_capital=100_000)
    assert (result.equity_curve > 0).all()


def test_no_lookahead_bias_weights_derivable_from_past_only(synthetic_prices):
    """For each rebalance event, recompute what an optimizer using ONLY
    returns strictly before that date would produce, and confirm the
    engine's stored weights match — i.e. it never peeked at future prices."""
    from app.optimize import classical

    sectors = sector_map(DEFAULT_UNIVERSE)
    constraints = PortfolioConstraints(max_weight=0.20, min_holdings=5, max_holdings=10)
    result = run_backtest(synthetic_prices, sectors, constraints, strategy="max_sharpe",
                           frequency="monthly", lookback_days=252, initial_capital=100_000)

    daily_ret = synthetic_prices.pct_change().dropna(how="all")
    idx = daily_ret.index

    checked = 0
    for event in result.rebalance_events[:5]:  # spot-check first few
        day = pd.Timestamp(event.date)
        loc = idx.get_loc(day)
        window = daily_ret.iloc[max(0, loc - 252): loc]  # strictly before `day`
        if len(window) < 20:
            continue
        mu = window.mean() * 252
        cov = window.cov() * 252
        recomputed = classical.maximum_sharpe(mu, cov, sectors, constraints, 0.06)["weights"]
        stored = pd.Series(event.weights)
        aligned = recomputed.reindex(stored.index).fillna(0)
        assert (aligned - stored).abs().max() < 1e-3  # engine stores weights rounded to 4dp
        checked += 1
    assert checked > 0


def test_benchmark_buy_and_hold_has_no_transaction_cost(synthetic_prices):
    sectors = sector_map(DEFAULT_UNIVERSE)
    constraints = PortfolioConstraints(max_weight=0.20, min_holdings=5, max_holdings=10)
    result = run_backtest(synthetic_prices, sectors, constraints, strategy="equal_weight",
                           frequency="monthly", lookback_days=252, initial_capital=100_000)
    assert result.benchmark_metrics["buy_and_hold"]["total_transaction_cost"] == 0


def test_insufficient_data_raises_clear_error():
    tiny_prices = generate_synthetic_prices(DEFAULT_UNIVERSE, years=1, seed=2).iloc[:10]
    sectors = sector_map(DEFAULT_UNIVERSE)
    constraints = PortfolioConstraints(max_weight=0.20, min_holdings=5, max_holdings=10)
    with pytest.raises(ValueError):
        run_backtest(tiny_prices, sectors, constraints, strategy="max_sharpe",
                      frequency="monthly", lookback_days=252, initial_capital=100_000)
