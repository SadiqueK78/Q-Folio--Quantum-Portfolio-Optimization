"""
Portfolio construction from weights (Sections 10, 33-34): converts a weight
vector into actual rupee amounts, share counts (fractional or whole),
transaction cost, and leftover cash. Also runs constraint post-validation
(Section 51) so every result the UI shows has been checked, not just solved.
"""
from __future__ import annotations

import math
from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.optimize.constraints import PortfolioConstraints


@dataclass
class HoldingLine:
    symbol: str
    weight: float
    amount: float
    price: float | None
    shares: float
    leftover_cash: float


@dataclass
class ConstructedPortfolio:
    holdings: list[HoldingLine]
    total_invested: float
    remaining_cash: float
    utilization_pct: float
    transaction_cost: float
    validation: dict[str, bool]


def construct_portfolio(
    weights: pd.Series,
    budget: float,
    constraints: PortfolioConstraints,
    latest_prices: dict[str, float] | None = None,
    whole_shares: bool = False,
    sectors: dict[str, str] | None = None,
) -> ConstructedPortfolio:
    weights = weights.clip(lower=0)
    if weights.sum() > 0:
        weights = weights / weights.sum()

    gross_amounts = weights * budget
    transaction_cost = float(gross_amounts.abs().sum() * constraints.transaction_cost_pct)
    investable = budget - transaction_cost

    holdings: list[HoldingLine] = []
    total_invested = 0.0
    for symbol, w in weights.items():
        amount = float(w * investable)
        price = (latest_prices or {}).get(symbol)
        leftover = 0.0
        shares = 0.0
        if price and price > 0:
            if whole_shares:
                shares = math.floor(amount / price)
                actual_amount = shares * price
                leftover = amount - actual_amount
                amount = actual_amount
            else:
                shares = amount / price
        if w > 1e-9:
            holdings.append(HoldingLine(symbol, float(w), amount, price, shares, leftover))
            total_invested += amount

    remaining_cash = budget - total_invested - transaction_cost
    utilization = (total_invested / budget * 100) if budget else 0.0

    validation = _validate_result(weights, budget, total_invested, constraints, sectors or {})

    return ConstructedPortfolio(
        holdings=holdings,
        total_invested=round(total_invested, 2),
        remaining_cash=round(remaining_cash, 2),
        utilization_pct=round(utilization, 2),
        transaction_cost=round(transaction_cost, 2),
        validation=validation,
    )


def _validate_result(weights: pd.Series, budget: float, invested: float,
                      constraints: PortfolioConstraints, sectors: dict[str, str]) -> dict[str, bool]:
    checks = {}
    checks["budget_constraint"] = invested <= budget + 1e-6
    checks["no_negative_allocation"] = bool((weights >= -1e-9).all())
    checks["no_nan_values"] = bool(not weights.isna().any())
    checks["allocation_constraints"] = bool(
        ((weights <= constraints.max_weight + 1e-6) | (weights < 1e-9)).all()
    )
    if constraints.min_holdings or constraints.max_holdings:
        n_held = int((weights > 1e-9).sum())
        lo = constraints.min_holdings or 0
        hi = constraints.max_holdings or n_held
        checks["holdings_constraint"] = lo <= n_held <= hi
    else:
        checks["holdings_constraint"] = True
    if constraints.sector_bounds and sectors:
        ok = True
        for sector, (lo, hi) in constraints.sector_bounds.items():
            total = sum(w for sym, w in weights.items() if sectors.get(sym) == sector)
            if not (lo - 1e-6 <= total <= hi + 1e-6):
                ok = False
        checks["sector_constraints"] = ok
    else:
        checks["sector_constraints"] = True
    return checks
