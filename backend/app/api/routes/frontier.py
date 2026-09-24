from fastapi import APIRouter, Query
from app.optimize import classical
from app.optimize.constraints import PortfolioConstraints
from app.services.pipeline import get_returns_and_risk, get_universe
from app.data.universe import sector_map

router = APIRouter(tags=["efficient frontier"])


@router.get("/efficient-frontier")
def efficient_frontier(
    frequency: str = Query("monthly", pattern="^(daily|weekly|monthly)$"),
    max_weight: float = Query(0.20, gt=0, le=1),
    n_points: int = Query(20, ge=5, le=50),
):
    ctx = get_returns_and_risk(frequency)
    constraints = PortfolioConstraints(max_weight=max_weight, min_weight=0.0)
    frontier = classical.efficient_frontier(ctx["mu"], ctx["cov"], constraints, n_points=n_points)

    min_vol = classical.minimum_volatility(ctx["mu"], ctx["cov"], sector_map(get_universe()), constraints, 0.06)
    max_sh = classical.maximum_sharpe(ctx["mu"], ctx["cov"], sector_map(get_universe()), constraints, 0.06)

    return {
        "data_source": ctx["bundle"].source_label,
        "frontier": [{"return": round(p["return"], 5), "risk": round(p["risk"], 5)} for p in frontier],
        "min_volatility_point": {"return": round(min_vol["statistics"]["return"], 5),
                                  "risk": round(min_vol["statistics"]["risk"], 5)},
        "max_sharpe_point": {"return": round(max_sh["statistics"]["return"], 5),
                              "risk": round(max_sh["statistics"]["risk"], 5)},
    }
