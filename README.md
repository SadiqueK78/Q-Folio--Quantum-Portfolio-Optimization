# Portfolio Optimization Platform

A research and decision-support platform for classical and quantum-inspired portfolio optimization. The project combines a FastAPI/Python backend with a React/TypeScript dashboard for market data, financial analytics, portfolio construction, efficient-frontier analysis, QUBO/QAOA experiments, backtesting, and news-event monitoring.

> **Not financial advice.** This software is for research and decision support. Historical returns are not guaranteed future returns. Always verify data, assumptions, and results before using them for investment decisions.

## Project Status

The current workspace contains a working backend and frontend for the core optimization workflow.

Implemented:

- Market data retrieval through Yahoo Finance, with cleaning, caching, and data-quality reporting
- Explicit data provenance labels: `live`, `cached`, `synthetic`, `latest_available`, `market_closed`, and `unavailable`
- Daily, weekly, and monthly return calculations
- Risk metrics including volatility, covariance, correlation, Sharpe, Sortino, maximum drawdown, historical VaR, CVaR, beta, risk contribution, and diversification score
- Classical portfolio strategies: equal weight, minimum volatility, maximum Sharpe, risk parity, and efficient frontier
- Constraint feasibility validation before optimization
- QUBO construction from expected returns, covariance, weight discretization, budget, holdings, and sector constraints
- Simulated annealing through `dwave-neal`
- A from-scratch QAOA statevector simulator for small QUBO problems
- Classical, QUBO, and QAOA comparison results with runtime and objective information
- Portfolio conversion from weights to amounts, shares, leftover cash, transaction costs, and validation results
- Rule-based Market, Company, and Sector news agents using free RSS feeds
- Walk-forward backtesting and benchmark comparison
- React dashboard pages for overview, optimization, risk, efficient frontier, quantum experiments, backtesting, news, live TV, market data, and settings

Planned or incomplete areas:

- CSV and PDF export
- Automatic reoptimization after a high-impact event, including a Current vs Recommended comparison
- A frontend editor for per-sector bounds; the backend already accepts `sector_bounds`
- Production authentication, persistent user portfolios, and deployment configuration

## Repository Layout

```text
Optimization/
├── backend/
│   ├── app/
│   │   ├── agents/          # News and event agents
│   │   ├── analytics/       # Returns and risk calculations
│   │   ├── api/             # FastAPI application and route modules
│   │   ├── backtest/        # Walk-forward backtesting engine
│   │   ├── core/            # Settings and shared configuration
│   │   ├── data/             # Market data, universe, cache, synthetic fallback
│   │   ├── optimize/         # Classical, QUBO, QAOA, constraints, portfolio logic
│   │   ├── schemas/          # Pydantic request and response models
│   │   └── services/         # Shared data and optimization pipelines
│   ├── data_cache/           # Local generated data cache; ignored by Git
│   ├── scripts/              # End-to-end demo scripts
│   ├── tests/                # Backend unit and integration tests
│   ├── requirements.txt
│   └── README.md             # Backend-specific documentation
├── frontend/
│   ├── src/
│   │   ├── components/       # Shared dashboard components
│   │   ├── context/          # Shared settings state
│   │   ├── lib/              # API, formatting, and media helpers
│   │   └── pages/            # Dashboard screens
│   ├── public/
│   ├── package.json
│   └── README.md             # Frontend-specific documentation
└── README.md
```

## Requirements

Install the following before starting:

- Python 3.10 or newer
- Node.js 18 or newer and npm
- Git
- Internet access for live Yahoo Finance and RSS requests, when live data is desired

The backend has a synthetic fallback for restricted or unavailable data sources. Synthetic results are labeled and should not be mistaken for market data.

## Quick Start

Start the backend and frontend in separate terminals.

### 1. Backend

From the repository root:

```powershell
cd backend
python -m venv venv
.\venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
pip install -r requirements-dev.txt
Copy-Item .env.example .env
uvicorn app.api.main:app --reload
```

The API will be available at `http://localhost:8000`.

Interactive API documentation:

- Swagger UI: `http://localhost:8000/docs`
- ReDoc: `http://localhost:8000/redoc`

If PowerShell blocks script activation, activate the environment through Command Prompt instead:

```bat
venv\Scripts\activate.bat
```

### 2. Frontend

Open a second terminal from the repository root:

```powershell
cd frontend
npm install
Copy-Item .env.example .env
npm run dev
```

The Vite development server normally runs at `http://localhost:5173`. The frontend reads `VITE_API_BASE_URL` from `frontend/.env`; the default backend URL is `http://localhost:8000`.

Example frontend environment file:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

### 3. Open the application

Open `http://localhost:5173` after both processes are running. The dashboard calls the backend API directly, so the backend must be available for market, risk, optimization, and news views to load.

## Backend Commands

Run the complete demo pipeline from `backend/`:

```powershell
python scripts/demo_end_to_end.py
```

Run all backend tests:

```powershell
pytest tests/ -v
```

Run the API without reload mode:

```powershell
uvicorn app.api.main:app --host 0.0.0.0 --port 8000
```

The backend cache is stored under `backend/data_cache/` and is ignored by Git. Delete that directory when you need to force a fresh data request.

## Frontend Commands

Run from `frontend/`:

```powershell
npm run dev       # Start Vite development server
npm run build     # Type-check and create a production build
npm run lint      # Run oxlint
npm run preview   # Preview the production build locally
```

## Main Dashboard Pages

- **Overview**: Run the default optimization and inspect allocation, holdings, and key portfolio statistics.
- **Market Data**: Inspect latest quotes, historical availability, cache state, and data-quality information.
- **Risk Analysis**: Review risk metrics and correlation relationships across the active universe.
- **Optimization**: Choose a classical strategy and configure budget, weight, holdings, frequency, and transaction-cost constraints.
- **Efficient Frontier**: Compare risk-return tradeoffs and identify minimum-volatility and maximum-Sharpe portfolios.
- **Quantum Lab**: Inspect the QUBO formulation, penalty coefficients, QUBO matrix, and classical/QUBO/QAOA comparison.
- **Backtesting**: Run walk-forward simulations and compare portfolio performance with benchmarks.
- **News & Events**: Review RSS-derived events, agent classifications, sentiment, severity, confidence, time decay, and bounded impact scores.
- **Live TV**: View configured market-news video channels when available.
- **Settings**: Maintain shared budget, risk, holdings, and optimization defaults used throughout the dashboard.

## API Surface

The FastAPI service exposes the following main routes:

```text
GET  /api/health
GET  /api/assets
GET  /api/market-data
GET  /api/historical-data
GET  /api/data-status

GET  /api/returns?frequency=daily|weekly|monthly
GET  /api/risk?frequency=...
GET  /api/covariance?frequency=...
GET  /api/correlation?frequency=...
GET  /api/efficient-frontier

POST /api/optimize/feasibility
POST /api/optimize/classical
POST /api/optimize/qubo
POST /api/optimize/qaoa
POST /api/optimize/compare

GET  /api/news
GET  /api/events
GET  /api/events/impact
```

Optimization requests can include:

- `budget`
- `min_weight` and `max_weight`
- `min_holdings` and `max_holdings`
- `transaction_cost_pct`
- `sector_bounds`
- `frequency`
- `risk_free_rate`
- `whole_shares`

The exact request and response contracts are defined in `backend/app/schemas/` and are also available through Swagger UI.

## Data and Provenance

The application is designed to keep the origin and freshness of data visible:

- **Live**: fetched from the configured external source during the request
- **Cached**: loaded from a prior successful fetch in `backend/data_cache/`
- **Synthetic**: generated fallback data used when external access fails
- **Latest available**: the most recent quote returned by the provider, which may not be real-time
- **Market closed**: the provider returned a valid quote outside active trading hours
- **Unavailable**: no usable value was returned

A network restriction or provider failure should not be interpreted as a successful live market-data response. Check the provenance indicator before using any result.

## Optimization Model

The classical objective is based on expected return and portfolio variance:

```text
E[R_p] = w^T mu
variance = w^T Sigma w
Sharpe = (w^T mu - R_f) / sqrt(w^T Sigma w)
```

The QUBO layer discretizes each asset weight into allowed levels and introduces binary variables that select those levels. Penalty terms represent budget, one-hot asset selection, holdings-count, and sector constraints. The QUBO is generated from the actual expected-return vector, covariance matrix, and request constraints; it is not a random demonstration matrix.

QAOA is implemented as a small statevector simulator and is intentionally capped because statevector memory grows exponentially with the number of qubits. Larger problems use the classical or simulated-annealing paths instead of silently pretending to provide a quantum advantage.

## Configuration

Backend configuration is loaded from `backend/.env` using Pydantic Settings. Start with:

```powershell
cd backend
Copy-Item .env.example .env
```

Do not commit secrets or machine-specific values. The backend `.gitignore` excludes `.env`, virtual environments, Python caches, test caches, generated market data, and build artifacts while preserving `.env.example`.

Frontend configuration is loaded from `frontend/.env`:

```dotenv
VITE_API_BASE_URL=http://localhost:8000
```

Only variables prefixed with `VITE_` are exposed to the browser. Never place private credentials in frontend environment variables.

## Testing Strategy

Backend tests cover the calculation and service boundaries that drive the dashboard, including:

- Backtesting behavior
- Constraint feasibility and portfolio construction
- Dynamic reoptimization behavior
- Latest quote handling
- Market and news source fallbacks
- QUBO generation and solving
- Risk metrics

Before opening a pull request, run:

```powershell
cd backend
pytest tests/ -v
cd ..\frontend
npm run build
npm run lint
```

When external data is unavailable, tests should continue to use deterministic synthetic fixtures or explicitly mocked providers. Live provider availability must not be required for the test suite.

## Development Notes

- Keep data provenance visible in new API responses and UI components.
- Preserve the distinction between a delayed/latest provider quote and a real-time quote.
- Validate constraints before invoking an optimizer so users receive an actionable explanation for infeasible requests.
- Keep QUBO and QAOA results honest: report runtime and feasibility, and do not claim quantum advantage without evidence.
- Add tests beside backend behavior changes.
- Keep generated caches, virtual environments, build output, and local secrets out of version control.

## License and Disclaimer

No investment recommendation is made by this project. This repository is a research implementation and does not guarantee data accuracy, availability, performance, or profitability. Review dependencies, provider terms, and applicable regulations before deploying it beyond local experimentation.
