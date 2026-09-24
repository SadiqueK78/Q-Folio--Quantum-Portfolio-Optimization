"""
Classical portfolio optimization (Sections 9, 18-19).

All solvers work on annualized mu / covariance and a PortfolioConstraints
object. Sector constraints are enforced as linear inequalities; holdings-
count constraints (cardinality) are NOT enforced in the continuous solvers
below (SLSQP can't handle integer cardinality) — that's exactly the gap the
QUBO/MIQP layer exists to fill when a hard min/max-holdings count matters.
"""
from __future__ import annotations

import numpy as np
import pandas as pd
from scipy.optimize import minimize

from app.optimize.constraints import PortfolioConstraints


def _sector_constraint_funcs(names: list[str], sectors: dict[str, str], sector_bounds: dict[str, tuple[float, float]]):
    rules = []
    for sector, (lo, hi) in sector_bounds.items():
        idx = [i for i, n in enumerate(names) if sectors.get(n) == sector]
        if not idx:
            continue
        rules.append({"type": "ineq", "fun": lambda w, idx=idx, lo=lo: w[idx].sum() - lo})
        rules.append({"type": "ineq", "fun": lambda w, idx=idx, hi=hi: hi - w[idx].sum()})
    return rules


def _base_rules(n: int):
    return [{"type": "eq", "fun": lambda w: w.sum() - 1}]


def _bounds(n: int, constraints: PortfolioConstraints):
    return [(constraints.min_weight, constraints.max_weight)] * n


def _stats(w, mu, cov, rf):
    ret = float(w @ mu)
    var = float(max(w @ cov @ w, 0))
    vol = var ** 0.5
    return {"return": ret, "risk": vol, "variance": var, "sharpe": (ret - rf) / vol if vol else 0.0}


def minimum_volatility(mu: pd.Series, cov: pd.DataFrame, sectors: dict[str, str],
                        constraints: PortfolioConstraints, risk_free_rate: float) -> dict:
    names = list(mu.index)
    mu_v, cov_v = mu.to_numpy(), cov.to_numpy()
    n = len(names)
    rules = _base_rules(n) + _sector_constraint_funcs(names, sectors, constraints.sector_bounds)

    result = minimize(lambda w: float(w @ cov_v @ w), np.repeat(1 / n, n), method="SLSQP",
                       bounds=_bounds(n, constraints), constraints=rules,
                       options={"maxiter": 1000, "ftol": 1e-12})
    if not result.success:
        raise RuntimeError(f"Minimum-volatility optimization failed: {result.message}")
    w = np.clip(result.x, 0, None)
    w = w / w.sum()
    return {"weights": pd.Series(w, index=names), "statistics": _stats(w, mu_v, cov_v, risk_free_rate),
            "method": "Minimum Volatility"}


def maximum_sharpe(mu: pd.Series, cov: pd.DataFrame, sectors: dict[str, str],
                    constraints: PortfolioConstraints, risk_free_rate: float) -> dict:
    names = list(mu.index)
    mu_v, cov_v = mu.to_numpy(), cov.to_numpy()
    n = len(names)
    rules = _base_rules(n) + _sector_constraint_funcs(names, sectors, constraints.sector_bounds)

    def neg_sharpe(w):
        var = float(max(w @ cov_v @ w, 0))
        vol = var ** 0.5
        if vol == 0:
            return 1e6
        return -((w @ mu_v - risk_free_rate) / vol)

    result = minimize(neg_sharpe, np.repeat(1 / n, n), method="SLSQP",
                       bounds=_bounds(n, constraints), constraints=rules,
                       options={"maxiter": 1000, "ftol": 1e-12})
    if not result.success:
        raise RuntimeError(f"Maximum-Sharpe optimization failed: {result.message}")
    w = np.clip(result.x, 0, None)
    w = w / w.sum()
    return {"weights": pd.Series(w, index=names), "statistics": _stats(w, mu_v, cov_v, risk_free_rate),
            "method": "Maximum Sharpe"}


def risk_parity(mu: pd.Series, cov: pd.DataFrame, sectors: dict[str, str],
                 constraints: PortfolioConstraints, risk_free_rate: float) -> dict:
    """Equalize each asset's contribution to portfolio variance, subject to
    the same weight bounds (sector bounds are treated as soft here since an
    exact-RP + sector-constrained solution isn't always feasible)."""
    names = list(mu.index)
    mu_v, cov_v = mu.to_numpy(), cov.to_numpy()
    n = len(names)

    def objective(w):
        port_var = float(w @ cov_v @ w)
        if port_var <= 0:
            return 1e6
        marginal = cov_v @ w
        contrib = w * marginal / port_var
        target = 1.0 / n
        return float(np.sum((contrib - target) ** 2))

    rules = _base_rules(n)
    result = minimize(objective, np.repeat(1 / n, n), method="SLSQP",
                       bounds=_bounds(n, constraints), constraints=rules,
                       options={"maxiter": 2000, "ftol": 1e-14})
    if not result.success:
        raise RuntimeError(f"Risk-parity optimization failed: {result.message}")
    w = np.clip(result.x, 0, None)
    w = w / w.sum()
    return {"weights": pd.Series(w, index=names), "statistics": _stats(w, mu_v, cov_v, risk_free_rate),
            "method": "Risk Parity"}


def equal_weight(mu: pd.Series, cov: pd.DataFrame, risk_free_rate: float) -> dict:
    names = list(mu.index)
    n = len(names)
    w = np.repeat(1 / n, n)
    return {"weights": pd.Series(w, index=names),
            "statistics": _stats(w, mu.to_numpy(), cov.to_numpy(), risk_free_rate),
            "method": "Equal Weight"}


def efficient_frontier(mu: pd.Series, cov: pd.DataFrame, constraints: PortfolioConstraints,
                        n_points: int = 25) -> list[dict]:
    """Sweep target returns between min-vol and max-return portfolios,
    minimizing variance at each target (Section 42)."""
    names = list(mu.index)
    mu_v, cov_v = mu.to_numpy(), cov.to_numpy()
    n = len(names)

    lo_ret = float(mu_v.min())
    hi_ret = float(mu_v.max())
    targets = np.linspace(lo_ret, hi_ret, n_points)

    frontier = []
    for target in targets:
        rules = [
            {"type": "eq", "fun": lambda w: w.sum() - 1},
            {"type": "eq", "fun": lambda w, t=target: w @ mu_v - t},
        ]
        result = minimize(lambda w: float(w @ cov_v @ w), np.repeat(1 / n, n), method="SLSQP",
                           bounds=_bounds(n, constraints), constraints=rules,
                           options={"maxiter": 500, "ftol": 1e-10})
        if result.success:
            w = np.clip(result.x, 0, None)
            if w.sum() > 0:
                w = w / w.sum()
            vol = float(max(w @ cov_v @ w, 0)) ** 0.5
            frontier.append({"return": float(w @ mu_v), "risk": vol, "weights": dict(zip(names, w))})
    return frontier
