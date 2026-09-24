import { useState } from "react";
import { Card } from "../components/Card";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { endpoints, type OptimizeResult, ApiError } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { formatCurrency, formatPct } from "../lib/format";

const STRATEGIES = [
  { id: "equal_weight", label: "Equal Weight" },
  { id: "min_volatility", label: "Minimum Volatility" },
  { id: "max_sharpe", label: "Maximum Sharpe" },
  { id: "risk_parity", label: "Risk Parity" },
] as const;

export function Optimization() {
  const { settings, setSettings, toOptimizeParams } = useSettings();
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function runOptimization() {
    setLoading(true);
    setError(null);
    try {
      const r = await endpoints.optimizeClassical({ ...toOptimizeParams(), strategy: settings.strategy });
      setResult(r);
    } catch (e) {
      setError(e instanceof ApiError ? formatDetail(e.detail) : String(e));
    } finally {
      setLoading(false);
    }
  }

  function formatDetail(detail: unknown): string {
    if (typeof detail === "string") return detail;
    if (detail && typeof detail === "object" && "reasons" in (detail as any)) {
      const d = detail as { error: string; reasons: string[]; suggestions: string[] };
      return `${d.error}\n\n${d.reasons.map((r) => `\u2717 ${r}`).join("\n")}\n\nSuggestions:\n${d.suggestions.map((s) => `\u2192 ${s}`).join("\n")}`;
    }
    return JSON.stringify(detail);
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-ink">Optimization Workspace</h1>
        <p className="text-sm text-ink-muted mt-1">Configure constraints, choose a strategy, and run classical optimization.</p>
      </div>

      <Card title="Configuration">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Field label="Budget (\u20b9)">
            <input
              type="number"
              value={settings.budget}
              onChange={(e) => setSettings({ ...settings, budget: Number(e.target.value) })}
              className="input"
            />
          </Field>
          <Field label="Strategy">
            <select
              value={settings.strategy}
              onChange={(e) => setSettings({ ...settings, strategy: e.target.value as any })}
              className="input"
            >
              {STRATEGIES.map((s) => (
                <option key={s.id} value={s.id}>{s.label}</option>
              ))}
            </select>
          </Field>
          <Field label="Frequency">
            <select
              value={settings.frequency}
              onChange={(e) => setSettings({ ...settings, frequency: e.target.value as any })}
              className="input"
            >
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </Field>
          <Field label="Max Allocation / Asset">
            <input
              type="number" step="0.01"
              value={settings.maxWeight}
              onChange={(e) => setSettings({ ...settings, maxWeight: Number(e.target.value) })}
              className="input"
            />
          </Field>
          <Field label="Min Holdings">
            <input
              type="number"
              value={settings.minHoldings}
              onChange={(e) => setSettings({ ...settings, minHoldings: Number(e.target.value) })}
              className="input"
            />
          </Field>
          <Field label="Max Holdings">
            <input
              type="number"
              value={settings.maxHoldings}
              onChange={(e) => setSettings({ ...settings, maxHoldings: Number(e.target.value) })}
              className="input"
            />
          </Field>
          <Field label="Risk-Free Rate">
            <input
              type="number" step="0.01"
              value={settings.riskFreeRate}
              onChange={(e) => setSettings({ ...settings, riskFreeRate: Number(e.target.value) })}
              className="input"
            />
          </Field>
          <Field label="Transaction Cost %">
            <input
              type="number" step="0.0001"
              value={settings.transactionCostPct}
              onChange={(e) => setSettings({ ...settings, transactionCostPct: Number(e.target.value) })}
              className="input"
            />
          </Field>
        </div>
        <button
          onClick={runOptimization}
          disabled={loading}
          className="mt-5 px-4 py-2 bg-amber text-canvas font-display text-sm font-medium rounded hover:bg-amber/90 transition-colors disabled:opacity-50"
        >
          {loading ? "Optimizing\u2026" : "Optimize Portfolio"}
        </button>
      </Card>

      {loading && <LoadingState label="Solving constrained optimization\u2026" />}
      {error && <ErrorState message={error} onRetry={runOptimization} />}
      {!loading && !error && !result && (
        <EmptyState title="No optimization has been run yet" description="Configure your portfolio above and click Optimize Portfolio." />
      )}

      {result && !loading && (
        <>
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
            <MetricPill label="Expected Return" value={formatPct(result.statistics.return * 100)} />
            <MetricPill label="Volatility" value={formatPct(result.statistics.risk * 100)} />
            <MetricPill label="Sharpe Ratio" value={result.statistics.sharpe.toFixed(3)} />
            <MetricPill label="Utilization" value={formatPct(result.utilization_pct)} />
          </div>

          <Card title="Recommended Allocation">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-muted text-xs uppercase tracking-wider border-b border-hairline">
                  <th className="pb-2 font-normal">Symbol</th>
                  <th className="pb-2 font-normal">Sector</th>
                  <th className="pb-2 font-normal text-right">Weight</th>
                  <th className="pb-2 font-normal text-right">Amount</th>
                  <th className="pb-2 font-normal text-right">Shares</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {[...result.holdings].sort((a, b) => b.weight_pct - a.weight_pct).map((h) => (
                  <tr key={h.symbol} className="border-b border-hairline/50">
                    <td className="py-2 text-ink">{h.symbol}</td>
                    <td className="py-2 text-ink-muted font-body">{h.sector}</td>
                    <td className="py-2 text-right text-amber">{h.weight_pct.toFixed(2)}%</td>
                    <td className="py-2 text-right">{formatCurrency(h.amount)}</td>
                    <td className="py-2 text-right">{h.shares}</td>
                  </tr>
                ))}
              </tbody>
            </table>
            <div className="flex flex-wrap gap-4 mt-4 pt-4 border-t border-hairline text-xs">
              {Object.entries(result.validation).map(([k, v]) => (
                <div key={k} className={`flex items-center gap-1.5 ${v ? "text-signal-pos" : "text-signal-neg"}`}>
                  <span>{v ? "\u2713" : "\u2717"}</span>
                  <span className="text-ink-muted">{k.replace(/_/g, " ")}</span>
                </div>
              ))}
            </div>
          </Card>
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

function MetricPill({ label, value }: { label: string; value: string }) {
  return (
    <div className="bg-surface-raised border border-hairline rounded-lg px-4 py-3">
      <div className="text-[10px] text-ink-muted uppercase tracking-wider">{label}</div>
      <div className="font-mono text-lg text-ink mt-0.5">{value}</div>
    </div>
  );
}
