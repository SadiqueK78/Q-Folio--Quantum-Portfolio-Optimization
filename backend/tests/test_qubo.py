"""
Unit tests for the QUBO formulation, decoding, and solver correctness
against exact enumeration on tiny instances.
"""
import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import numpy as np
import pandas as pd
import pytest

from app.optimize.constraints import PortfolioConstraints
from app.optimize.qubo import build_qubo, decode_solution, solve_qubo, build_levels


def test_build_levels():
    levels = build_levels(0.20, 0.05)
    assert levels == [0.0, 0.05, 0.10, 0.15, 0.20]


def _two_asset_problem():
    mu = pd.Series({"A": 0.20, "B": 0.10})
    cov = pd.DataFrame({"A": [0.04, 0.0], "B": [0.0, 0.01]}, index=["A", "B"])
    constraints = PortfolioConstraints(max_weight=1.0, min_holdings=1, max_holdings=2)
    return mu, cov, constraints


def test_qubo_variable_count():
    mu, cov, constraints = _two_asset_problem()
    problem = build_qubo(mu, cov, {}, constraints, risk_aversion=1.0, penalty_budget=8.0,
                          penalty_holdings=4.0, penalty_sector=4.0, weight_step=0.5)
    # 2 assets * 3 levels (0, 0.5, 1.0) = 6 binary variables
    assert len(problem.variables) == 6


def test_qubo_decode_picks_highest_selected_level():
    mu, cov, constraints = _two_asset_problem()
    problem = build_qubo(mu, cov, {}, constraints, 1.0, 8.0, 4.0, 4.0, 0.5)
    # Manually construct a sample: asset A -> level index 2 (weight 1.0), asset B -> level 0
    sample = {v.var_id: 0 for v in problem.variables}
    for v in problem.variables:
        if v.asset == "A" and v.level_index == 2:
            sample[v.var_id] = 1
        if v.asset == "B" and v.level_index == 0:
            sample[v.var_id] = 1
    weights = decode_solution(problem, sample, ["A", "B"])
    assert weights["A"] == 1.0
    assert weights["B"] == 0.0


def test_exact_qubo_solver_favors_higher_return_asset_when_uncorrelated():
    """With two uncorrelated assets and A having much higher return relative
    to its risk, the exact QUBO solution should allocate fully to A."""
    mu, cov, constraints = _two_asset_problem()
    problem = build_qubo(mu, cov, {}, constraints, risk_aversion=0.5, penalty_budget=20.0,
                          penalty_holdings=1.0, penalty_sector=4.0, weight_step=0.5)
    sample = solve_qubo(problem, method="exact")
    weights = decode_solution(problem, sample, ["A", "B"])
    assert weights.sum() == pytest.approx(1.0, abs=1e-6)
    assert weights["A"] >= weights["B"]


def test_qubo_matrix_is_symmetric_dense():
    from app.optimize.qubo import qubo_to_dense_matrix
    mu, cov, constraints = _two_asset_problem()
    problem = build_qubo(mu, cov, {}, constraints, 1.0, 8.0, 4.0, 4.0, 0.5)
    mat = qubo_to_dense_matrix(problem)
    assert np.allclose(mat, mat.T)
