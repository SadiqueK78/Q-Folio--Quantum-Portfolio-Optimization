from fastapi import APIRouter, Query
from app.services.pipeline import get_returns_and_risk, get_universe
from app.analytics import risk as riskmod
from app.data.universe import sector_map

router = APIRouter(tags=["risk & returns"])


@router.get("/returns")
def returns(frequency: str = Query("monthly", pattern="^(daily|weekly|monthly)$")):
    ctx = get_returns_and_risk(frequency)
    r = ctx["returns"].tail(24)
    return {
        "frequency": frequency,
        "periods_per_year": ctx["periods_per_year"],
        "data_source": ctx["bundle"].source_label,
        "series": {str(idx.date()): row.round(5).to_dict() for idx, row in r.iterrows()},
    }


@router.get("/risk")
def risk_summary(frequency: str = Query("monthly", pattern="^(daily|weekly|monthly)$")):
    ctx = get_returns_and_risk(frequency)
    sectors = sector_map(get_universe())
    n = len(ctx["mu"])
    equal_w = [1 / n] * n
    report = riskmod.full_risk_report(
        ctx["returns"], equal_w, 0.06 / ctx["periods_per_year"], ctx["periods_per_year"]
    )
    report["data_source"] = ctx["bundle"].source_label
    report["note"] = "Portfolio-level figures shown for an equal-weight reference; POST /optimize/* for an optimized allocation's risk profile."
    return report


@router.get("/covariance")
def covariance(frequency: str = Query("monthly", pattern="^(daily|weekly|monthly)$")):
    ctx = get_returns_and_risk(frequency)
    return {"data_source": ctx["bundle"].source_label, "covariance": ctx["cov"].round(6).to_dict()}


@router.get("/correlation")
def correlation(frequency: str = Query("monthly", pattern="^(daily|weekly|monthly)$")):
    ctx = get_returns_and_risk(frequency)
    return {"data_source": ctx["bundle"].source_label, "correlation": ctx["corr"].round(4).to_dict()}
