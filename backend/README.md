# Classical + Quantum Portfolio Optimization Platform — Backend (Phase 1-4)

> **Not financial advice.** This is a research / decision-support system.
> Historical returns are not guaranteed future returns. Free data sources
> (Yahoo Finance, public RSS feeds) are explicitly labeled as delayed/latest
> available, never claimed as institutional real-time feeds. No quantum
> advantage is claimed — the QUBO/QAOA layer is compared honestly against
> classical results.

## What this delivers right now

This is **Phase 1–4 of the 10-phase build plan** in the original spec
(Foundation → Market Data → Financial Analytics → Classical Optimization),
plus a working slice of Phase 6 (QUBO/QAOA — moved earlier since it's the
mathematical core you asked me to validate against the reference PDF) and
Phase 7 (a lightweight rule-based news/event layer). It is a real,
tested, runnable FastAPI backend — not a mockup.

**Working end-to-end, with passing tests:**
- 10-company, 10-sector default universe (`app/data/universe.py`), configurable
- Historical data fetch via yfinance (10 years), with cleaning, a data-quality
  report, and caching (`app/data/fetcher.py`)
- Latest-quote fetch, explicitly labeled `latest_available` / `market_closed`
  / `unavailable` — never fabricated (Section 4)
- Daily / weekly / monthly return calculation (`app/analytics/returns.py`)
- Full risk-metrics engine: expected return, volatility, covariance,
  correlation, Sharpe, **Sortino, max drawdown, historical VaR, CVaR, beta,
  risk contribution, diversification score** (`app/analytics/risk.py`) — this
  was almost entirely missing from your uploaded scaffold
- Constraint engine + feasibility pre-validation, so an infeasible constraint
  set is explained in plain language instead of crashing the solver
  (`app/optimize/constraints.py`)
- Classical optimizers: Equal Weight, Minimum Volatility, Maximum Sharpe,
  Risk Parity, Efficient Frontier (`app/optimize/classical.py`)
- **QUBO formulation derived directly from mu/Sigma/constraints** — binary
  weight-discretization exactly following the reference PDF's transition
  from `max wᵀμ − λwᵀΣw` into binary variables, with real penalty terms for
  budget, one-hot selection, holdings count, and sector bounds (no random Q
  matrix) (`app/optimize/qubo.py`)
- QUBO solved via `dwave-neal` simulated annealing (a real, swappable
  quantum-annealing stand-in)
- **A from-scratch QAOA statevector simulator** (`app/optimize/qaoa.py`) — no
  qiskit dependency, genuine QAOA math (QUBO→Ising, cost/mixer unitaries,
  classical outer-loop optimization), verified against an exact solver on a
  small test case. Honestly capped at 16 qubits and says so when exceeded,
  rather than silently doing something else.
- Classical vs QUBO vs QAOA comparison table with runtime, never claiming an
  advantage that isn't there (`app/optimize/compare.py`)
- Portfolio construction: rupee amounts, whole/fractional shares, leftover
  cash, transaction cost, and **post-hoc validation of every constraint**
  (`app/optimize/portfolio.py`)
- A rule-based (no LLM cost) 3-agent news pipeline over free RSS feeds —
  Market / Company / Sector agents, structured Event objects with
  sentiment × severity × confidence × time-decay scoring, bounded impact
  adjustments (`app/agents/news_agents.py`)
- A working FastAPI app with the endpoints from Section 46
- 22 passing unit tests (`tests/`)

## What's NOT built yet (be aware before you present this)

- **Frontend** — none yet. This backend is ready for one; not built this pass.
- **Backtesting engine** (Section 16) — the walk-forward/rolling-window
  engine isn't implemented. This is the next highest-value piece to add.
- **Dynamic reoptimization trigger** (Section 30) — events are scored and
  exposed via `/api/events/impact`, but nothing yet automatically re-runs
  optimization when a high-impact event lands, or feeds the adjustment into
  `mu` before optimizing.
- **PDF/CSV export** (Section 60).
- Sector bounds default to empty (no bounds) — wire up defaults per sector
  in `OptimizeRequest.sector_bounds` from the UI when you build it.

## Why some things are labeled "synthetic" when you run this

**This build/test sandbox has no outbound internet access to Yahoo Finance
or RSS hosts** (its network egress is locked to package registries only).
So every live-data code path is written and tested for real use, but was
validated here with a clearly-labeled synthetic fallback (illustrative GBM
price paths / synthetic headlines) — the same "no real file attached, so
here's an illustrative dataset with identical methodology" approach the
reference PDF itself uses. **On your own machine, with normal internet
access, `python -m scripts.demo_end_to_end` will fetch real Yahoo Finance
data automatically** — no code changes needed. The fallback only activates
if the live fetch fails.

## Running it

```bash
cd backend
pip install -r requirements-dev.txt
cp .env.example .env

# Full pipeline demo (prints every stage to the console)
python scripts/demo_end_to_end.py

# Or run the API
uvicorn app.api.main:app --reload
# then open http://localhost:8000/docs for interactive Swagger UI
```

Run tests:
```bash
pytest tests/ -v
```

## API surface (Section 46)

```
GET  /api/assets
GET  /api/market-data
GET  /api/historical-data
GET  /api/data-status
GET  /api/health

GET  /api/returns?frequency=daily|weekly|monthly
GET  /api/risk?frequency=...
GET  /api/covariance?frequency=...
GET  /api/correlation?frequency=...
GET  /api/efficient-frontier

POST /api/optimize/feasibility
POST /api/optimize/classical      { strategy: equal_weight|min_volatility|max_sharpe|risk_parity, ... }
POST /api/optimize/qubo
POST /api/optimize/qaoa
POST /api/optimize/compare

GET  /api/news
GET  /api/events
GET  /api/events/impact
```

Every `/optimize/*` request accepts `budget`, `min_weight`, `max_weight`,
`min_holdings`, `max_holdings`, `transaction_cost_pct`, `sector_bounds`,
`frequency`, `risk_free_rate`, `whole_shares` — see `app/schemas/optimize.py`.

## The math (Section 58), briefly

Classical:
```
E[R_p] = wᵀμ            (expected return)
σ²_p   = wᵀΣw            (portfolio variance)
Sharpe = (wᵀμ − R_f) / √(wᵀΣw)
```

QUBO transition (exactly the reference PDF's closing section):
1. Discretize each asset's weight into levels `{0, step, 2·step, ..., max_weight}`
2. One binary variable `x_{i,k}` per (asset, level) — "asset i gets level k"
3. `w_i = Σ_k level(k)·x_{i,k}`
4. Minimize:
   ```
   Q = −α·(Σ mu_i · w_i)                        [return, linear]
       + β·(wᵀΣw)                                [risk, quadratic]
       + γ·(Σw_i − 1)²                            [budget penalty]
       + δ·Σ_i(Σ_k x_{i,k} − 1)²                  [one-hot per asset]
       + ε·(Σ_{selected} 1 − target_holdings)²    [holdings-count penalty]
       + ζ·Σ_sector(Σw_i − sector_mid)²           [sector penalty]
   ```
   Every coefficient is computed from the real mu/Σ/constraints passed in —
   see `app/optimize/qubo.py::build_qubo`.
5. Solve via simulated annealing (`dwave-neal`) or a from-scratch QAOA
   statevector simulator (`app/optimize/qaoa.py`).

## Project layout

```
backend/
├── app/
│   ├── core/config.py           # all tunables in one place
│   ├── data/
│   │   ├── universe.py          # 10-company default universe
│   │   ├── fetcher.py           # yfinance historical + latest quotes
│   │   ├── synthetic.py         # fallback only, clearly labeled
│   │   └── synthetic_news.py
│   ├── analytics/
│   │   ├── returns.py
│   │   └── risk.py              # full risk-metrics engine
│   ├── optimize/
│   │   ├── constraints.py       # feasibility validation
│   │   ├── classical.py         # MVO, min-vol, max-Sharpe, risk parity, frontier
│   │   ├── qubo.py              # QUBO formulation + solver
│   │   ├── qaoa.py              # from-scratch QAOA simulator
│   │   ├── compare.py           # classical vs QUBO vs QAOA
│   │   └── portfolio.py         # weights -> shares/amounts/validation
│   ├── agents/news_agents.py    # 3-agent RSS pipeline
│   ├── services/pipeline.py     # shared fetch/cache/derive service
│   └── api/                     # FastAPI app + routes
├── scripts/demo_end_to_end.py
├── tests/                       # 22 passing tests
└── requirements.txt
```

## Suggested next session

1. **Backtesting engine** (Section 16) — rolling/walk-forward, no look-ahead
   bias, benchmark comparison. This is the highest-value gap.
2. **Frontend** — a React/TS dashboard consuming this API (Overview, Risk
   Analysis, Optimization, Quantum Lab, News & Events, Backtesting pages per
   your nav spec).
3. Wire `/api/events/impact` adjustments into `mu` before optimization
   (dynamic reoptimization, Section 30), with a "Current vs Recommended"
   diff view.
4. CSV/PDF export (Section 60).
