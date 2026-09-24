"""
Configurable asset universe (Section 3).

Ships with a default 10-company, 10-sector universe so the platform is usable
out of the box, but nothing downstream is hard-coded to these specific
tickers — callers pass a list of Asset objects everywhere.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Asset:
    symbol: str          # exchange ticker, e.g. "RELIANCE.NS" or "AAPL"
    name: str
    sector: str
    industry: str = ""
    exchange: str = ""
    currency: str = "INR"
    data_source: str = "yahoo"


# Default universe: 10 companies, 10 distinct sectors, NSE-listed (India) so it
# lines up with the reference PDF's stock choices and the ₹ budget convention.
# Swap this list (or load one from a config/DB) to use a different universe —
# nothing else in the codebase assumes exactly these tickers.
DEFAULT_UNIVERSE: list[Asset] = [
    Asset("TCS.NS", "Tata Consultancy Services", "Technology", "IT Services", "NSE", "INR"),
    Asset("HDFCBANK.NS", "HDFC Bank", "Financials", "Private Bank", "NSE", "INR"),
    Asset("SUNPHARMA.NS", "Sun Pharmaceutical", "Healthcare", "Pharmaceuticals", "NSE", "INR"),
    Asset("RELIANCE.NS", "Reliance Industries", "Energy", "Oil, Gas & Retail Conglomerate", "NSE", "INR"),
    Asset("HINDUNILVR.NS", "Hindustan Unilever", "Consumer Goods", "FMCG", "NSE", "INR"),
    Asset("MARUTI.NS", "Maruti Suzuki", "Automotive", "Passenger Vehicles", "NSE", "INR"),
    Asset("BHARTIARTL.NS", "Bharti Airtel", "Telecommunications", "Wireless Carrier", "NSE", "INR"),
    Asset("LT.NS", "Larsen & Toubro", "Industrials", "Engineering & Construction", "NSE", "INR"),
    Asset("TITAN.NS", "Titan Company", "Retail", "Jewellery & Watches", "NSE", "INR"),
    Asset("ADANIPORTS.NS", "Adani Ports & SEZ", "Infrastructure", "Port Operations", "NSE", "INR"),
]


def sector_map(universe: list[Asset]) -> dict[str, str]:
    return {a.symbol: a.sector for a in universe}


def symbols(universe: list[Asset]) -> list[str]:
    return [a.symbol for a in universe]
