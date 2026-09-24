from fastapi import APIRouter, HTTPException
import pandas as pd
from app.services.pipeline import get_returns_and_risk, get_universe, get_latest_quotes
from app.data.universe import sector_map
from app.optimize import classical
from app.optimize.constraints import PortfolioConstraints, validate_feasibility
from app.optimize.portfolio import construct_portfolio
from app.optimize.qubo import build_qubo, decode_solution, solve_qubo, qubo_to_dense_matrix
from app.optimize.qaoa import run_qaoa, MAX_QAOA_QUBITS
from app.optimize.compare import run_comparison, build_comparison_table
from app.optimize.dynamic import adjust_expected_returns, build_reason
from app.agents.news_agents import run_news_pipeline
from app.schemas.optimize import OptimizeRequest, QuboRequest, CompareRequest, ReoptimizeRequest

router = APIRouter(tags=["optimization"])


def _build_constraints(req: OptimizeRequest) -> PortfolioConstraints:
    return PortfolioConstraints(
        budget=req.budget, min_weight=req.min_weight, max_weight=req.max_weight,
        sector_bounds={b.sector: (b.min_pct, b.max_pct) for b in req.sector_bounds},
        min_holdings=req.min_holdings, max_holdings=req.max_holdings,
        transaction_cost_pct=req.transaction_cost_pct,
    )


def _weights_response(result: dict, ctx: dict, constraints: PortfolioConstraints, req: OptimizeRequest):
    sectors = sector_map(get_universe())
    quotes = {q.symbol: q.price for q in get_latest_quotes() if q.price}
    fallback_prices = {sym: float(ctx["bundle"].adj_close[sym].dropna().iloc[-1])
                        for sym in ctx["bundle"].adj_close.columns}
    prices = {**fallback_prices, **quotes}
    constructed = construct_portfolio(result["weights"], req.budget, constraints, prices,
                                       whole_shares=req.whole_shares, sectors=sectors)
    return {
        "method": result.get("method"),
        "statistics": {k: round(v, 5) for k, v in result["statistics"].items()},
        "weights": result["weights"].round(5).to_dict(),
        "holdings": [
            {"symbol": h.symbol, "sector": sectors.get(h.symbol), "weight_pct": round(h.weight * 100, 2),
             "amount": h.amount, "price": h.price, "shares": h.shares}
            for h in sorted(constructed.holdings, key=lambda x: -x.weight)
        ],
        "budget": req.budget, "total_invested": constructed.total_invested,
        "remaining_cash": constructed.remaining_cash, "transaction_cost": constructed.transaction_cost,
        "utilization_pct": constructed.utilization_pct, "validation": constructed.validation,
        "data_source": ctx["bundle"].source_label,
    }


@router.post("/optimize/feasibility")
def check_feasibility(req: OptimizeRequest):
    constraints = _build_constraints(req)
    result = validate_feasibility(constraints, n_assets=len(get_universe()))
    return {"feasible": result.feasible, "reasons": result.reasons, "suggestions": result.suggestions}


@router.post("/optimize/classical")
def optimize_classical(req: OptimizeRequest):
    ctx = get_returns_and_risk(req.frequency)
    sectors = sector_map(get_universe())
    constraints = _build_constraints(req)

    feas = validate_feasibility(constraints, n_assets=len(get_universe()))
    if not feas.feasible:
        raise HTTPException(400, detail={"error": "Optimization cannot be performed: infeasible constraints.",
                                          "reasons": feas.reasons, "suggestions": feas.suggestions})

    strategy_fn = {
        "equal_weight": lambda: classical.equal_weight(ctx["mu"], ctx["cov"], req.risk_free_rate),
        "min_volatility": lambda: classical.minimum_volatility(ctx["mu"], ctx["cov"], sectors, constraints, req.risk_free_rate),
        "max_sharpe": lambda: classical.maximum_sharpe(ctx["mu"], ctx["cov"], sectors, constraints, req.risk_free_rate),
        "risk_parity": lambda: classical.risk_parity(ctx["mu"], ctx["cov"], sectors, constraints, req.risk_free_rate),
    }[req.strategy]

    try:
        result = strategy_fn()
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc))

    return _weights_response(result, ctx, constraints, req)


@router.post("/optimize/qubo")
def optimize_qubo(req: QuboRequest):
    ctx = get_returns_and_risk(req.frequency)
    sectors = sector_map(get_universe())
    constraints = _build_constraints(req)

    feas = validate_feasibility(constraints, n_assets=len(get_universe()))
    if not feas.feasible:
        raise HTTPException(400, detail={"error": "Optimization cannot be performed: infeasible constraints.",
                                          "reasons": feas.reasons, "suggestions": feas.suggestions})

    problem = build_qubo(ctx["mu"], ctx["cov"], sectors, constraints, req.risk_aversion,
                          req.penalty_budget, req.penalty_holdings, req.penalty_sector, req.weight_step)
    if req.solver == "exact" and len(problem.variables) > 20:
        raise HTTPException(400, detail=f"Exact solver only supports <=20 binary variables; this problem has "
                                         f"{len(problem.variables)}. Use solver=simulated_annealing or increase weight_step.")
    sample = solve_qubo(problem, method=req.solver, num_reads=req.num_reads)
    weights = decode_solution(problem, sample, list(ctx["mu"].index))
    stats = classical._stats(weights.to_numpy() if weights.sum() == 0 else (weights / weights.sum()).to_numpy(),
                              ctx["mu"].to_numpy(), ctx["cov"].to_numpy(), req.risk_free_rate)
    norm_weights = weights / weights.sum() if weights.sum() > 0 else weights

    resp = _weights_response({"weights": norm_weights, "statistics": stats, "method": f"QUBO ({req.solver})"},
                              ctx, constraints, req)
    resp["qubo"] = {
        "n_binary_variables": len(problem.variables),
        "n_levels_per_asset": problem.n_levels,
        "penalty_terms": problem.penalty_terms,
        "matrix_preview": qubo_to_dense_matrix(problem)[:10, :10].round(4).tolist(),
    }
    return resp


@router.post("/optimize/qaoa")
def optimize_qaoa(req: QuboRequest):
    ctx = get_returns_and_risk(req.frequency)
    sectors = sector_map(get_universe())
    constraints = _build_constraints(req)

    problem = build_qubo(ctx["mu"], ctx["cov"], sectors, constraints, req.risk_aversion,
                          req.penalty_budget, req.penalty_holdings, req.penalty_sector, req.weight_step)
    if len(problem.variables) > MAX_QAOA_QUBITS:
        raise HTTPException(400, detail=f"This problem needs {len(problem.variables)} qubits; the QAOA "
                                         f"simulator supports up to {MAX_QAOA_QUBITS}. Increase weight_step "
                                         f"or reduce the asset count.")
    result = run_qaoa(problem, p_layers=2)
    weights = decode_solution(problem, result.best_sample, list(ctx["mu"].index))
    norm_weights = weights / weights.sum() if weights.sum() > 0 else weights
    stats = classical._stats(norm_weights.to_numpy(), ctx["mu"].to_numpy(), ctx["cov"].to_numpy(), req.risk_free_rate)

    resp = _weights_response({"weights": norm_weights, "statistics": stats,
                               "method": f"QAOA Simulator (p={result.p_layers})"}, ctx, constraints, req)
    resp["qaoa"] = {"n_qubits": result.n_qubits, "p_layers": result.p_layers, "note": result.runtime_note}
    return resp


@router.post("/optimize/compare")
def optimize_compare(req: CompareRequest):
    ctx = get_returns_and_risk(req.frequency)
    sectors = sector_map(get_universe())
    constraints = _build_constraints(req)

    feas = validate_feasibility(constraints, n_assets=len(get_universe()))
    if not feas.feasible:
        raise HTTPException(400, detail={"error": "Optimization cannot be performed: infeasible constraints.",
                                          "reasons": feas.reasons, "suggestions": feas.suggestions})

    results = run_comparison(
        mu=ctx["mu"], cov=ctx["cov"], sectors=sectors, constraints=constraints,
        risk_free_rate=req.risk_free_rate, risk_aversion=req.risk_aversion,
        penalty_budget=req.penalty_budget, penalty_holdings=req.penalty_holdings,
        penalty_sector=req.penalty_sector, weight_step=req.weight_step,
        qubo_num_reads=req.num_reads, include_qaoa=req.include_qaoa, qaoa_p_layers=req.qaoa_p_layers,
    )
    table = build_comparison_table(results)
    return {"data_source": ctx["bundle"].source_label, "comparison_table": table}


@router.post("/portfolio/reoptimize")
def reoptimize(req: ReoptimizeRequest):
    """Dynamic reoptimization (Section 30): adjusts expected returns using
    current news/event impact scores, re-runs the chosen strategy, and
    returns Current vs Recommended so the caller can decide whether to
    rebalance."""
    ctx = get_returns_and_risk(req.frequency)
    sectors = sector_map(get_universe())
    constraints = _build_constraints(req)
    names = list(ctx["mu"].index)

    feas = validate_feasibility(constraints, n_assets=len(get_universe()))
    if not feas.feasible:
        raise HTTPException(400, detail={"error": "Optimization cannot be performed: infeasible constraints.",
                                          "reasons": feas.reasons, "suggestions": feas.suggestions})

    # --- Current portfolio: either supplied by the caller, or equal-weight baseline ---
    if req.current_weights:
        current_weights = pd.Series(req.current_weights).reindex(names).fillna(0.0)
        if current_weights.sum() > 0:
            current_weights = current_weights / current_weights.sum()
        current_label = "Supplied by caller"
    else:
        current_weights = pd.Series(1.0 / len(names), index=names)
        current_label = "Equal-weight baseline (no current portfolio supplied)"
    current_stats = classical._stats(current_weights.to_numpy(), ctx["mu"].to_numpy(), ctx["cov"].to_numpy(), req.risk_free_rate)

    # --- Event-adjusted expected returns ---
    adjustments: dict[str, float] = {}
    news_note = "News adjustment not requested."
    if req.apply_news_adjustment:
        news_result = run_news_pipeline(get_universe())
        adjustments = news_result["adjustments"]
        news_note = f"Applied event-adjusted expected returns ({news_result['data_source']} news data)."
        mu_for_opt = adjust_expected_returns(ctx["mu"], adjustments)
    else:
        mu_for_opt = ctx["mu"]

    strategy_fn = {
        "equal_weight": lambda: classical.equal_weight(mu_for_opt, ctx["cov"], req.risk_free_rate),
        "min_volatility": lambda: classical.minimum_volatility(mu_for_opt, ctx["cov"], sectors, constraints, req.risk_free_rate),
        "max_sharpe": lambda: classical.maximum_sharpe(mu_for_opt, ctx["cov"], sectors, constraints, req.risk_free_rate),
        "risk_parity": lambda: classical.risk_parity(mu_for_opt, ctx["cov"], sectors, constraints, req.risk_free_rate),
    }[req.strategy]

    try:
        recommended = strategy_fn()
    except RuntimeError as exc:
        raise HTTPException(400, detail=str(exc))

    rec_weights = recommended["weights"].reindex(names).fillna(0.0)

    diffs = []
    for symbol in names:
        before = float(current_weights.get(symbol, 0.0))
        after = float(rec_weights.get(symbol, 0.0))
        adj = adjustments.get(symbol, 0.0)
        if abs(after - before) < 1e-4 and abs(adj) < 1e-4:
            continue
        diffs.append({
            "symbol": symbol, "sector": sectors.get(symbol),
            "current_pct": round(before * 100, 2), "recommended_pct": round(after * 100, 2),
            "change_pct": round((after - before) * 100, 2), "news_adjustment": round(adj, 4),
            "reason": build_reason(symbol, adj, before, after),
        })
    diffs.sort(key=lambda d: -abs(d["change_pct"]))

    return {
        "data_source": ctx["bundle"].source_label,
        "current": {"label": current_label, "weights": current_weights.round(4).to_dict(),
                     "statistics": {k: round(v, 5) for k, v in current_stats.items()}},
        "recommended": {"label": f"{recommended['method']} ({news_note})",
                          "weights": rec_weights.round(4).to_dict(),
                          "statistics": {k: round(v, 5) for k, v in recommended["statistics"].items()}},
        "news_adjustments": {k: round(v, 4) for k, v in adjustments.items()},
        "diff": diffs,
        "note": news_note,
    }
