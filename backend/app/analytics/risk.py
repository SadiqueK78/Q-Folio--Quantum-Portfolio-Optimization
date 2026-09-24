"""
Risk-metrics engine (Section 8) — the module the original scaffold was
missing almost entirely. Every function here is pure (no I/O), takes
returns/weights in, and returns a number or Series, so it is trivially unit
testable and reusable by both the classical and QUBO optimizers.
"""
from __future__ import annotations

import numpy as np
import pandas as pd


# ---------- Expected return ----------

def expected_return_historical_mean(returns: pd.DataFrame) -> pd.Series:
    return returns.mean()


def expected_return_geometric(returns: pd.DataFrame) -> pd.Series:
    return (1 + returns).prod() ** (1 / len(returns)) - 1


def annualize_return(periodic_mean: pd.Series, periods_per_year: float) -> pd.Series:
    return periodic_mean * periods_per_year


# ---------- Volatility / covariance / correlation ----------

def volatility(returns: pd.DataFrame) -> pd.Series:
    """sigma_i = std dev of periodic returns."""
    return returns.std(ddof=1)


def annualize_volatility(periodic_vol: pd.Series, periods_per_year: float) -> pd.Series:
    return periodic_vol * np.sqrt(periods_per_year)


def covariance_matrix(returns: pd.DataFrame, periods_per_year: float = 1.0) -> pd.DataFrame:
    return returns.cov() * periods_per_year


def correlation_matrix(returns: pd.DataFrame) -> pd.DataFrame:
    return returns.corr()


# ---------- Portfolio-level ----------

def portfolio_return(weights: np.ndarray, mu: np.ndarray) -> float:
    return float(np.asarray(weights) @ np.asarray(mu))


def portfolio_variance(weights: np.ndarray, covariance: np.ndarray) -> float:
    w = np.asarray(weights)
    return float(w @ np.asarray(covariance) @ w)


def portfolio_volatility(weights: np.ndarray, covariance: np.ndarray) -> float:
    return max(portfolio_variance(weights, covariance), 0.0) ** 0.5


def sharpe_ratio(port_return: float, port_vol: float, risk_free_rate: float) -> float:
    if port_vol == 0:
        return 0.0
    return (port_return - risk_free_rate) / port_vol


def sortino_ratio(returns: pd.Series, risk_free_periodic: float, periods_per_year: float) -> float:
    """Downside-deviation-based ratio. `returns` is a periodic return series
    for the portfolio (or a single asset)."""
    downside = returns[returns < risk_free_periodic]
    if len(downside) == 0:
        return 0.0
    downside_dev = np.sqrt((downside.sub(risk_free_periodic) ** 2).mean())
    if downside_dev == 0:
        return 0.0
    excess = returns.mean() - risk_free_periodic
    return float((excess / downside_dev) * np.sqrt(periods_per_year))


def max_drawdown(cumulative_value: pd.Series) -> float:
    """cumulative_value: e.g. (1+returns).cumprod(). Returns a negative fraction."""
    running_max = cumulative_value.cummax()
    drawdown = cumulative_value / running_max - 1
    return float(drawdown.min())


def historical_var(returns: pd.Series, confidence: float = 0.95) -> float:
    """Historical (non-parametric) Value at Risk, returned as a positive loss fraction."""
    if len(returns) == 0:
        return 0.0
    return float(-np.percentile(returns, (1 - confidence) * 100))


def historical_cvar(returns: pd.Series, confidence: float = 0.95) -> float:
    """Conditional VaR / Expected Shortfall: mean loss beyond the VaR threshold."""
    if len(returns) == 0:
        return 0.0
    var_threshold = np.percentile(returns, (1 - confidence) * 100)
    tail = returns[returns <= var_threshold]
    if len(tail) == 0:
        return float(-var_threshold)
    return float(-tail.mean())


def beta(asset_returns: pd.Series, benchmark_returns: pd.Series) -> float:
    aligned = pd.concat([asset_returns, benchmark_returns], axis=1).dropna()
    if len(aligned) < 2:
        return float("nan")
    cov = aligned.cov().iloc[0, 1]
    bench_var = aligned.iloc[:, 1].var()
    return float(cov / bench_var) if bench_var else float("nan")


def risk_contribution(weights: np.ndarray, covariance: np.ndarray) -> np.ndarray:
    """Marginal contribution of each asset to total portfolio variance,
    normalized to sum to 1 (used for the Risk Contribution chart / risk-parity)."""
    w = np.asarray(weights)
    cov = np.asarray(covariance)
    port_var = portfolio_variance(w, cov)
    if port_var == 0:
        return np.zeros_like(w)
    marginal = cov @ w
    contribution = w * marginal
    return contribution / port_var


def diversification_score(weights: np.ndarray, correlation: np.ndarray) -> float:
    """1 - average pairwise correlation weighted by allocation; higher = more
    diversified. Used as the optional +lambda4 term in Section 9's objective."""
    w = np.asarray(weights)
    corr = np.asarray(correlation)
    n = len(w)
    if n < 2:
        return 0.0
    weighted_corr_sum, weight_sum = 0.0, 0.0
    for i in range(n):
        for j in range(n):
            if i == j:
                continue
            weighted_corr_sum += w[i] * w[j] * corr[i, j]
            weight_sum += w[i] * w[j]
    avg_corr = weighted_corr_sum / weight_sum if weight_sum else 0.0
    return 1 - avg_corr


def full_risk_report(
    returns: pd.DataFrame,
    weights: np.ndarray | None,
    risk_free_periodic: float,
    periods_per_year: float,
    benchmark_returns: pd.Series | None = None,
) -> dict:
    """Convenience aggregator used by the /api/risk endpoint and Risk Analysis page."""
    mu = expected_return_historical_mean(returns)
    vol = volatility(returns)
    cov = covariance_matrix(returns)
    corr = correlation_matrix(returns)

    report: dict = {
        "expected_return_annualized": (mu * periods_per_year).to_dict(),
        "volatility_annualized": (vol * np.sqrt(periods_per_year)).to_dict(),
        "covariance_annualized": (cov * periods_per_year).round(6).to_dict(),
        "correlation": corr.round(4).to_dict(),
    }

    if weights is not None:
        w = np.asarray(weights)
        cov_ann = (cov * periods_per_year).to_numpy()
        mu_ann = (mu * periods_per_year).to_numpy()
        p_ret = portfolio_return(w, mu_ann)
        p_vol = portfolio_volatility(w, cov_ann)
        port_periodic = returns @ w
        cum = (1 + port_periodic).cumprod()

        report["portfolio"] = {
            "expected_return": p_ret,
            "volatility": p_vol,
            "sharpe": sharpe_ratio(p_ret, p_vol, risk_free_periodic * periods_per_year),
            "sortino": sortino_ratio(port_periodic, risk_free_periodic, periods_per_year),
            "max_drawdown": max_drawdown(cum),
            "var_95": historical_var(port_periodic, 0.95),
            "cvar_95": historical_cvar(port_periodic, 0.95),
            "risk_contribution": dict(zip(returns.columns, risk_contribution(w, cov_ann))),
            "diversification_score": diversification_score(w, corr.to_numpy()),
        }
        if benchmark_returns is not None:
            aligned_bench = benchmark_returns.reindex(port_periodic.index).dropna()
            common = port_periodic.reindex(aligned_bench.index)
            report["portfolio"]["beta"] = beta(common, aligned_bench)

    return report
