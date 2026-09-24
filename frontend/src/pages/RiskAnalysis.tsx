import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { StatCard } from "../components/StatCard";
import { Heatmap } from "../components/Heatmap";
import { LoadingState, ErrorState } from "../components/States";
import { endpoints, type RiskReport, ApiError } from "../lib/api";
import { formatPct } from "../lib/format";

export function RiskAnalysis() {
  const [frequency, setFrequency] = useState<"daily" | "weekly" | "monthly">("monthly");
  const [report, setReport] = useState<RiskReport | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    endpoints
      .risk(frequency)
      .then(setReport)
      .catch((e) => setError(e instanceof ApiError ? String(e.message) : String(e)))
      .finally(() => setLoading(false));
  }, [frequency]);

  const symbols = report ? Object.keys(report.expected_return_annualized) : [];
  const corrMatrix = report ? symbols.map((s) => symbols.map((t) => report.correlation[s]?.[t] ?? 0)) : [];

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl text-ink">Risk Analysis</h1>
          <p className="text-sm text-ink-muted mt-1">Equal-weight reference portfolio. Volatility, correlation, VaR/CVaR, drawdown.</p>
        </div>
        <select value={frequency} onChange={(e) => setFrequency(e.target.value as any)} className="input w-40">
          <option value="daily">Daily</option>
          <option value="weekly">Weekly</option>
          <option value="monthly">Monthly</option>
        </select>
      </div>

      {loading && <LoadingState label="Computing risk metrics\u2026" />}
      {error && <ErrorState message={error} />}

      {report && !loading && (
        <>
          {report.portfolio && (
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
              <StatCard label="Portfolio Return" value={formatPct(report.portfolio.expected_return * 100)} />
              <StatCard label="Volatility" value={formatPct(report.portfolio.volatility * 100)} />
              <StatCard label="Sharpe" value={report.portfolio.sharpe.toFixed(3)} />
              <StatCard label="Sortino" value={report.portfolio.sortino.toFixed(3)} />
              <StatCard label="Max Drawdown" value={formatPct(report.portfolio.max_drawdown * 100)} />
              <StatCard label="VaR (95%)" value={formatPct(report.portfolio.var_95 * 100)} />
              <StatCard label="CVaR (95%)" value={formatPct(report.portfolio.cvar_95 * 100)} />
              <StatCard label="Diversification" value={report.portfolio.diversification_score.toFixed(2)} />
            </div>
          )}

          <Card title="Per-Asset Return & Volatility (Annualized)">
            <table className="w-full text-sm">
              <thead>
                <tr className="text-left text-ink-muted text-xs uppercase tracking-wider border-b border-hairline">
                  <th className="pb-2 font-normal">Symbol</th>
                  <th className="pb-2 font-normal text-right">Expected Return</th>
                  <th className="pb-2 font-normal text-right">Volatility</th>
                  <th className="pb-2 font-normal text-right">Risk Contribution</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {symbols.map((s) => (
                  <tr key={s} className="border-b border-hairline/50">
                    <td className="py-2 text-ink">{s}</td>
                    <td className="py-2 text-right text-signal-pos">{formatPct(report.expected_return_annualized[s] * 100)}</td>
                    <td className="py-2 text-right text-amber">{formatPct(report.volatility_annualized[s] * 100)}</td>
                    <td className="py-2 text-right text-ink-muted">
                      {report.portfolio ? formatPct((report.portfolio.risk_contribution[s] ?? 0) * 100) : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </Card>

          <Card title="Correlation Matrix" subtitle="Amber = positive correlation, violet = negative correlation">
            <Heatmap labels={symbols} matrix={corrMatrix} colorMode="diverging" />
          </Card>
        </>
      )}
    </div>
  );
}
