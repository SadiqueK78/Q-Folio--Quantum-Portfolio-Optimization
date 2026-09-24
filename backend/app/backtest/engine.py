"""
Backtesting engine (Section 16-17) — walk-forward / rolling-window
optimization with NO look-ahead bias: at every rebalance date, the
optimizer only ever sees returns strictly BEFORE that date. Portfolio value
then evolves forward using realized (already-happened, out-of-sample)
returns until the next rebalance date.

Supports:
  - rolling window (fixed lookback) or expanding window (from series start)
  - daily / weekly / monthly / quarterly rebalancing
  - transaction costs charged on turnover at each rebalance
  - benchmark comparison: equal-weight (rebalanced same frequency) and
    buy-and-hold (weights fixed at the first rebalance, never re-traded)
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
import pandas as pd

from app.analytics import risk as riskmod
from app.optimize import classical
from app.optimize.constraints import PortfolioConstraints


FREQ_TO_OFFSET = {"daily": "B", "weekly": "W", "monthly": "ME", "quarterly": "QE"}
FREQ_TO_PPY = {"daily": 252.0, "weekly": 52.0, "monthly": 12.0, "quarterly": 4.0}


@dataclass
class RebalanceEvent:
    date: str
    weights: dict[str, float]
    turnover: float
    transaction_cost: float
    portfolio_value_before: float


@dataclass
class BacktestResult:
    equity_curve: pd.Series               # portfolio value indexed by date
    benchmark_equal_weight: pd.Series
    benchmark_buy_hold: pd.Series
    drawdown: pd.Series
    daily_returns: pd.Series
    rebalance_events: list[RebalanceEvent]
    metrics: dict
    benchmark_metrics: dict
    warnings: list[str] = field(default_factory=list)


def _rebalance_dates(index: pd.DatetimeIndex, start: pd.Timestamp, end: pd.Timestamp, frequency: str) -> list[pd.Timestamp]:
    offset = FREQ_TO_OFFSET[frequency]
    if frequency == "daily":
        candidates = index[(index >= start) & (index <= end)]
    else:
        periodic = pd.date_range(start, end, freq=offset)
        candidates = []
        for p in periodic:
            pos = index.searchsorted(p)
            if pos < len(index):
                candidates.append(index[pos])
        candidates = pd.DatetimeIndex(sorted(set(candidates)))
    return list(candidates)


def _metrics_from_equity(equity: pd.Series, daily_returns: pd.Series, risk_free_rate: float,
                          transaction_cost_total: float, n_rebalances: int, turnover_total: float) -> dict:
    if len(equity) < 2:
        return {}
    total_return = float(equity.iloc[-1] / equity.iloc[0] - 1)
    n_years = (equity.index[-1] - equity.index[0]).days / 365.25
    cagr = float((equity.iloc[-1] / equity.iloc[0]) ** (1 / n_years) - 1) if n_years > 0 else 0.0
    ann_vol = float(daily_returns.std(ddof=1) * np.sqrt(252)) if len(daily_returns) > 1 else 0.0
    sharpe = (cagr - risk_free_rate) / ann_vol if ann_vol else 0.0
    sortino = riskmod.sortino_ratio(daily_returns, risk_free_rate / 252, 252)
    mdd = riskmod.max_drawdown(equity / equity.iloc[0])
    calmar = (cagr / abs(mdd)) if mdd != 0 else 0.0
    return {
        "total_return_pct": round(total_return * 100, 2),
        "cagr_pct": round(cagr * 100, 2),
        "volatility_pct": round(ann_vol * 100, 2),
        "sharpe": round(sharpe, 3),
        "sortino": round(sortino, 3),
        "max_drawdown_pct": round(mdd * 100, 2),
        "calmar_ratio": round(calmar, 3),
        "n_rebalances": n_rebalances,
        "total_transaction_cost": round(transaction_cost_total, 2),
        "average_turnover_pct": round((turnover_total / n_rebalances) * 100, 2) if n_rebalances else 0.0,
    }


def _optimize_weights(mu: pd.Series, cov: pd.DataFrame, sectors: dict[str, str],
                       constraints: PortfolioConstraints, risk_free_rate: float, strategy: str) -> pd.Series | None:
    try:
        if strategy == "equal_weight":
            return classical.equal_weight(mu, cov, risk_free_rate)["weights"]
        if strategy == "min_volatility":
            return classical.minimum_volatility(mu, cov, sectors, constraints, risk_free_rate)["weights"]
        if strategy == "max_sharpe":
            return classical.maximum_sharpe(mu, cov, sectors, constraints, risk_free_rate)["weights"]
        if strategy == "risk_parity":
            return classical.risk_parity(mu, cov, sectors, constraints, risk_free_rate)["weights"]
    except RuntimeError:
        return None
    return None


def run_backtest(
    prices: pd.DataFrame,
    sectors: dict[str, str],
    constraints: PortfolioConstraints,
    strategy: str = "max_sharpe",
    frequency: str = "monthly",
    lookback_days: int = 504,          # ~2 years of trading days
    window_type: str = "rolling",       # "rolling" | "expanding"
    initial_capital: float = 100_000.0,
    risk_free_rate: float = 0.06,
    start_date: str | None = None,
    end_date: str | None = None,
) -> BacktestResult:
    warnings: list[str] = []
    daily_ret_all = prices.pct_change().dropna(how="all")
    idx = daily_ret_all.index

    start = pd.Timestamp(start_date) if start_date else idx[min(lookback_days, len(idx) - 1)]
    end = pd.Timestamp(end_date) if end_date else idx[-1]
    start = max(start, idx[min(lookback_days, len(idx) - 1)])  # ensure enough lookback exists

    rebal_dates = _rebalance_dates(idx, start, end, frequency)
    if len(rebal_dates) < 2:
        raise ValueError("Not enough data for the requested backtest window and rebalancing frequency.")

    trading_days = idx[(idx >= rebal_dates[0]) & (idx <= end)]

    # --- Strategy portfolio simulation ---
    equity = pd.Series(index=trading_days, dtype=float)
    shares = pd.Series(0.0, index=prices.columns)
    cash = initial_capital
    portfolio_value = initial_capital
    events: list[RebalanceEvent] = []
    transaction_cost_total = 0.0
    turnover_total = 0.0
    rebal_set = set(rebal_dates)

    for day in trading_days:
        day_prices = prices.loc[day].reindex(prices.columns)
        holdings_value = float((shares * day_prices).fillna(0).sum())
        portfolio_value = holdings_value + cash

        if day in rebal_set:
            lookback_start_idx = 0 if window_type == "expanding" else max(0, idx.get_loc(day) - lookback_days)
            window = daily_ret_all.iloc[lookback_start_idx: idx.get_loc(day)]
            if len(window) < 20:
                equity[day] = portfolio_value
                continue

            mu = window.mean() * 252
            cov = window.cov() * 252
            weights = _optimize_weights(mu, cov, sectors, constraints, risk_free_rate, strategy)
            if weights is None:
                warnings.append(f"Optimization failed at {day.date()}; holding previous allocation.")
                equity[day] = portfolio_value
                continue

            current_weights = (shares * day_prices).fillna(0) / portfolio_value if portfolio_value > 0 else shares * 0
            turnover = float((weights.reindex(prices.columns, fill_value=0) - current_weights).abs().sum())
            cost = portfolio_value * turnover * constraints.transaction_cost_pct
            investable = portfolio_value - cost

            target_value = weights.reindex(prices.columns, fill_value=0) * investable
            new_shares = (target_value / day_prices).fillna(0)
            shares = new_shares
            cash = investable - float((new_shares * day_prices).fillna(0).sum())
            transaction_cost_total += cost
            turnover_total += turnover
            portfolio_value = investable

            events.append(RebalanceEvent(
                date=str(day.date()), weights=weights.round(4).to_dict(), turnover=round(turnover, 4),
                transaction_cost=round(cost, 2), portfolio_value_before=round(holdings_value + (cash + cost), 2),
            ))

        equity[day] = portfolio_value

    equity = equity.ffill().dropna()
    port_daily_returns = equity.pct_change().dropna()
    drawdown = equity / equity.cummax() - 1

    # --- Benchmark: equal weight, rebalanced same frequency, no optimization needed ---
    n = len(prices.columns)
    eq_shares = pd.Series(0.0, index=prices.columns)
    eq_cash = initial_capital
    eq_equity = pd.Series(index=trading_days, dtype=float)
    for day in trading_days:
        day_prices = prices.loc[day].reindex(prices.columns)
        val = float((eq_shares * day_prices).fillna(0).sum()) + eq_cash
        if day in rebal_set:
            target = val / n
            eq_shares = (pd.Series(target, index=prices.columns) / day_prices).fillna(0)
            eq_cash = val - float((eq_shares * day_prices).fillna(0).sum())
            val = eq_cash + float((eq_shares * day_prices).fillna(0).sum())
        eq_equity[day] = val
    eq_equity = eq_equity.ffill().dropna()

    # --- Benchmark: buy & hold, weights fixed at first rebalance, never re-traded ---
    first_prices = prices.loc[trading_days[0]].reindex(prices.columns)
    bh_shares = (pd.Series(initial_capital / n, index=prices.columns) / first_prices).fillna(0)
    bh_equity = (prices.loc[trading_days] * bh_shares).sum(axis=1)

    metrics = _metrics_from_equity(equity, port_daily_returns, risk_free_rate,
                                    transaction_cost_total, len(events), turnover_total)
    bench_metrics = {
        "equal_weight": _metrics_from_equity(eq_equity, eq_equity.pct_change().dropna(), risk_free_rate, 0, 0, 0),
        "buy_and_hold": _metrics_from_equity(bh_equity, bh_equity.pct_change().dropna(), risk_free_rate, 0, 0, 0),
    }

    return BacktestResult(
        equity_curve=equity, benchmark_equal_weight=eq_equity, benchmark_buy_hold=bh_equity,
        drawdown=drawdown, daily_returns=port_daily_returns, rebalance_events=events,
        metrics=metrics, benchmark_metrics=bench_metrics, warnings=warnings,
    )
