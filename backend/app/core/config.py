"""
Central configuration for the platform.

Every "magic number" the spec calls out as user-configurable (budget, weight
bounds, sector caps, risk-free rate, transaction cost, discretization steps,
penalty coefficients...) lives here with a sane default, so the rest of the
codebase never hard-codes a number that should be a setting.
"""
from __future__ import annotations

import os
from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    # --- Data ---
    price_provider: str = "yahoo"          # only free/open sources are supported
    historical_years: int = 10
    # Vercel functions can only write under /tmp.
    data_dir: str = "/tmp/data_cache" if os.environ.get("VERCEL") else "data_cache"
    cache_hours_historical: int = 24
    cache_minutes_latest: int = 5
    cache_minutes_news: int = 10

    # --- Currency / budget ---
    currency: str = "INR"
    default_budget: float = 100_000.0

    # --- Risk-free / objective ---
    risk_free_rate: float = 0.06           # matches the PDF's 6% assumption
    trading_days_per_year: int = 252
    months_per_year: int = 12

    # --- Allocation constraints (Section 11) ---
    default_min_weight: float = 0.0
    default_max_weight: float = 0.20       # simple cap, per user's confirmed choice
    default_min_holdings: int = 5
    default_max_holdings: int = 10

    # --- Transaction costs (Section 14) ---
    default_transaction_cost_pct: float = 0.0010   # 0.10%

    # --- QUBO discretization (Section 21) ---
    qubo_weight_step: float = 0.05         # 0%, 5%, 10%, ... granularity
    qubo_max_weight_level: float = 0.20    # ties to default_max_weight
    qubo_num_reads: int = 200

    # --- QUBO penalty coefficients (Section 22), configurable ---
    qubo_penalty_budget: float = 8.0
    qubo_penalty_holdings: float = 4.0
    qubo_penalty_sector: float = 4.0
    qubo_risk_aversion: float = 3.0        # weight on the quadratic risk term

    # --- API ---
    allowed_origins: str = "http://localhost:5173,http://localhost:3000"
    environment: str = "development"

    # --- News / events ---
    rss_feeds: str = (
        "https://www.cnbc.com/id/100003114/device/rss/rss.html,"
        "https://www.cnbc.com/id/10001147/device/rss/rss.html,"
        "https://www.cnbc.com/id/20910258/device/rss/rss.html,"
        "https://feeds.reuters.com/reuters/businessNews,"
        "https://www.moneycontrol.com/rss/latestnews.xml,"
        "https://economictimes.indiatimes.com/markets/rssfeeds/1977021501.cms"
    )
    news_confidence_threshold: float = 0.4
    news_decay_half_life_hours: float = 36.0
    news_max_adjustment: float = 0.15      # cap on how much events can move a score


@lru_cache
def get_settings() -> Settings:
    return Settings()
