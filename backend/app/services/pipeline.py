"""
Shared pipeline service used by API routes: fetch (or synthetically
fall back), clean, and cache historical data + derived returns/risk so
every endpoint doesn't refetch. In-process cache is fine for this reference
implementation (Section 45 says caching should exist and be configurable;
swapping in Redis is a drop-in replacement for `_CACHE`).
"""
from __future__ import annotations

import time
from dataclasses import dataclass

import pandas as pd

from app.core.config import get_settings
from app.data.universe import DEFAULT_UNIVERSE, Asset, sector_map
from app.data.fetcher import fetch_historical, clean_prices, DataFetchError, fetch_latest_quotes
from app.data.synthetic import generate_synthetic_prices
from app.analytics.returns import frequency_returns, periods_per_year
from app.analytics import risk as riskmod


@dataclass
class MarketDataBundle:
    adj_close: pd.DataFrame
    source_label: str      # "live" | "cached" | "synthetic"
    fetched_at: float
    quality_text: str


_CACHE: dict[str, MarketDataBundle] = {}


def get_universe() -> list[Asset]:
    return DEFAULT_UNIVERSE


def get_market_data(force_refresh: bool = False) -> MarketDataBundle:
    settings = get_settings()
    cache_key = "default_universe"
    cached = _CACHE.get(cache_key)
    max_age = settings.cache_hours_historical * 3600
    if cached and not force_refresh and (time.time() - cached.fetched_at) < max_age:
        return cached

    universe = get_universe()
    try:
        close, adj_close, volume, report = fetch_historical(universe, years=settings.historical_years)
        bundle = MarketDataBundle(clean_prices(adj_close), "live", time.time(), report.as_text())
    except DataFetchError:
        if cached is not None:
            stale = MarketDataBundle(cached.adj_close, "cached_stale", cached.fetched_at, cached.quality_text)
            _CACHE[cache_key] = stale
            return stale
        adj_close = generate_synthetic_prices(universe, years=settings.historical_years)
        quality = (
            f"SYNTHETIC illustrative data ({adj_close.shape[1]} assets, {adj_close.shape[0]} "
            f"trading days). Live market data unavailable in this environment."
        )
        bundle = MarketDataBundle(adj_close, "synthetic", time.time(), quality)

    _CACHE[cache_key] = bundle
    return bundle


def get_returns_and_risk(frequency: str = "monthly"):
    bundle = get_market_data()
    returns = frequency_returns(bundle.adj_close, frequency)
    ppy = periods_per_year(frequency)
    mu = riskmod.expected_return_historical_mean(returns) * ppy
    cov = riskmod.covariance_matrix(returns, ppy)
    corr = riskmod.correlation_matrix(returns)
    return {
        "bundle": bundle, "returns": returns, "periods_per_year": ppy,
        "mu": mu, "cov": cov, "corr": corr,
    }


def get_latest_quotes():
    universe = get_universe()
    try:
        return fetch_latest_quotes(universe)
    except Exception:
        # Network unavailable in this environment; report explicitly rather
        # than fabricating a price (Section 4/44's core requirement).
        from app.data.fetcher import LatestQuote
        from datetime import datetime, timezone
        now = datetime.now(timezone.utc).strftime("%d %b %Y, %H:%M UTC")
        return [LatestQuote(a.symbol, None, "unavailable", now, "UNKNOWN") for a in universe]
