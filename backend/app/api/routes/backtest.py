from fastapi import APIRouter, HTTPException

from app.services.pipeline import get_universe, get_market_data
from app.data.universe import sector_map
from app.optimize.constraints import PortfolioConstraints
from app.backtest.engine import run_backtest
from app.schemas.backtest import BacktestRequest

router = APIRouter(tags=["backtesting"])


@router.post("/backtest")
def backtest(req: BacktestRequest):
    bundle = get_market_data()
    sectors = sector_map(get_universe())
    constraints = PortfolioConstraints(
        max_weight=req.max_weight, min_holdings=req.min_holdings, max_holdings=req.max_holdings,
        transaction_cost_pct=req.transaction_cost_pct,
    )
    try:
        result = run_backtest(
            prices=bundle.adj_close, sectors=sectors, constraints=constraints,
            strategy=req.strategy, frequency=req.frequency, lookback_days=req.lookback_days,
            window_type=req.window_type, initial_capital=req.initial_capital,
            risk_free_rate=req.risk_free_rate, start_date=req.start_date, end_date=req.end_date,
        )
    except ValueError as exc:
        raise HTTPException(400, detail=str(exc))

    def series_to_dict(s):
        return {str(idx.date()): round(float(v), 2) for idx, v in s.items()}

    return {
        "data_source": bundle.source_label,
        "metrics": result.metrics,
        "benchmark_metrics": result.benchmark_metrics,
        "equity_curve": series_to_dict(result.equity_curve),
        "benchmark_equal_weight": series_to_dict(result.benchmark_equal_weight),
        "benchmark_buy_hold": series_to_dict(result.benchmark_buy_hold),
        "drawdown": {str(idx.date()): round(float(v) * 100, 3) for idx, v in result.drawdown.items()},
        "rebalance_events": [
            {"date": e.date, "weights": e.weights, "turnover_pct": round(e.turnover * 100, 2),
             "transaction_cost": e.transaction_cost}
            for e in result.rebalance_events
        ],
        "warnings": result.warnings,
    }
