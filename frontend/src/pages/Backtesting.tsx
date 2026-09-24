import { useState } from "react";
import { Card } from "../components/Card";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { endpoints, type BacktestResult, ApiError } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { formatPct } from "../lib/format";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend, AreaChart, Area } from "recharts";

export function Backtesting() {
  const { settings, setSettings } = useSettings();
  const [windowType, setWindowType] = useState<"rolling" | "expanding">("rolling");
  const [lookback, setLookback] = useState(504);
  const [result, setResult] = useState<BacktestResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    try {
      const r = await endpoints.backtest({
        strategy: settings.strategy, frequency: settings.frequency, window_type: windowType,
        lookback_days: lookback, initial_capital: settings.budget, max_weight: settings.maxWeight,
        min_holdings: settings.minHoldings, max_holdings: settings.maxHoldings,
        transaction_cost_pct: settings.transactionCostPct, risk_free_rate: settings.riskFreeRate,
      });
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiError ? JSON.stringify(e.detail) : String(e));
    } finally {
      setLoading(false);
    }
  }

  const equityData = result
    ? Object.keys(result.equity_curve).map((date) => ({
        date,
        strategy: result.equity_curve[date],
        equal_weight: result.benchmark_equal_weight[date],
        buy_hold: result.benchmark_buy_hold[date],
      }))
    : [];

  const drawdownData = result
    ? Object.entries(result.drawdown).map(([date, v]) => ({ date, drawdown: v }))
    : [];

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-ink">Backtesting</h1>
        <p className="text-sm text-ink-muted mt-1">
          Walk-forward simulation \u2014 the optimizer only ever sees returns strictly before each rebalance date.
        </p>
      </div>

      <Card title="Configuration">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Field label="Strategy">
            <select value={settings.strategy} onChange={(e) => setSettings({ ...settings, strategy: e.target.value as any })} className="input">
              <option value="equal_weight">Equal Weight</option>
              <option value="min_volatility">Minimum Volatility</option>
              <option value="max_sharpe">Maximum Sharpe</option>
              <option value="risk_parity">Risk Parity</option>
            </select>
          </Field>
          <Field label="Rebalancing Frequency">
            <select value={settings.frequency} onChange={(e) => setSettings({ ...settings, frequency: e.target.value as any })} className="input">
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </Field>
          <Field label="Window Type">
            <select value={windowType} onChange={(e) => setWindowType(e.target.value as any)} className="input">
              <option value="rolling">Rolling</option>
              <option value="expanding">Expanding</option>
            </select>
          </Field>
          <Field label="Lookback (trading days)">
            <input type="number" value={lookback} onChange={(e) => setLookback(Number(e.target.value))} className="input" />
          </Field>
          <Field label="Initial Capital (\u20b9)">
            <input type="number" value={settings.budget} onChange={(e) => setSettings({ ...settings, budget: Number(e.target.value) })} className="input" />
          </Field>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="mt-5 px-4 py-2 bg-amber text-canvas font-display text-sm font-medium rounded hover:bg-amber/90 transition-colors disabled:opacity-50"
        >
          {loading ? "Running backtest\u2026" : "Run Backtest"}
        </button>
      </Card>

      {loading && <LoadingState label="Walking forward through history\u2026" />}
      {error && <ErrorState message={error} onRetry={run} />}
      {!loading && !error && !result && (
        <EmptyState title="No backtest has been run yet" description="Configure the settings above and click Run Backtest." />
      )}

      {result && !loading && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <Metric label="Total Return" value={formatPct(result.metrics.total_return_pct)} />
            <Metric label="CAGR" value={formatPct(result.metrics.cagr_pct)} />
            <Metric label="Sharpe" value={result.metrics.sharpe?.toFixed(3) ?? "\u2014"} />
            <Metric label="Max Drawdown" value={formatPct(result.metrics.max_drawdown_pct)} />
            <Metric label="Sortino" value={result.metrics.sortino?.toFixed(3) ?? "\u2014"} />
            <Metric label="Calmar Ratio" value={result.metrics.calmar_ratio?.toFixed(3) ?? "\u2014"} />
            <Metric label="Turnover (avg)" value={formatPct(result.metrics.average_turnover_pct)} />
            <Metric label="Transaction Cost" value={`\u20b9${result.metrics.total_transaction_cost?.toLocaleString()}`} />
          </div>

          <Card title="Equity Curve vs Benchmarks">
            <ResponsiveContainer width="100%" height={320}>
              <LineChart data={equityData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232838" />
                <XAxis dataKey="date" tick={{ fill: "#8992a6", fontSize: 10 }} minTickGap={60} />
                <YAxis tick={{ fill: "#8992a6", fontSize: 11 }} tickFormatter={(v) => `${(v / 1000).toFixed(0)}k`} />
                <Tooltip contentStyle={{ background: "#171b24", border: "1px solid #232838", borderRadius: 6, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Line type="monotone" dataKey="strategy" name={settings.strategy} stroke="#e3a857" dot={false} strokeWidth={2} />
                <Line type="monotone" dataKey="equal_weight" name="Equal Weight" stroke="#4abf8a" dot={false} strokeWidth={1.5} strokeDasharray="4 3" />
                <Line type="monotone" dataKey="buy_hold" name="Buy & Hold" stroke="#8992a6" dot={false} strokeWidth={1.5} strokeDasharray="2 2" />
              </LineChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Drawdown">
            <ResponsiveContainer width="100%" height={180}>
              <AreaChart data={drawdownData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232838" />
                <XAxis dataKey="date" tick={{ fill: "#8992a6", fontSize: 10 }} minTickGap={60} />
                <YAxis tick={{ fill: "#8992a6", fontSize: 11 }} tickFormatter={(v) => `${v.toFixed(0)}%`} />
                <Tooltip contentStyle={{ background: "#171b24", border: "1px solid #232838", borderRadius: 6, fontSize: 12 }} formatter={(v) => `${Number(v).toFixed(2)}%`} />
                <Area type="monotone" dataKey="drawdown" stroke="#e1665b" fill="#e1665b" fillOpacity={0.15} />
              </AreaChart>
            </ResponsiveContainer>
          </Card>

          <Card title="Benchmark Comparison">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-muted text-xs uppercase tracking-wider border-b border-hairline">
                  <th className="pb-2 font-normal">Strategy</th>
                  <th className="pb-2 font-normal text-right">CAGR</th>
                  <th className="pb-2 font-normal text-right">Volatility</th>
                  <th className="pb-2 font-normal text-right">Sharpe</th>
                  <th className="pb-2 font-normal text-right">Max Drawdown</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                <tr className="border-b border-hairline/50">
                  <td className="py-2 text-amber">{settings.strategy}</td>
                  <td className="py-2 text-right">{formatPct(result.metrics.cagr_pct)}</td>
                  <td className="py-2 text-right">{formatPct(result.metrics.volatility_pct)}</td>
                  <td className="py-2 text-right">{result.metrics.sharpe?.toFixed(3)}</td>
                  <td className="py-2 text-right">{formatPct(result.metrics.max_drawdown_pct)}</td>
                </tr>
                <tr className="border-b border-hairline/50">
                  <td className="py-2 text-signal-pos">Equal Weight</td>
                  <td className="py-2 text-right">{formatPct(result.benchmark_metrics.equal_weight.cagr_pct)}</td>
                  <td className="py-2 text-right">{formatPct(result.benchmark_metrics.equal_weight.volatility_pct)}</td>
                  <td className="py-2 text-right">{result.benchmark_metrics.equal_weight.sharpe?.toFixed(3)}</td>
                  <td className="py-2 text-right">{formatPct(result.benchmark_metrics.equal_weight.max_drawdown_pct)}</td>
                </tr>
                <tr>
                  <td className="py-2 text-ink-muted">Buy & Hold</td>
                  <td className="py-2 text-right">{formatPct(result.benchmark_metrics.buy_and_hold.cagr_pct)}</td>
                  <td className="py-2 text-right">{formatPct(result.benchmark_metrics.buy_and_hold.volatility_pct)}</td>
                  <td className="py-2 text-right">{result.benchmark_metrics.buy_and_hold.sharpe?.toFixed(3)}</td>
                  <td className="py-2 text-right">{formatPct(result.benchmark_metrics.buy_and_hold.max_drawdown_pct)}</td>
                </tr>
              </tbody>
            </table>
          </Card>

          {result.warnings.length > 0 && (
            <Card title="Warnings">
              <ul className="text-xs text-amber space-y-1">
                {result.warnings.map((w, i) => <li key={i}>&middot; {w}</li>)}
              </ul>
            </Card>
          )}
        </>
      )}
    </div>
  );
}

function Field({ label, children }: { label: string; children: React.ReactNode }) {
  return (
    <label className="block">
      <div className="text-xs text-ink-muted mb-1.5">{label}</div>
      {children}
    </label>
  );
}

function Metric({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-raised border border-hairline rounded-lg px-4 py-3">
      <div className="text-[10px] text-ink-muted uppercase tracking-wider">{label}</div>
      <div className="font-mono text-lg text-ink mt-0.5">{value}</div>
    </div>
  );
}
