# Portfolio Optimization Platform — Frontend

A React + TypeScript + Tailwind dashboard for the classical + quantum
portfolio optimization backend. Dark quant-terminal aesthetic: amber for
classical/market data, violet for the quantum/QUBO layer, a persistent
data-provenance pill (live / cached / synthetic) so you're never looking at
a number without knowing where it came from.

## Pages

- **Overview** — default optimization run, sector allocation, holdings table
- **Optimization** — configurable strategy/constraints workspace
- **Risk Analysis** — full risk-metrics report + correlation heatmap
- **Efficient Frontier** — risk/return scatter with min-vol / max-Sharpe points
- **Quantum Lab** — QUBO pipeline diagram, penalty-coefficient controls,
  classical vs QUBO vs QAOA comparison, QUBO matrix heatmap
- **Backtesting** — walk-forward simulation, equity curve vs benchmarks,
  drawdown chart, benchmark comparison table
- **News & Events** — 3-agent event timeline + bounded impact scores
- **Settings** — global budget/constraint/quantum defaults shared across pages

## Running it

```bash
npm install
cp .env.example .env
# Make sure the backend is running first: uvicorn app.api.main:app --reload
npm run dev
```

Open the printed local URL (usually http://localhost:5173).

`VITE_API_BASE_URL` in `.env` controls which backend the app talks to
(defaults to http://localhost:8000).

## Build

```bash
npm run build   # type-checks (tsc -b) then builds to dist/
npm run preview # serve the production build locally
```

## What's implemented vs. what's a next step

Implemented and wired to real backend endpoints: everything listed in the
page list above, all backed by live network calls (no mock data in the
frontend — every number comes from /api/*).

Not yet built: CSV/PDF export buttons (Section 60), a dynamic-reoptimization
trigger UI ("Current vs Recommended" diff after a high-impact event), and
per-sector constraint editing in the UI (the backend supports
sector_bounds in every optimize request; the Settings page doesn't yet
expose an editor for it — currently defaults to no sector bounds).

## Stack

React 19, TypeScript, Vite, Tailwind CSS v4, Recharts, React Router.
