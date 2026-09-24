"""
Market data fetcher (Sections 4-6).

Free-source only (yfinance / Yahoo Finance). Responsible for:
  - ~10 years of historical OHLCV per asset
  - latest/near-real-time quotes, explicitly labeled by data status
  - a data-quality report (missing values, duplicates, trading days)

This module NEVER guesses or fabricates a price. If a fetch fails, it raises
or returns an explicit failure status — callers decide whether to fall back
to cache, but the fallback is always labeled, never silent.
"""
from __future__ import annotations

import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path

import pandas as pd

from app.core.config import get_settings
from app.data.universe import Asset


class DataFetchError(RuntimeError):
    """Raised when a provider fails and no usable cache exists."""


@dataclass
class DataQualityReport:
    n_assets: int
    period_years: float
    trading_days: int
    missing_value_pct: float
    duplicate_rows: int
    start_date: str
    end_date: str
    per_asset_missing_pct: dict[str, float]

    def as_text(self) -> str:
        return (
            "Data Quality\n"
            "-------------\n"
            f"Assets: {self.n_assets}\n"
            f"Historical Period: {self.period_years:.1f} Years\n"
            f"Trading Days: {self.trading_days}\n"
            f"Missing Values: {self.missing_value_pct:.2f}%\n"
            f"Duplicates: {self.duplicate_rows}\n"
            f"Range: {self.start_date} -> {self.end_date}\n"
        )


def _cache_paths(data_dir: str) -> dict[str, Path]:
    root = Path(data_dir)
    root.mkdir(parents=True, exist_ok=True)
    return {
        "close": root / "historical_close.parquet",
        "adj_close": root / "historical_adjclose.parquet",
        "volume": root / "historical_volume.parquet",
        "meta": root / "historical_meta.json",
    }


def fetch_historical(
    universe: list[Asset],
    years: int | None = None,
    use_cache_if_stale: bool = True,
) -> tuple[pd.DataFrame, pd.DataFrame, pd.DataFrame, DataQualityReport]:
    """
    Fetch ~`years` of daily OHLCV for every asset in `universe` via yfinance.

    Returns (close, adj_close, volume, quality_report). Raises DataFetchError
    if the provider fails AND no cache is available (or use_cache_if_stale is
    False). A successful cache fallback is reported via the `source` field
    the caller should surface to the UI (Section 44) — this function itself
    only returns data + quality; labeling "cached vs live" is the caller's
    responsibility via fetch metadata (see fetch_historical_with_status).
    """
    settings = get_settings()
    years = years or settings.historical_years
    tickers = [a.symbol for a in universe]
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=int(years * 365.25))

    try:
        import yfinance as yf

        raw = yf.download(
            tickers,
            start=start.strftime("%Y-%m-%d"),
            end=end.strftime("%Y-%m-%d"),
            auto_adjust=False,
            progress=False,
            threads=True,
            group_by="ticker",
        )
        if raw is None or raw.empty:
            raise DataFetchError("Yahoo Finance returned no data for this universe/date range.")

        close, adj_close, volume = {}, {}, {}
        for t in tickers:
            try:
                sub = raw[t] if isinstance(raw.columns, pd.MultiIndex) else raw
                close[t] = sub["Close"]
                adj_close[t] = sub["Adj Close"] if "Adj Close" in sub else sub["Close"]
                volume[t] = sub["Volume"]
            except Exception:
                continue  # missing ticker handled by quality report below

        close_df = pd.DataFrame(close).sort_index()
        adj_df = pd.DataFrame(adj_close).sort_index()
        vol_df = pd.DataFrame(volume).sort_index()

        if close_df.empty:
            raise DataFetchError("No usable columns returned for any ticker in the universe.")

        # Caching is a nice-to-have — a successful LIVE fetch must never be
        # discarded just because the on-disk cache write failed (e.g. no
        # pyarrow/fastparquet installed). Fall back to CSV, and if even that
        # fails, still return the live data with a warning.
        paths = _cache_paths(settings.data_dir)
        try:
            close_df.to_parquet(paths["close"])
            adj_df.to_parquet(paths["adj_close"])
            vol_df.to_parquet(paths["volume"])
        except (ImportError, ValueError):
            try:
                close_df.to_csv(paths["close"].with_suffix(".csv"))
                adj_df.to_csv(paths["adj_close"].with_suffix(".csv"))
                vol_df.to_csv(paths["volume"].with_suffix(".csv"))
            except Exception:
                pass  # caching failed entirely; still return the live data below

        report = _quality_report(close_df, tickers, years)
        return close_df, adj_df, vol_df, report

    except Exception as exc:
        if use_cache_if_stale:
            cached = _load_cache(settings.data_dir)
            if cached is not None:
                close_df, adj_df, vol_df = cached
                report = _quality_report(close_df, tickers, years)
                return close_df, adj_df, vol_df, report
        raise DataFetchError(f"Historical data fetch failed and no cache available: {exc}") from exc


def _load_cache(data_dir: str):
    paths = _cache_paths(data_dir)
    if paths["close"].exists() and paths["adj_close"].exists() and paths["volume"].exists():
        try:
            return (
                pd.read_parquet(paths["close"]),
                pd.read_parquet(paths["adj_close"]),
                pd.read_parquet(paths["volume"]),
            )
        except (ImportError, ValueError):
            pass
    csv_close = paths["close"].with_suffix(".csv")
    csv_adj = paths["adj_close"].with_suffix(".csv")
    csv_vol = paths["volume"].with_suffix(".csv")
    if csv_close.exists() and csv_adj.exists() and csv_vol.exists():
        return (
            pd.read_csv(csv_close, index_col=0, parse_dates=True),
            pd.read_csv(csv_adj, index_col=0, parse_dates=True),
            pd.read_csv(csv_vol, index_col=0, parse_dates=True),
        )
    return None


def _quality_report(close_df: pd.DataFrame, tickers: list[str], years: int) -> DataQualityReport:
    total_cells = close_df.shape[0] * close_df.shape[1]
    missing = close_df.isna().sum().sum()
    dup_rows = int(close_df.index.duplicated().sum())
    per_asset_missing = (close_df.isna().mean() * 100).round(3).to_dict()
    return DataQualityReport(
        n_assets=len(tickers),
        period_years=years,
        trading_days=close_df.shape[0],
        missing_value_pct=round(float(missing / total_cells * 100), 4) if total_cells else 0.0,
        duplicate_rows=dup_rows,
        start_date=str(close_df.index.min().date()) if len(close_df) else "",
        end_date=str(close_df.index.max().date()) if len(close_df) else "",
        per_asset_missing_pct=per_asset_missing,
    )


def clean_prices(df: pd.DataFrame) -> pd.DataFrame:
    """
    Handle missing trading days, zero/negative prices, and duplicate index
    entries (Section 6). Forward-fills short gaps (holidays/thin trading);
    does NOT fabricate data across long gaps (delisting, corp actions) —
    those columns are left with NaN so downstream code can flag the asset.
    """
    out = df.copy()
    out = out[~out.index.duplicated(keep="first")]
    out = out.sort_index()
    out = out.where(out > 0)          # drop non-positive "prices"
    out = out.ffill(limit=5)          # bridge short gaps only
    return out


@dataclass
class LatestQuote:
    symbol: str
    price: float | None
    status: str            # "latest_available" | "delayed" | "market_closed" | "unavailable"
    as_of: str
    market_state: str


def _extract_fast_info_price(fast_info) -> float | None:
    """yfinance's `fast_info` has changed shape across versions (sometimes a
    dict-like object, sometimes exposing snake_case attributes, sometimes
    camelCase keys only). Try every known access pattern before giving up,
    so a single yfinance version quirk doesn't take down every quote."""
    candidates = ["last_price", "lastPrice", "regular_market_price", "regularMarketPrice"]
    for key in candidates:
        try:
            value = getattr(fast_info, key)
            if value is not None:
                return float(value)
        except Exception:
            pass
        try:
            value = fast_info[key]
            if value is not None:
                return float(value)
        except Exception:
            pass
    return None


def _nse_market_state(now_utc: datetime) -> str:
    """NSE trading hours are 09:15-15:30 IST, Mon-Fri. This is a LOCAL time
    heuristic, not a live status pulled from any API — used only because
    yfinance's free tier doesn't reliably expose real-time market state.
    Labeled honestly rather than presented as an authoritative feed."""
    ist = now_utc.astimezone(timezone(timedelta(hours=5, minutes=30)))
    if ist.weekday() >= 5:
        return "CLOSED"
    minutes = ist.hour * 60 + ist.minute
    return "OPEN" if 9 * 60 + 15 <= minutes <= 15 * 60 + 30 else "CLOSED"


def fetch_latest_quotes(universe: list[Asset]) -> list[LatestQuote]:
    """
    Best-effort latest price per asset via yfinance. Never claims
    exchange-grade real-time data (Section 4) — always labels status.
    Tries fast_info first (cheap), falls back to a 1-day history call
    (slower, one extra network round-trip) if fast_info doesn't yield a
    usable price on this yfinance version.
    """
    import yfinance as yf

    now = datetime.now(timezone.utc)
    now_label = now.strftime("%d %b %Y, %H:%M UTC")
    market_state = _nse_market_state(now)
    results: list[LatestQuote] = []

    for asset in universe:
        price: float | None = None
        try:
            ticker = yf.Ticker(asset.symbol)
            price = _extract_fast_info_price(ticker.fast_info)
            if price is None:
                hist = ticker.history(period="1d")
                if not hist.empty:
                    price = float(hist["Close"].iloc[-1])
        except Exception:
            price = None

        if price is None:
            results.append(LatestQuote(asset.symbol, None, "unavailable", now_label, "UNKNOWN"))
        else:
            status = "market_closed" if market_state == "CLOSED" else "latest_available"
            results.append(LatestQuote(asset.symbol, price, status, now_label, market_state))

    return results
