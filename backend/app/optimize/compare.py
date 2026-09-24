"""
Runs every strategy on the same mu/covariance/constraints and produces the
Classical vs QUBO vs QAOA comparison table (Sections 19, 24, 52). Explicitly
avoids fabricating a "quantum advantage" — reports whatever the numbers are.
"""
from __future__ import annotations

import time

import numpy as np
import pandas as pd

from app.optimize import classical
from app.optimize.constraints import PortfolioConstraints
from app.optimize.qubo import build_qubo, decode_solution, solve_qubo, qubo_to_dense_matrix
from app.optimize.qaoa import run_qaoa, MAX_QAOA_QUBITS


def run_comparison(
    mu: pd.Series,
    cov: pd.DataFrame,
    sectors: dict[str, str],
    constraints: PortfolioConstraints,
    risk_free_rate: float,
    risk_aversion: float,
    penalty_budget: float,
    penalty_holdings: float,
    penalty_sector: float,
    weight_step: float,
    qubo_num_reads: int,
    include_qaoa: bool = True,
    qaoa_p_layers: int = 2,
) -> dict:
    results = {}

    t0 = time.perf_counter()
    results["equal_weight"] = classical.equal_weight(mu, cov, risk_free_rate)
    results["equal_weight"]["runtime_sec"] = time.perf_counter() - t0

    t0 = time.perf_counter()
    try:
        results["min_volatility"] = classical.minimum_volatility(mu, cov, sectors, constraints, risk_free_rate)
        results["min_volatility"]["runtime_sec"] = time.perf_counter() - t0
    except RuntimeError as exc:
        results["min_volatility"] = {"error": str(exc)}

    t0 = time.perf_counter()
    try:
        results["max_sharpe"] = classical.maximum_sharpe(mu, cov, sectors, constraints, risk_free_rate)
        results["max_sharpe"]["runtime_sec"] = time.perf_counter() - t0
    except RuntimeError as exc:
        results["max_sharpe"] = {"error": str(exc)}

    t0 = time.perf_counter()
    try:
        results["risk_parity"] = classical.risk_parity(mu, cov, sectors, constraints, risk_free_rate)
        results["risk_parity"]["runtime_sec"] = time.perf_counter() - t0
    except RuntimeError as exc:
        results["risk_parity"] = {"error": str(exc)}

    # --- QUBO ---
    t0 = time.perf_counter()
    problem = build_qubo(mu, cov, sectors, constraints, risk_aversion, penalty_budget,
                          penalty_holdings, penalty_sector, weight_step)
    sample = solve_qubo(problem, method="simulated_annealing", num_reads=qubo_num_reads)
    weights = decode_solution(problem, sample, list(mu.index))
    runtime = time.perf_counter() - t0
    if weights.sum() > 0:
        w_norm = weights / weights.sum()
    else:
        w_norm = weights
    stats = classical._stats(w_norm.to_numpy(), mu.to_numpy(), cov.to_numpy(), risk_free_rate)
    results["qubo"] = {
        "weights": w_norm, "statistics": stats, "method": "QUBO (Simulated Annealing)",
        "runtime_sec": runtime, "n_binary_variables": len(problem.variables),
        "qubo_matrix_preview": qubo_to_dense_matrix(problem)[:12, :12].round(4).tolist(),
    }

    # --- QAOA ---
    if include_qaoa:
        t0 = time.perf_counter()
        if len(problem.variables) <= MAX_QAOA_QUBITS:
            try:
                qaoa_result = run_qaoa(problem, p_layers=qaoa_p_layers)
                qaoa_weights = decode_solution(problem, qaoa_result.best_sample, list(mu.index))
                runtime = time.perf_counter() - t0
                if qaoa_weights.sum() > 0:
                    qw_norm = qaoa_weights / qaoa_weights.sum()
                else:
                    qw_norm = qaoa_weights
                stats = classical._stats(qw_norm.to_numpy(), mu.to_numpy(), cov.to_numpy(), risk_free_rate)
                results["qaoa"] = {
                    "weights": qw_norm, "statistics": stats, "method": f"QAOA Simulator (p={qaoa_p_layers})",
                    "runtime_sec": runtime, "n_qubits": qaoa_result.n_qubits,
                    "note": qaoa_result.runtime_note,
                }
            except ValueError as exc:
                results["qaoa"] = {"error": str(exc)}
        else:
            results["qaoa"] = {
                "error": f"Problem has {len(problem.variables)} binary variables; QAOA statevector "
                         f"simulation is capped at {MAX_QAOA_QUBITS} for this platform. Reduce the "
                         f"discretization granularity or asset count to run QAOA."
            }

    return results


def build_comparison_table(results: dict) -> list[dict]:
    rows = []
    for key, label in [
        ("equal_weight", "Equal Weight"), ("min_volatility", "Min Volatility"),
        ("max_sharpe", "Max Sharpe"), ("risk_parity", "Risk Parity"),
        ("qubo", "Quantum QUBO"), ("qaoa", "QAOA Simulator"),
    ]:
        r = results.get(key)
        if not r or "error" in r:
            rows.append({"strategy": label, "error": (r or {}).get("error", "not run")})
            continue
        stats = r["statistics"]
        rows.append({
            "strategy": label,
            "return_pct": round(stats["return"] * 100, 2),
            "risk_pct": round(stats["risk"] * 100, 2),
            "sharpe": round(stats["sharpe"], 3),
            "runtime_sec": round(r.get("runtime_sec", 0), 4),
            "n_holdings": int((r["weights"] > 1e-6).sum()),
        })
    return rows
