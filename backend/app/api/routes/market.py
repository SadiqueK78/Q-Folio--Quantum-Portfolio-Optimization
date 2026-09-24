from fastapi import APIRouter, HTTPException
import pandas as pd
from app.services.pipeline import get_universe, get_market_data, get_latest_quotes

router = APIRouter(tags=["assets & market"])


@router.get("/assets")
def list_assets():
    return [
        {"symbol": a.symbol, "name": a.name, "sector": a.sector, "industry": a.industry,
         "exchange": a.exchange, "currency": a.currency, "data_source": a.data_source}
        for a in get_universe()
    ]


@router.get("/market-data")
def latest_market_data():
    quotes = get_latest_quotes()
    return [
        {"symbol": q.symbol, "price": q.price, "status": q.status,
         "as_of": q.as_of, "market_state": q.market_state}
        for q in quotes
    ]


@router.get("/historical-data")
def historical_data():
    bundle = get_market_data()
    tail = bundle.adj_close.tail(30)
    return {
        "source": bundle.source_label,
        "rows_total": len(bundle.adj_close),
        "columns": list(bundle.adj_close.columns),
        "sample_last_30_days": {
            str(idx.date()): row.round(2).to_dict() for idx, row in tail.iterrows()
        },
    }


RANGE_TO_DAYS = {
    "1m": 21, "3m": 63, "6m": 126, "1y": 252, "2y": 504, "5y": 1260, "10y": 2520, "max": None,
}


@router.get("/prices/{symbol}")
def price_series(symbol: str, range: str = "1y"):
    bundle = get_market_data()
    if symbol not in bundle.adj_close.columns:
        raise HTTPException(404, detail=f"Unknown symbol '{symbol}'. Valid symbols: {list(bundle.adj_close.columns)}")
    if range not in RANGE_TO_DAYS:
        raise HTTPException(400, detail=f"Unsupported range '{range}'. Use one of: {list(RANGE_TO_DAYS)}")

    series = bundle.adj_close[symbol].dropna()
    n_days = RANGE_TO_DAYS[range]
    if n_days is not None:
        series = series.tail(n_days)

    return {
        "symbol": symbol,
        "range": range,
        "data_source": bundle.source_label,
        "series": {str(idx.date()): round(float(v), 2) for idx, v in series.items()},
    }


@router.get("/prices")
def all_price_series(range: str = "1y"):
    """All assets, normalized to 100 at the start of the window, for overlay comparison charts."""
    bundle = get_market_data()
    if range not in RANGE_TO_DAYS:
        raise HTTPException(400, detail=f"Unsupported range '{range}'. Use one of: {list(RANGE_TO_DAYS)}")

    df = bundle.adj_close.copy()
    n_days = RANGE_TO_DAYS[range]
    if n_days is not None:
        df = df.tail(n_days)
    normalized = df / df.bfill().iloc[0] * 100

    return {
        "range": range,
        "data_source": bundle.source_label,
        "symbols": list(df.columns),
        "series": {
            str(idx.date()): {col: (round(float(v), 2) if pd.notna(v) else None) for col, v in row.items()}
            for idx, row in normalized.iterrows()
        },
    }


@router.get("/data-status")
def data_status():
    bundle = get_market_data()
    return {
        "market_data_connected": bundle.source_label in ("live", "cached_stale"),
        "source_label": bundle.source_label,
        "quality_report": bundle.quality_text,
        "warning": None if bundle.source_label == "live" else (
            "Live market data is unavailable in this environment; showing "
            f"{'stale cached' if bundle.source_label == 'cached_stale' else 'synthetic illustrative'} data."
        ),
    }


@router.get("/health")
def health():
    return {"status": "ok"}
