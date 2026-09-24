"""
Regression tests for fetch_latest_quotes — this function previously
returned "unavailable" for every asset because yfinance's fast_info object
doesn't support .get() and has no market_state attribute (a real bug found
via the Market Data page showing all quotes blank). These tests pin the
fix in place: price extraction must work across several fast_info shapes,
and market state is computed locally rather than assumed from the API.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from datetime import datetime, timezone

import pandas as pd
import pytest

from app.data.fetcher import _extract_fast_info_price, _nse_market_state, fetch_latest_quotes
from app.data.universe import DEFAULT_UNIVERSE


class _AttrOnlyFastInfo:
    """Mimics a fast_info object that supports attribute access but raises
    on dict-style access — the exact shape that caused the original bug."""
    def __init__(self, price):
        self.last_price = price
    def __getitem__(self, key):
        raise KeyError(key)


class _DictOnlyFastInfo(dict):
    """Mimics a fast_info object that only supports dict-style access."""
    pass


class _BrokenFastInfo:
    def __getattr__(self, name):
        raise AttributeError(name)
    def __getitem__(self, key):
        raise KeyError(key)


def test_extract_price_from_attribute_style_fast_info():
    assert _extract_fast_info_price(_AttrOnlyFastInfo(1234.56)) == pytest.approx(1234.56)


def test_extract_price_from_dict_style_fast_info():
    fi = _DictOnlyFastInfo(lastPrice=555.5)
    assert _extract_fast_info_price(fi) == pytest.approx(555.5)


def test_extract_price_returns_none_when_totally_broken():
    assert _extract_fast_info_price(_BrokenFastInfo()) is None


def test_nse_market_state_weekend_is_closed():
    saturday = datetime(2026, 8, 22, 10, 0, tzinfo=timezone.utc)  # a Saturday
    assert _nse_market_state(saturday) == "CLOSED"


def test_nse_market_state_weekday_midday_ist_is_open():
    # 2026-08-20 10:00 UTC = 15:30 IST -> right at close boundary, still open
    weekday_midday = datetime(2026, 8, 20, 6, 0, tzinfo=timezone.utc)  # 11:30 IST
    assert _nse_market_state(weekday_midday) == "OPEN"


def test_fetch_latest_quotes_recovers_via_history_fallback(monkeypatch):
    """End-to-end regression: even when fast_info is entirely broken, the
    history() fallback must still produce a usable price, not 'unavailable'."""
    import app.data.fetcher as fetcher_mod

    class FakeTicker:
        def __init__(self, symbol):
            self.symbol = symbol
        @property
        def fast_info(self):
            return _BrokenFastInfo()
        def history(self, period="1d"):
            return pd.DataFrame({"Close": [999.0]})

    import yfinance as yf
    monkeypatch.setattr(yf, "Ticker", FakeTicker)

    quotes = fetcher_mod.fetch_latest_quotes(DEFAULT_UNIVERSE[:2])
    assert all(q.price == pytest.approx(999.0) for q in quotes)
    assert all(q.status != "unavailable" for q in quotes)
