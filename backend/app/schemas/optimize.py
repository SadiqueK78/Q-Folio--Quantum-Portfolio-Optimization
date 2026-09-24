"""Pydantic request/response models for the optimize/portfolio endpoints."""
from __future__ import annotations

from pydantic import BaseModel, Field


class SectorBound(BaseModel):
    sector: str
    min_pct: float = Field(ge=0, le=1)
    max_pct: float = Field(ge=0, le=1)


class OptimizeRequest(BaseModel):
    budget: float = Field(default=100_000.0, gt=0)
    min_weight: float = Field(default=0.0, ge=0, le=1)
    max_weight: float = Field(default=0.20, gt=0, le=1)
    min_holdings: int | None = Field(default=5, ge=1)
    max_holdings: int | None = Field(default=10, ge=1)
    transaction_cost_pct: float = Field(default=0.0010, ge=0, le=0.05)
    sector_bounds: list[SectorBound] = Field(default_factory=list)
    frequency: str = Field(default="monthly", pattern="^(daily|weekly|monthly)$")
    risk_free_rate: float = Field(default=0.06, ge=0, le=0.3)
    strategy: str = Field(default="max_sharpe",
                           pattern="^(equal_weight|min_volatility|max_sharpe|risk_parity)$")
    whole_shares: bool = True


class QuboRequest(OptimizeRequest):
    risk_aversion: float = Field(default=3.0, gt=0)
    penalty_budget: float = Field(default=8.0, gt=0)
    penalty_holdings: float = Field(default=4.0, gt=0)
    penalty_sector: float = Field(default=4.0, gt=0)
    weight_step: float = Field(default=0.05, gt=0, le=0.5)
    num_reads: int = Field(default=200, ge=10, le=2000)
    solver: str = Field(default="simulated_annealing", pattern="^(simulated_annealing|exact)$")


class CompareRequest(QuboRequest):
    include_qaoa: bool = True
    qaoa_p_layers: int = Field(default=2, ge=1, le=5)


class ReoptimizeRequest(OptimizeRequest):
    current_weights: dict[str, float] | None = Field(
        default=None,
        description="Symbol -> weight (0-1). If omitted, an equal-weight baseline is used as 'current'.",
    )
    apply_news_adjustment: bool = True

