"""
Synthetic price generator — used ONLY when real market data is unavailable
(e.g. this sandbox has no network access to Yahoo Finance, or for local unit
tests that shouldn't depend on the network). Mirrors the reference PDF's
approach: "you haven't attached a real price file, so here's an illustrative
dataset with the same methodology." Every consumer of this data must label
it clearly as synthetic/illustrative — never presented as real market data.
"""
from __future__ import annotations

import numpy as np
import pandas as pd

from app.data.universe import Asset


def generate_synthetic_prices(
    universe: list[Asset],
    years: int = 10,
    seed: int = 42,
) -> pd.DataFrame:
    """Geometric Brownian motion with per-sector drift/vol and a shared
    market factor, so correlations look realistic (same sector => higher
    correlation), purely for pipeline testing / demos."""
    rng = np.random.default_rng(seed)
    n_days = int(years * 252)
    dates = pd.bdate_range(end=pd.Timestamp.today(), periods=n_days)

    sectors = sorted({a.sector for a in universe})
    sector_factor = {s: rng.normal(0.0003, 0.012, n_days) for s in sectors}
    market_factor = rng.normal(0.0002, 0.010, n_days)

    data = {}
    for asset in universe:
        idio = rng.normal(0.0002, 0.014, n_days)
        drift = 0.0003 + rng.normal(0, 0.0001)
        daily_ret = (
            0.4 * market_factor + 0.35 * sector_factor[asset.sector] + 0.25 * idio + drift
        )
        price_path = 100 * np.exp(np.cumsum(daily_ret))
        data[asset.symbol] = price_path

    return pd.DataFrame(data, index=dates)
