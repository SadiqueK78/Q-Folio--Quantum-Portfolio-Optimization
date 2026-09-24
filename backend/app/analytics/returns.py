"""Return calculations (Section 7)."""
from __future__ import annotations

import numpy as np
import pandas as pd


def daily_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """R_t = P_t / P_{t-1} - 1"""
    return prices.pct_change().dropna(how="all")


def log_returns(prices: pd.DataFrame) -> pd.DataFrame:
    """r_t = ln(P_t / P_{t-1})"""
    return np.log(prices / prices.shift(1)).dropna(how="all")


def resample_returns(daily: pd.DataFrame, freq: str = "M") -> pd.DataFrame:
    """
    Aggregate daily simple returns into weekly/monthly compounded returns.
    freq: "W" weekly, "M" monthly, "Q" quarterly.
    """
    compounded = (1 + daily).resample(freq).prod() - 1
    return compounded.dropna(how="all")


def frequency_returns(prices: pd.DataFrame, frequency: str) -> pd.DataFrame:
    """frequency: 'daily' | 'weekly' | 'monthly'"""
    daily = daily_returns(prices)
    if frequency == "daily":
        return daily
    if frequency == "weekly":
        return resample_returns(daily, "W")
    if frequency == "monthly":
        return resample_returns(daily, "ME")
    raise ValueError(f"Unsupported frequency: {frequency}")


def periods_per_year(frequency: str, trading_days_per_year: int = 252) -> float:
    return {"daily": trading_days_per_year, "weekly": 52.0, "monthly": 12.0}[frequency]
