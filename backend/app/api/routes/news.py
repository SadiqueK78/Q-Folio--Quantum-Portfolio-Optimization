from fastapi import APIRouter
from app.agents.news_agents import run_news_pipeline, friendly_source_name
from app.services.pipeline import get_universe

router = APIRouter(tags=["news & events"])


@router.get("/news")
def news():
    result = run_news_pipeline(get_universe())
    return {
        "data_source": result["data_source"],
        "sources_configured": result["sources_configured"],
        "sources_active": result["sources_active"],
        "entries": [
            {"headline": e.headline, "source": friendly_source_name(e.source), "url": e.url,
             "published_at": e.published_at, "event_type": e.event_type, "company": e.company, "sector": e.sector}
            for e in result["events"]
        ],
    }


@router.get("/events")
def events():
    result = run_news_pipeline(get_universe())
    return [
        {
            "company": e.company, "sector": e.sector, "event_type": e.event_type,
            "headline": e.headline, "source": friendly_source_name(e.source), "url": e.url,
            "published_at": e.published_at, "sentiment": e.sentiment,
            "severity": e.severity, "confidence": e.confidence, "agent": e.agent,
        }
        for e in result["events"]
    ]


@router.get("/events/impact")
def events_impact():
    result = run_news_pipeline(get_universe())
    return {
        "data_source": result["data_source"],
        "adjustments": result["adjustments"],
        "note": "Each value is a bounded score in [-max_adjustment, +max_adjustment] combining "
                "sentiment x severity x confidence x recency for company, sector, and market events. "
                "This is a signal for review, not a guaranteed price predictor.",
    }
