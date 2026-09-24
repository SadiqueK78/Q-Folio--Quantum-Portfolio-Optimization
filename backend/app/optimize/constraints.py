"""
Portfolio constraints + feasibility validation (Sections 10-13, 50).

The optimizer never runs against constraints without this module first
checking they're satisfiable — a solver crashing with an opaque error is
treated as a bug, per Section 50.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class PortfolioConstraints:
    budget: float = 100_000.0
    min_weight: float = 0.0
    max_weight: float = 0.20
    sector_bounds: dict[str, tuple[float, float]] = field(default_factory=dict)  # sector -> (lo, hi)
    min_holdings: int | None = 5
    max_holdings: int | None = 10
    transaction_cost_pct: float = 0.0010
    exclusions: set[str] = field(default_factory=set)


@dataclass
class FeasibilityResult:
    feasible: bool
    reasons: list[str]
    suggestions: list[str]


def validate_feasibility(
    constraints: PortfolioConstraints,
    n_assets: int,
    sector_membership_counts: dict[str, int] | None = None,
) -> FeasibilityResult:
    reasons: list[str] = []
    suggestions: list[str] = []

    max_h = constraints.max_holdings or n_assets
    min_h = constraints.min_holdings or 0

    if min_h > n_assets:
        reasons.append(f"Minimum holdings ({min_h}) exceeds universe size ({n_assets}).")
        suggestions.append("Reduce minimum holdings or expand the asset universe.")

    if min_h > max_h:
        reasons.append(f"Minimum holdings ({min_h}) exceeds maximum holdings ({max_h}).")
        suggestions.append("Set minimum holdings <= maximum holdings.")

    # Can `min_h` assets each respecting max_weight sum to >= 100%?
    if constraints.max_weight * max_h < 1.0 - 1e-9:
        needed = 1.0 / constraints.max_weight
        reasons.append(
            f"With a {constraints.max_weight:.0%} max allocation per asset, at least "
            f"{needed:.1f} holdings are needed to reach 100% budget, but max holdings is {max_h}."
        )
        suggestions.append(
            f"Increase max allocation above {1/max_h:.0%}, or raise max holdings above {needed:.0f}."
        )

    # Can `max_h` assets each at least min_weight avoid forcing >100%?
    if constraints.min_weight * min_h > 1.0 + 1e-9:
        reasons.append(
            f"Minimum allocation {constraints.min_weight:.0%} across {min_h} required holdings "
            f"exceeds 100% of budget."
        )
        suggestions.append("Lower the minimum per-asset allocation or minimum holdings count.")

    if constraints.min_weight > constraints.max_weight:
        reasons.append("Minimum weight is greater than maximum weight.")
        suggestions.append("Set minimum weight <= maximum weight.")

    for sector, (lo, hi) in constraints.sector_bounds.items():
        if lo > hi:
            reasons.append(f"Sector '{sector}' has min bound > max bound.")
            suggestions.append(f"Fix sector '{sector}' bounds so min <= max.")
        if sector_membership_counts is not None:
            count = sector_membership_counts.get(sector, 0)
            if count == 0 and hi > 0:
                reasons.append(f"Sector '{sector}' has a bound but no assets belong to it.")
                suggestions.append(f"Remove the bound for '{sector}' or add assets from that sector.")
            elif count and lo > count * constraints.max_weight + 1e-9:
                reasons.append(
                    f"Sector '{sector}' minimum ({lo:.0%}) cannot be reached: only {count} "
                    f"asset(s) available at max {constraints.max_weight:.0%} each."
                )
                suggestions.append(f"Lower the minimum bound for sector '{sector}'.")

    total_sector_min = sum(lo for lo, _ in constraints.sector_bounds.values())
    if total_sector_min > 1.0 + 1e-9:
        reasons.append(f"Sum of sector minimums ({total_sector_min:.0%}) exceeds 100%.")
        suggestions.append("Reduce one or more sector minimum bounds.")

    if constraints.budget <= 0:
        reasons.append("Budget must be positive.")
        suggestions.append("Set a budget greater than ₹0.")

    return FeasibilityResult(feasible=len(reasons) == 0, reasons=reasons, suggestions=suggestions)
