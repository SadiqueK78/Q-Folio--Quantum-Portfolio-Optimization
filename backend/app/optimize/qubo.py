"""
QUBO formulation of the portfolio problem (Sections 20-24) — the classical
Markowitz problem, discretized into binary variables, exactly as the
reference PDF's closing section sets up:

    max_w  w^T mu - lambda * w^T Sigma w      s.t.  sum(w) = 1, bounds

becomes, after discretizing each asset's weight into levels
{0, step, 2*step, ..., max_weight}:

    x_{i,k} in {0,1}   -- "asset i is allocated exactly level k"
    w_i = sum_k level(k) * x_{i,k}

QUBO objective (to MINIMIZE):

    Q = - alpha * (return term, linear in x)
        + beta  * (risk term, quadratic in x, from Sigma)
        + gamma * (budget penalty: (sum_i w_i - 1)^2 )
        + delta * (one-hot penalty: for each asset, (sum_k x_{i,k} - 1)^2 )
        + eps   * (holdings-count penalty: (sum_{i,k>0} x_{i,k} - target)^2 )
        + zeta  * (sector penalty per sector bound)

Every coefficient below is derived from the actual mu/Sigma/constraints
passed in — never a random or placeholder Q matrix (per Section 22's
explicit requirement).
"""
from __future__ import annotations

from dataclasses import dataclass

import numpy as np
import pandas as pd

from app.optimize.constraints import PortfolioConstraints


@dataclass
class QuboVariable:
    asset: str
    level_index: int
    weight_value: float
    var_id: int


@dataclass
class QuboProblem:
    Q: dict[tuple[int, int], float]
    variables: list[QuboVariable]
    n_assets: int
    n_levels: int
    penalty_terms: dict[str, float]


def build_levels(max_weight: float, step: float) -> list[float]:
    """Discrete allocation levels: 0%, step, 2*step, ..., up to max_weight."""
    n = int(round(max_weight / step))
    return [round(k * step, 6) for k in range(n + 1)]


def build_qubo(
    mu: pd.Series,
    cov: pd.DataFrame,
    sectors: dict[str, str],
    constraints: PortfolioConstraints,
    risk_aversion: float,
    penalty_budget: float,
    penalty_holdings: float,
    penalty_sector: float,
    weight_step: float,
) -> QuboProblem:
    names = list(mu.index)
    n_assets = len(names)
    levels = build_levels(constraints.max_weight, weight_step)
    n_levels = len(levels)

    # Enumerate variables: var_id = i * n_levels + k
    variables: list[QuboVariable] = []
    for i, name in enumerate(names):
        for k, level in enumerate(levels):
            variables.append(QuboVariable(asset=name, level_index=k, weight_value=level,
                                           var_id=i * n_levels + k))

    mu_v = mu.to_numpy()
    cov_v = cov.to_numpy()
    Q: dict[tuple[int, int], float] = {}

    def add(i, j, val):
        key = (i, j) if i <= j else (j, i)
        Q[key] = Q.get(key, 0.0) + val

    # --- Return term (linear, on the diagonal): -alpha * sum_i mu_i * w_i ---
    for i, name in enumerate(names):
        for k, level in enumerate(levels):
            vid = i * n_levels + k
            add(vid, vid, -mu_v[i] * level)

    # --- Risk term (quadratic): +risk_aversion * w^T Sigma w ---
    for i in range(n_assets):
        for k1, l1 in enumerate(levels):
            v1 = i * n_levels + k1
            if l1 == 0:
                continue
            for j in range(n_assets):
                for k2, l2 in enumerate(levels):
                    v2 = j * n_levels + k2
                    if l2 == 0 or v2 < v1:
                        continue
                    coeff = risk_aversion * cov_v[i, j] * l1 * l2
                    if v1 == v2:
                        add(v1, v1, coeff)
                    else:
                        add(v1, v2, coeff)  # cross term counted once, dimod treats Q[i,j]+Q[j,i] via upper-tri

    # --- One-hot penalty per asset: exactly one level selected ---
    # penalty_holdings also reused as the one-hot coefficient scale; keep a
    # dedicated large constant so one-hot is *always* enforced strongly.
    onehot_coeff = max(penalty_holdings, 2.0) * 3.0
    for i in range(n_assets):
        idxs = [i * n_levels + k for k in range(n_levels)]
        # (sum x_k - 1)^2 = sum x_k^2 + 2*sum_{k<k'} x_k x_k' - 2*sum x_k + 1
        for a in idxs:
            add(a, a, onehot_coeff * (1 - 2))  # x_k^2 == x_k for binary
        for ai in range(len(idxs)):
            for aj in range(ai + 1, len(idxs)):
                add(idxs[ai], idxs[aj], onehot_coeff * 2)

    # --- Budget penalty: (sum_i w_i - 1)^2, expanded over all (i,k) pairs ---
    all_ids = [(i * n_levels + k, levels[k]) for i in range(n_assets) for k in range(n_levels)]
    for a_id, a_level in all_ids:
        add(a_id, a_id, penalty_budget * (a_level ** 2 - 2 * a_level))
    for ai in range(len(all_ids)):
        for aj in range(ai + 1, len(all_ids)):
            id1, l1 = all_ids[ai]
            id2, l2 = all_ids[aj]
            if l1 == 0 or l2 == 0:
                continue
            add(id1, id2, penalty_budget * 2 * l1 * l2)

    # --- Holdings-count penalty: encourage (max_holdings) selections with level>0 ---
    target_holdings = constraints.max_holdings or n_assets
    selected_ids = [i * n_levels + k for i in range(n_assets) for k in range(1, n_levels)]
    for a_id in selected_ids:
        add(a_id, a_id, penalty_holdings * (1 - 2 * target_holdings))
    for ai in range(len(selected_ids)):
        for aj in range(ai + 1, len(selected_ids)):
            add(selected_ids[ai], selected_ids[aj], penalty_holdings * 2)

    # --- Sector penalty: (sum_{i in sector} w_i - target_mid)^2 softly keeps within bounds ---
    for sector, (lo, hi) in constraints.sector_bounds.items():
        mid = (lo + hi) / 2
        sector_ids = [(i * n_levels + k, levels[k]) for i, name in enumerate(names)
                      if sectors.get(name) == sector for k in range(n_levels)]
        if not sector_ids:
            continue
        for a_id, a_level in sector_ids:
            add(a_id, a_id, penalty_sector * (a_level ** 2 - 2 * a_level * mid))
        for ai in range(len(sector_ids)):
            for aj in range(ai + 1, len(sector_ids)):
                id1, l1 = sector_ids[ai]
                id2, l2 = sector_ids[aj]
                if l1 == 0 or l2 == 0:
                    continue
                add(id1, id2, penalty_sector * 2 * l1 * l2)

    return QuboProblem(
        Q=Q, variables=variables, n_assets=n_assets, n_levels=n_levels,
        penalty_terms={
            "risk_aversion": risk_aversion, "penalty_budget": penalty_budget,
            "penalty_holdings": penalty_holdings, "penalty_sector": penalty_sector,
            "onehot_coeff": onehot_coeff, "target_holdings": target_holdings,
        },
    )


def qubo_to_dense_matrix(problem: QuboProblem) -> np.ndarray:
    """Dense NxN matrix for visualization (Quantum Lab's QUBO heatmap, Section 40)."""
    n = len(problem.variables)
    mat = np.zeros((n, n))
    for (i, j), v in problem.Q.items():
        mat[i, j] = v
        if i != j:
            mat[j, i] = v
    return mat


def decode_solution(problem: QuboProblem, sample: dict[int, int], names: list[str]) -> pd.Series:
    """Convert a binary sample back into a weight vector. If an asset's
    one-hot constraint was violated by the solver (more/less than one level
    selected), take the highest selected level as a best-effort decode and
    note it as a constraint violation upstream."""
    weights = {name: 0.0 for name in names}
    for v in problem.variables:
        if sample.get(v.var_id, 0) == 1 and v.weight_value > weights[v.asset]:
            weights[v.asset] = v.weight_value
    return pd.Series(weights)


def solve_qubo(
    problem: QuboProblem,
    method: str = "simulated_annealing",
    num_reads: int = 200,
) -> dict[int, int]:
    """
    method: "exact" (dimod.ExactSolver, only for tiny problems), or
    "simulated_annealing" (neal — a classical stand-in for a quantum/QAOA
    annealer; this is the same solver a QAOA-simulator or D-Wave hardware
    backend would be swapped in for, per Section 23).
    """
    import dimod

    bqm = dimod.BinaryQuadraticModel.from_qubo(problem.Q)

    if method == "exact":
        if len(problem.variables) > 20:
            raise ValueError("Exact solver is only practical for <= 20 binary variables.")
        sampler = dimod.ExactSolver()
        result = sampler.sample(bqm)
    else:
        import neal
        sampler = neal.SimulatedAnnealingSampler()
        result = sampler.sample(bqm, num_reads=num_reads)

    best = result.first.sample
    return {int(k): int(v) for k, v in best.items()}
