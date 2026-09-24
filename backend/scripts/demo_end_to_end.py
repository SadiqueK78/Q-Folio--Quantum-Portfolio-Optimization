"""
End-to-end pipeline smoke test / demo (mirrors Section 64's Definition of
Done, items 1-16). Run with:  python -m scripts.demo_end_to_end

Uses real yfinance data if network access is available, otherwise falls back
to the synthetic generator with a clear on-screen label — never silently.
"""
from __future__ import annotations

import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd

from app.core.config import get_settings
from app.data.universe import DEFAULT_UNIVERSE, sector_map
from app.data.fetcher import fetch_historical, clean_prices, DataFetchError
from app.data.synthetic import generate_synthetic_prices
from app.analytics.returns import frequency_returns, periods_per_year
from app.analytics import risk as riskmod
from app.optimize.constraints import PortfolioConstraints, validate_feasibility
from app.optimize.portfolio import construct_portfolio
from app.optimize.compare import run_comparison, build_comparison_table


def line(title: str = "") -> None:
    print("\n" + "=" * 78)
    if title:
        print(title)
        print("=" * 78)


def main():
    settings = get_settings()
    universe = DEFAULT_UNIVERSE
    sectors = sector_map(universe)

    line("1-4. UNIVERSE & DATA")
    print(f"{len(universe)} companies across {len(set(sectors.values()))} sectors:")
    for a in universe:
        print(f"  {a.symbol:14s} {a.name:32s} {a.sector}")

    try:
        close, adj_close, volume, report = fetch_historical(universe, years=settings.historical_years)
        data_source_label = "LIVE (Yahoo Finance)"
    except DataFetchError as exc:
        print(f"\n[data status] Live fetch unavailable ({exc})")
        print("[data status] Falling back to SYNTHETIC illustrative data (clearly labeled, per PDF methodology).")
        adj_close = generate_synthetic_prices(universe, years=settings.historical_years)
        data_source_label = "SYNTHETIC (illustrative — no live network access in this environment)"
        total_cells = adj_close.shape[0] * adj_close.shape[1]

        class _Report:
            def as_text(self_inner):
                return (
                    "Data Quality (synthetic)\n-------------------------\n"
                    f"Assets: {adj_close.shape[1]}\nTrading Days: {adj_close.shape[0]}\n"
                    f"Missing Values: 0.00%\nDuplicates: 0\n"
                )
        report = _Report()

    print(f"\nData Source: {data_source_label}")
    print(report.as_text())

    adj_close = clean_prices(adj_close)

    line("5-7. RETURNS")
    frequency = "monthly"
    returns = frequency_returns(adj_close, frequency)
    ppy = periods_per_year(frequency, settings.trading_days_per_year)
    print(f"Frequency: {frequency} | Periods/year: {ppy} | Observations: {len(returns)}")

    line("8. RISK METRICS")
    mu_periodic = riskmod.expected_return_historical_mean(returns)
    mu = mu_periodic * ppy
    cov = riskmod.covariance_matrix(returns, ppy)
    corr = riskmod.correlation_matrix(returns)
    vol = riskmod.annualize_volatility(riskmod.volatility(returns), ppy)

    print("\nExpected annual return:")
    print((mu * 100).round(2).astype(str) + "%")
    print("\nAnnualized volatility:")
    print((vol * 100).round(2).astype(str) + "%")
    print("\nCorrelation matrix (first 5x5):")
    print(corr.iloc[:5, :5].round(2))

    line("9-13. CONSTRAINTS & FEASIBILITY")
    budget = settings.default_budget
    constraints = PortfolioConstraints(
        budget=budget,
        min_weight=settings.default_min_weight,
        max_weight=settings.default_max_weight,
        sector_bounds={},  # left open by default; UI can populate per Section 12
        min_holdings=settings.default_min_holdings,
        max_holdings=settings.default_max_holdings,
        transaction_cost_pct=settings.default_transaction_cost_pct,
    )
    feasibility = validate_feasibility(constraints, n_assets=len(universe))
    print(f"Budget: ₹{budget:,.0f} | Max weight/asset: {constraints.max_weight:.0%} | "
          f"Holdings: {constraints.min_holdings}-{constraints.max_holdings}")
    print(f"Feasible: {feasibility.feasible}")
    if not feasibility.feasible:
        for r in feasibility.reasons:
            print(f"  ✗ {r}")
        return

    line("18-24. CLASSICAL vs QUBO vs QAOA")
    results = run_comparison(
        mu=mu, cov=cov, sectors=sectors, constraints=constraints,
        risk_free_rate=settings.risk_free_rate, risk_aversion=settings.qubo_risk_aversion,
        penalty_budget=settings.qubo_penalty_budget, penalty_holdings=settings.qubo_penalty_holdings,
        penalty_sector=settings.qubo_penalty_sector, weight_step=settings.qubo_weight_step,
        qubo_num_reads=settings.qubo_num_reads, include_qaoa=True, qaoa_p_layers=2,
    )
    table = build_comparison_table(results)
    df = pd.DataFrame(table)
    print(df.to_string(index=False))

    line("33-34. FINAL ALLOCATION (Max Sharpe strategy)")
    chosen = results["max_sharpe"]["weights"]
    latest_prices = {sym: float(adj_close[sym].dropna().iloc[-1]) for sym in adj_close.columns}
    constructed = construct_portfolio(chosen, budget, constraints, latest_prices,
                                       whole_shares=True, sectors=sectors)
    for h in sorted(constructed.holdings, key=lambda x: -x.weight):
        print(f"  {h.symbol:14s} weight={h.weight*100:5.2f}%  amount=₹{h.amount:10,.2f}  "
              f"price=₹{h.price:9,.2f}  shares={h.shares:.2f}")
    print(f"\nTotal Invested: ₹{constructed.total_invested:,.2f}")
    print(f"Remaining Cash: ₹{constructed.remaining_cash:,.2f}")
    print(f"Transaction Cost: ₹{constructed.transaction_cost:,.2f}")
    print(f"Utilization: {constructed.utilization_pct:.2f}%")
    print(f"\nValidation: {constructed.validation}")

    line("52. CLASSICAL vs QUANTUM — HONEST COMPARISON")
    ms = results["max_sharpe"]["statistics"]
    qb = results["qubo"]["statistics"]
    print(f"Classical Max-Sharpe: return={ms['return']*100:.2f}%  risk={ms['risk']*100:.2f}%  sharpe={ms['sharpe']:.3f}")
    print(f"Quantum QUBO:         return={qb['return']*100:.2f}%  risk={qb['risk']*100:.2f}%  sharpe={qb['sharpe']:.3f}")
    diff = qb["sharpe"] - ms["sharpe"]
    verdict = "higher" if diff > 0.01 else ("lower" if diff < -0.01 else "comparable")
    print(f"\nVerdict: On this discretized {settings.qubo_weight_step:.0%}-step universe, the QUBO solution's "
          f"Sharpe ratio is {verdict} than the continuous classical optimum — as expected, since QUBO is "
          f"constrained to coarser weight levels. No quantum advantage is claimed.")

    line("DONE")


if __name__ == "__main__":
    main()
