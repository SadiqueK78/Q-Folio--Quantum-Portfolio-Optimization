// Typed client for the FastAPI backend. Base URL is configurable via
// VITE_API_BASE_URL (see .env.example); defaults to localhost:8000.

const BASE_URL = import.meta.env.VITE_API_BASE_URL || "http://localhost:8000";

export class ApiError extends Error {
  status: number;
  detail: unknown;
  constructor(status: number, detail: unknown) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

async function request<T>(path: string, options?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE_URL}${path}`, {
    ...options,
    headers: { "Content-Type": "application/json", ...(options?.headers || {}) },
  });
  if (!res.ok) {
    let detail: unknown = res.statusText;
    try {
      const body = await res.json();
      detail = body.detail ?? body;
    } catch {
      /* ignore parse failure */
    }
    throw new ApiError(res.status, detail);
  }
  return res.json() as Promise<T>;
}

export const api = {
  get: <T,>(path: string) => request<T>(path),
  post: <T,>(path: string, body: unknown) =>
    request<T>(path, { method: "POST", body: JSON.stringify(body) }),
};

// ---------- Types ----------

export interface Asset {
  symbol: string;
  name: string;
  sector: string;
  industry: string;
  exchange: string;
  currency: string;
  data_source: string;
}

export interface Quote {
  symbol: string;
  price: number | null;
  status: string;
  as_of: string;
  market_state: string;
}

export interface DataStatus {
  market_data_connected: boolean;
  source_label: string;
  quality_report: string;
  warning: string | null;
}

export interface OptimizeParams {
  budget: number;
  min_weight: number;
  max_weight: number;
  min_holdings: number | null;
  max_holdings: number | null;
  transaction_cost_pct: number;
  sector_bounds: { sector: string; min_pct: number; max_pct: number }[];
  frequency: "daily" | "weekly" | "monthly";
  risk_free_rate: number;
  strategy?: "equal_weight" | "min_volatility" | "max_sharpe" | "risk_parity";
  whole_shares: boolean;
}

export interface Holding {
  symbol: string;
  sector: string;
  weight_pct: number;
  amount: number;
  price: number | null;
  shares: number;
}

export interface OptimizeResult {
  method: string;
  statistics: { return: number; risk: number; variance: number; sharpe: number };
  weights: Record<string, number>;
  holdings: Holding[];
  budget: number;
  total_invested: number;
  remaining_cash: number;
  transaction_cost: number;
  utilization_pct: number;
  validation: Record<string, boolean>;
  data_source: string;
  qubo?: { n_binary_variables: number; n_levels_per_asset: number; penalty_terms: Record<string, number>; matrix_preview: number[][] };
  qaoa?: { n_qubits: number; p_layers: number; note: string };
}

export interface FeasibilityResult {
  feasible: boolean;
  reasons: string[];
  suggestions: string[];
}

export interface ComparisonRow {
  strategy: string;
  return_pct?: number;
  risk_pct?: number;
  sharpe?: number;
  runtime_sec?: number;
  n_holdings?: number;
  error?: string;
}

export interface RiskReport {
  expected_return_annualized: Record<string, number>;
  volatility_annualized: Record<string, number>;
  covariance_annualized: Record<string, Record<string, number>>;
  correlation: Record<string, Record<string, number>>;
  portfolio?: {
    expected_return: number;
    volatility: number;
    sharpe: number;
    sortino: number;
    max_drawdown: number;
    var_95: number;
    cvar_95: number;
    risk_contribution: Record<string, number>;
    diversification_score: number;
  };
  data_source: string;
}

export interface FrontierPoint { return: number; risk: number }
export interface FrontierResponse {
  data_source: string;
  frontier: FrontierPoint[];
  min_volatility_point: FrontierPoint;
  max_sharpe_point: FrontierPoint;
}

export interface NewsEntry {
  headline: string; source: string; url: string; published_at: string;
  event_type: string; company: string | null; sector: string | null;
}
export interface EventEntry extends NewsEntry {
  sentiment: number; severity: number; confidence: number; agent: string;
}

export interface BacktestParams {
  strategy: string; frequency: "daily" | "weekly" | "monthly" | "quarterly";
  window_type: "rolling" | "expanding"; lookback_days: number;
  initial_capital: number; max_weight: number; min_holdings: number | null;
  max_holdings: number | null; transaction_cost_pct: number; risk_free_rate: number;
}
export interface BacktestResult {
  data_source: string;
  metrics: Record<string, number>;
  benchmark_metrics: { equal_weight: Record<string, number>; buy_and_hold: Record<string, number> };
  equity_curve: Record<string, number>;
  benchmark_equal_weight: Record<string, number>;
  benchmark_buy_hold: Record<string, number>;
  drawdown: Record<string, number>;
  rebalance_events: { date: string; weights: Record<string, number>; turnover_pct: number; transaction_cost: number }[];
  warnings: string[];
}

export type PriceRange = "1m" | "3m" | "6m" | "1y" | "2y" | "5y" | "10y" | "max";

export interface PriceSeriesResponse {
  symbol: string;
  range: PriceRange;
  data_source: string;
  series: Record<string, number>;
}

export interface AllPricesResponse {
  range: PriceRange;
  data_source: string;
  symbols: string[];
  series: Record<string, Record<string, number | null>>;
}

export interface ReoptimizeDiffRow {
  symbol: string;
  sector: string | null;
  current_pct: number;
  recommended_pct: number;
  change_pct: number;
  news_adjustment: number;
  reason: string;
}

export interface ReoptimizeResult {
  data_source: string;
  current: { label: string; weights: Record<string, number>; statistics: Record<string, number> };
  recommended: { label: string; weights: Record<string, number>; statistics: Record<string, number> };
  news_adjustments: Record<string, number>;
  diff: ReoptimizeDiffRow[];
  note: string;
}

// ---------- Calls ----------

export const endpoints = {
  assets: () => api.get<Asset[]>("/api/assets"),
  marketData: () => api.get<Quote[]>("/api/market-data"),
  dataStatus: () => api.get<DataStatus>("/api/data-status"),
  risk: (frequency: string) => api.get<RiskReport>(`/api/risk?frequency=${frequency}`),
  correlation: (frequency: string) =>
    api.get<{ data_source: string; correlation: Record<string, Record<string, number>> }>(
      `/api/correlation?frequency=${frequency}`
    ),
  frontier: (maxWeight: number) => api.get<FrontierResponse>(`/api/efficient-frontier?max_weight=${maxWeight}`),
  feasibility: (params: OptimizeParams) => api.post<FeasibilityResult>("/api/optimize/feasibility", params),
  optimizeClassical: (params: OptimizeParams) => api.post<OptimizeResult>("/api/optimize/classical", params),
  optimizeQubo: (params: OptimizeParams & { risk_aversion: number; penalty_budget: number; penalty_holdings: number; penalty_sector: number; weight_step: number; num_reads: number; solver: string }) =>
    api.post<OptimizeResult>("/api/optimize/qubo", params),
  optimizeQaoa: (params: OptimizeParams & { risk_aversion: number; penalty_budget: number; penalty_holdings: number; penalty_sector: number; weight_step: number; num_reads: number; solver: string }) =>
    api.post<OptimizeResult>("/api/optimize/qaoa", params),
  compare: (params: OptimizeParams & { risk_aversion: number; penalty_budget: number; penalty_holdings: number; penalty_sector: number; weight_step: number; num_reads: number; solver: string; include_qaoa: boolean; qaoa_p_layers: number }) =>
    api.post<{ data_source: string; comparison_table: ComparisonRow[] }>("/api/optimize/compare", params),
  news: () => api.get<{ data_source: string; sources_configured: number; sources_active: number; entries: NewsEntry[] }>("/api/news"),
  events: () => api.get<EventEntry[]>("/api/events"),
  eventsImpact: () => api.get<{ data_source: string; adjustments: Record<string, number>; note: string }>("/api/events/impact"),
  backtest: (params: BacktestParams) => api.post<BacktestResult>("/api/backtest", params),
  priceSeries: (symbol: string, range: PriceRange) => api.get<PriceSeriesResponse>(`/api/prices/${symbol}?range=${range}`),
  allPrices: (range: PriceRange) => api.get<AllPricesResponse>(`/api/prices?range=${range}`),
  reoptimize: (params: OptimizeParams & { current_weights?: Record<string, number> | null; apply_news_adjustment: boolean }) =>
    api.post<ReoptimizeResult>("/api/portfolio/reoptimize", params),
};
