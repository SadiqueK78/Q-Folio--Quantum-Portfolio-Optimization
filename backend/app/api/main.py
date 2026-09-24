from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.core.config import get_settings
from app.api.routes import market, risk, optimize, frontier, news, backtest

settings = get_settings()

app = FastAPI(
    title="Classical + Quantum Portfolio Optimization Platform",
    description=(
        "Research/decision-support platform. NOT financial advice. "
        "Free/open data sources only (Yahoo Finance). Quantum layer is a "
        "QUBO formulation solved via simulated annealing and a from-scratch "
        "QAOA statevector simulator — no quantum advantage is claimed."
    ),
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.allowed_origins.split(","),
    allow_credentials=False,
    allow_methods=["GET", "POST"],
    allow_headers=["*"],
)

app.include_router(market.router, prefix="/api")
app.include_router(risk.router, prefix="/api")
app.include_router(optimize.router, prefix="/api")
app.include_router(frontier.router, prefix="/api")
app.include_router(news.router, prefix="/api")
app.include_router(backtest.router, prefix="/api")


@app.get("/")
def root():
    return {"name": app.title, "version": app.version, "docs": "/docs"}
