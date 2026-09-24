"""
Synthetic news entries — used only when RSS feeds are unreachable (this
sandbox, or any environment lacking outbound internet), clearly labeled.
Mirrors the same "illustrative data" pattern as app.data.synthetic.
"""
from __future__ import annotations

import random
from datetime import datetime, timedelta, timezone

from app.data.universe import Asset

_TEMPLATES = [
    ("company", "{company} beats quarterly earnings estimates, shares rally"),
    ("company", "{company} announces new product launch"),
    ("company", "{company} faces regulatory investigation over compliance lapse"),
    ("company", "{company} reports leadership change as CFO steps down"),
    ("sector", "{sector} sector sees supply-chain disruption amid global shortages"),
    ("sector", "Analysts upgrade outlook for {sector} sector"),
    ("market", "RBI signals rate hike amid persistent inflation concerns"),
    ("market", "Global markets rattled by geopolitical tension"),
]


def generate_synthetic_news(universe: list[Asset], n: int = 12, seed: int = 3) -> list[dict]:
    rng = random.Random(seed)
    now = datetime.now(timezone.utc)
    sources = ["https://www.cnbc.com/synthetic", "https://feeds.reuters.com/synthetic",
               "https://www.moneycontrol.com/synthetic", "https://economictimes.indiatimes.com/synthetic"]
    entries = []
    for i in range(n):
        kind, template = rng.choice(_TEMPLATES)
        if kind == "company":
            asset = rng.choice(universe)
            title = template.format(company=asset.name)
        elif kind == "sector":
            sector = rng.choice(list({a.sector for a in universe}))
            title = template.format(sector=sector)
        else:
            title = template
        published = (now - timedelta(hours=rng.uniform(0, 72))).isoformat()
        entries.append({
            "title": title, "summary": title, "link": f"https://example-news.local/{i}",
            "published": published, "source": rng.choice(sources),
        })
    return entries
