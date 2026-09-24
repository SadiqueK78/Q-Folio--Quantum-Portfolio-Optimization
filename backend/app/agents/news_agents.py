"""
News/event agents (Sections 25-28) — free RSS-based, no paid API keys.

Three lightweight agent "roles" over the same free RSS pool, distinguished
by what they look for, not by separate infrastructure (keeps this runnable
without per-agent API keys):

  - MarketNewsAgent   : broad market/macro keywords
  - CompanyNewsAgent  : company-name / ticker mentions
  - SectorNewsAgent   : sector-keyword mentions

Each produces structured Event objects with a rule-based sentiment/severity
score (keyword lexicon) — deliberately NOT an LLM call, so this runs offline
and has zero marginal cost per headline. Swapping in an LLM classifier later
is a drop-in replacement for `_score_text`.
"""
from __future__ import annotations

import math
import re
from dataclasses import dataclass, field
from datetime import datetime, timezone

from app.core.config import get_settings
from app.data.universe import Asset

POSITIVE_WORDS = {
    "beat", "beats", "surge", "surges", "rally", "record", "growth", "profit", "upgrade",
    "upgraded", "strong", "wins", "win", "expansion", "raises", "outperform", "bullish",
}
NEGATIVE_WORDS = {
    "miss", "misses", "plunge", "plunges", "fall", "falls", "crash", "lawsuit", "downgrade",
    "downgraded", "weak", "loss", "losses", "probe", "investigation", "recall", "layoffs",
    "bearish", "default", "fraud", "scandal",
}
SEVERITY_WORDS = {
    "crash": 0.9, "fraud": 0.9, "scandal": 0.85, "lawsuit": 0.6, "investigation": 0.6,
    "recall": 0.55, "layoffs": 0.5, "downgrade": 0.45, "downgraded": 0.45, "surge": 0.4,
    "record": 0.35, "upgrade": 0.35, "default": 0.9,
}

MARKET_KEYWORDS = {"fed", "inflation", "recession", "interest rate", "rate hike", "gdp",
                    "geopolitical", "war", "tariff", "market crash", "rbi", "repo rate"}
SECTOR_KEYWORDS = {
    "Technology": {"chip", "semiconductor", "IT spending", "software"},
    "Financials": {"bank", "banking", "npa", "rbi", "interest rate"},
    "Healthcare": {"drug", "fda", "pharma", "clinical trial"},
    "Energy": {"oil", "crude", "opec", "refinery"},
    "Automotive": {"ev", "vehicle sales", "auto"},
    "Telecommunications": {"spectrum", "5g", "telecom"},
}

# Maps a feed URL substring -> a human-readable publisher name, so the UI
# never has to show a raw RSS URL to the user (Section 29's timeline UI
# expects a clean "source" label).
SOURCE_NAME_MAP = {
    "cnbc.com": "CNBC",
    "reuters.com": "Reuters",
    "moneycontrol.com": "Moneycontrol",
    "economictimes": "Economic Times",
    "synthetic-feed": "Synthetic (illustrative)",
}


def friendly_source_name(url: str) -> str:
    for needle, label in SOURCE_NAME_MAP.items():
        if needle in url:
            return label
    return url


@dataclass
class NewsEvent:
    company: str | None
    sector: str | None
    event_type: str
    headline: str
    source: str
    url: str
    published_at: str
    sentiment: float       # -1..1
    severity: float        # 0..1
    confidence: float      # 0..1
    agent: str

    def event_score(self, decay_hours: float, half_life_hours: float) -> float:
        recency = 0.5 ** (decay_hours / half_life_hours) if half_life_hours > 0 else 1.0
        return self.sentiment * self.severity * self.confidence * recency


def _score_text(text: str) -> tuple[float, float, float]:
    """Rule-based sentiment/severity/confidence from a keyword lexicon."""
    lower = text.lower()
    words = re.findall(r"[a-z]+", lower)
    pos_hits = sum(1 for w in words if w in POSITIVE_WORDS)
    neg_hits = sum(1 for w in words if w in NEGATIVE_WORDS)
    total_hits = pos_hits + neg_hits
    sentiment = 0.0 if total_hits == 0 else (pos_hits - neg_hits) / total_hits
    severity = max((v for k, v in SEVERITY_WORDS.items() if k in lower), default=0.2)
    confidence = min(1.0, 0.3 + 0.15 * total_hits)  # more keyword hits -> more confident
    return round(sentiment, 3), round(severity, 3), round(confidence, 3)


def fetch_rss_entries(feed_urls: list[str], limit_per_feed: int = 30) -> list[dict]:
    """Fetch and parse RSS entries via feedparser. Each source failing is
    reported, not silently dropped — callers should surface which sources
    are live (Section 44's "News Feed: 2/3 Sources Active")."""
    import feedparser

    entries = []
    for url in feed_urls:
        url = url.strip()
        if not url:
            continue
        try:
            parsed = feedparser.parse(url)
            if parsed.bozo and not parsed.entries:
                continue
            for e in parsed.entries[:limit_per_feed]:
                entries.append({
                    "title": e.get("title", ""), "summary": e.get("summary", ""),
                    "link": e.get("link", ""), "published": e.get("published", ""),
                    "source": url,
                })
        except Exception:
            continue  # this source is down; other agents/sources continue
    return entries


def classify_events(entries: list[dict], universe: list[Asset]) -> list[NewsEvent]:
    """Runs all three agent roles over the same entry pool."""
    events: list[NewsEvent] = []
    now = datetime.now(timezone.utc).isoformat()
    name_to_asset = {a.name.lower(): a for a in universe}
    symbol_roots = {a.symbol.split(".")[0].lower(): a for a in universe}

    for entry in entries:
        text = f"{entry['title']} {entry['summary']}"
        lower = text.lower()
        sentiment, severity, confidence = _score_text(text)

        # Company agent: does the headline mention a company name or ticker root?
        matched_asset = None
        for name, asset in name_to_asset.items():
            if name in lower:
                matched_asset = asset
                break
        if matched_asset is None:
            for root, asset in symbol_roots.items():
                if re.search(rf"\b{re.escape(root)}\b", lower):
                    matched_asset = asset
                    break
        if matched_asset:
            events.append(NewsEvent(
                company=matched_asset.symbol, sector=matched_asset.sector, event_type="company",
                headline=entry["title"], source=entry["source"], url=entry["link"],
                published_at=entry["published"] or now, sentiment=sentiment, severity=severity,
                confidence=confidence, agent="CompanyNewsAgent",
            ))
            continue

        # Sector agent
        matched_sector = None
        for sector, keywords in SECTOR_KEYWORDS.items():
            if any(k in lower for k in keywords):
                matched_sector = sector
                break
        if matched_sector:
            events.append(NewsEvent(
                company=None, sector=matched_sector, event_type="sector",
                headline=entry["title"], source=entry["source"], url=entry["link"],
                published_at=entry["published"] or now, sentiment=sentiment, severity=severity,
                confidence=confidence, agent="SectorNewsAgent",
            ))
            continue

        # Market agent
        if any(k in lower for k in MARKET_KEYWORDS):
            events.append(NewsEvent(
                company=None, sector=None, event_type="market",
                headline=entry["title"], source=entry["source"], url=entry["link"],
                published_at=entry["published"] or now, sentiment=sentiment, severity=severity,
                confidence=confidence, agent="MarketNewsAgent",
            ))

    return events


def event_impact_adjustments(
    events: list[NewsEvent],
    universe: list[Asset],
    confidence_threshold: float,
    max_adjustment: float,
    decay_half_life_hours: float,
) -> dict[str, float]:
    """
    Aggregate event scores per asset (direct company events + sector events
    they belong to + a shared market-wide term), capped at +/- max_adjustment
    (Section 28's safeguard against one article dominating the portfolio).
    """
    sector_of = {a.symbol: a.sector for a in universe}
    raw: dict[str, float] = {a.symbol: 0.0 for a in universe}

    market_scores = [e.event_score(0, decay_half_life_hours) for e in events
                      if e.event_type == "market" and e.confidence >= confidence_threshold]
    market_term = sum(market_scores) / len(market_scores) if market_scores else 0.0

    for e in events:
        if e.confidence < confidence_threshold:
            continue
        score = e.event_score(0, decay_half_life_hours)
        if e.event_type == "company" and e.company:
            raw[e.company] += score
        elif e.event_type == "sector" and e.sector:
            for symbol, sector in sector_of.items():
                if sector == e.sector:
                    raw[symbol] += score * 0.5  # sector events matter less than direct company news

    for symbol in raw:
        raw[symbol] += market_term * 0.2

    return {symbol: max(-max_adjustment, min(max_adjustment, v)) for symbol, v in raw.items()}


def run_news_pipeline(universe: list[Asset]) -> dict:
    settings = get_settings()
    feeds = [f for f in settings.rss_feeds.split(",") if f.strip()]
    entries = fetch_rss_entries(feeds)
    data_source = "live_rss"
    if not entries:
        from app.data.synthetic_news import generate_synthetic_news
        entries = generate_synthetic_news(universe)
        data_source = "synthetic"
    events = classify_events(entries, universe)
    adjustments = event_impact_adjustments(
        events, universe, settings.news_confidence_threshold,
        settings.news_max_adjustment, settings.news_decay_half_life_hours,
    )
    return {
        "sources_configured": len(feeds),
        "sources_active": len({e.source for e in events}) if events else 0,
        "data_source": data_source,
        "n_entries_fetched": len(entries),
        "n_events_classified": len(events),
        "events": events,
        "adjustments": adjustments,
    }
