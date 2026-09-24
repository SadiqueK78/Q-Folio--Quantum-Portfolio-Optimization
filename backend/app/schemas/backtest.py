from pydantic import BaseModel, Field


class BacktestRequest(BaseModel):
    strategy: str = Field(default="max_sharpe",
                           pattern="^(equal_weight|min_volatility|max_sharpe|risk_parity)$")
    frequency: str = Field(default="monthly", pattern="^(daily|weekly|monthly|quarterly)$")
    window_type: str = Field(default="rolling", pattern="^(rolling|expanding)$")
    lookback_days: int = Field(default=504, ge=60, le=2520)
    initial_capital: float = Field(default=100_000.0, gt=0)
    max_weight: float = Field(default=0.20, gt=0, le=1)
    min_holdings: int | None = Field(default=5, ge=1)
    max_holdings: int | None = Field(default=10, ge=1)
    transaction_cost_pct: float = Field(default=0.0010, ge=0, le=0.05)
    risk_free_rate: float = Field(default=0.06, ge=0, le=0.3)
    start_date: str | None = None
    end_date: str | None = None
