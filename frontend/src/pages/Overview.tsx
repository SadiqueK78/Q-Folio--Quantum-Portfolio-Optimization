import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { StatCard } from "../components/StatCard";
import { LoadingState, ErrorState } from "../components/States";
import { endpoints, type Asset, type OptimizeResult, type RiskReport, ApiError } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { formatCurrency, formatPct } from "../lib/format";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip, BarChart, Bar, XAxis, YAxis, CartesianGrid } from "recharts";

const SECTOR_COLORS = ["#e3a857", "#8b7fe8", "#4abf8a", "#e1665b", "#5b8dee", "#c98bd9", "#e0c05a", "#7fb0e8", "#e88b7f", "#8ae8d4"];

export function Overview() {
  const { toOptimizeParams } = useSettings();
  const [assets, setAssets] = useState<Asset[] | null>(null);
  const [result, setResult] = useState<OptimizeResult | null>(null);
  const [risk, setRisk] = useState<RiskReport | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    setLoading(true);
    setError(null);
    Promise.all([
      endpoints.assets(),
      endpoints.optimizeClassical(toOptimizeParams()),
      endpoints.risk("monthly"),
    ])
      .then(([a, r, risk]) => {
        setAssets(a);
        setResult(r);
        setRisk(risk);
      })
      .catch((e) => setError(e instanceof ApiError ? JSON.stringify(e.detail) : String(e)))
      .finally(() => setLoading(false));
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  if (loading) return <LoadingState label="Running default optimization\u2026" />;
  if (error) return <ErrorState message={error} />;
  if (!result || !assets) return null;

  const sectorTotals: Record<string, number> = {};
  result.holdings.forEach((h) => {
    sectorTotals[h.sector] = (sectorTotals[h.sector] || 0) + h.weight_pct;
  });
  const sectorData = Object.entries(sectorTotals).map(([sector, value]) => ({ sector, value }));
  const holdingsData = [...result.holdings].sort((a, b) => b.weight_pct - a.weight_pct);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-ink">Portfolio Overview</h1>
        <p className="text-sm text-ink-muted mt-1">
          Default strategy: <span className="text-amber">{result.method}</span> &middot; Budget {formatCurrency(result.budget)}
        </p>
      </div>

      <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
        <StatCard label="Total Invested" value={formatCurrency(result.total_invested)} hint={`${formatPct(result.utilization_pct)} utilized`} />
        <StatCard label="Expected Annual Return" value={formatPct(result.statistics.return * 100)} />
        <StatCard label="Portfolio Risk" value={formatPct(result.statistics.risk * 100)} />
        <StatCard label="Sharpe Ratio" value={result.statistics.sharpe.toFixed(3)} />
      </div>

      {risk?.portfolio && (
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <StatCard label="Sortino" value={risk.portfolio.sortino.toFixed(3)} />
          <StatCard label="Max Drawdown" value={formatPct(risk.portfolio.max_drawdown * 100)} />
          <StatCard label="CVaR (95%)" value={formatPct(risk.portfolio.cvar_95 * 100)} />
          <StatCard label="Diversification Score" value={risk.portfolio.diversification_score.toFixed(2)} />
        </div>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
        <Card title="Sector Allocation" className="lg:col-span-1">
          <ResponsiveContainer width="100%" height={220}>
            <PieChart>
              <Pie data={sectorData} dataKey="value" nameKey="sector" innerRadius={50} outerRadius={85} paddingAngle={2}>
                {sectorData.map((_, i) => (
                  <Cell key={i} fill={SECTOR_COLORS[i % SECTOR_COLORS.length]} stroke="#0a0c10" />
                ))}
              </Pie>
              <Tooltip
                contentStyle={{ background: "#171b24", border: "1px solid #232838", borderRadius: 6, fontSize: 12 }}
                formatter={(v) => `${Number(v).toFixed(1)}%`}
              />
            </PieChart>
          </ResponsiveContainer>
          <div className="flex flex-wrap gap-x-3 gap-y-1 mt-2 justify-center">
            {sectorData.map((s, i) => (
              <div key={s.sector} className="flex items-center gap-1.5 text-[10px] text-ink-muted">
                <span className="w-2 h-2 rounded-full" style={{ background: SECTOR_COLORS[i % SECTOR_COLORS.length] }} />
                {s.sector}
              </div>
            ))}
          </div>
        </Card>

        <Card title="Holdings by Weight" className="lg:col-span-2">
          <ResponsiveContainer width="100%" height={260}>
            <BarChart data={holdingsData} layout="vertical" margin={{ left: 20 }}>
              <CartesianGrid strokeDasharray="3 3" stroke="#232838" horizontal={false} />
              <XAxis type="number" tick={{ fill: "#8992a6", fontSize: 11 }} unit="%" />
              <YAxis
                type="category"
                dataKey="symbol"
                tick={{ fill: "#8992a6", fontSize: 11 }}
                width={90}
                tickFormatter={(v: string) => v.replace(".NS", "")}
              />
              <Tooltip
                contentStyle={{ background: "#171b24", border: "1px solid #232838", borderRadius: 6, fontSize: 12 }}
                formatter={(v) => `${Number(v).toFixed(2)}%`}
              />
              <Bar dataKey="weight_pct" fill="#e3a857" radius={[0, 3, 3, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </Card>
      </div>

      <Card title="Holdings Detail">
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-ink-muted text-xs uppercase tracking-wider border-b border-hairline">
                <th className="pb-2 font-normal">Symbol</th>
                <th className="pb-2 font-normal">Sector</th>
                <th className="pb-2 font-normal text-right">Weight</th>
                <th className="pb-2 font-normal text-right">Amount</th>
                <th className="pb-2 font-normal text-right">Price</th>
                <th className="pb-2 font-normal text-right">Shares</th>
              </tr>
            </thead>
            <tbody className="font-mono">
              {holdingsData.map((h) => (
                <tr key={h.symbol} className="border-b border-hairline/50">
                  <td className="py-2 text-ink">{h.symbol}</td>
                  <td className="py-2 text-ink-muted font-body">{h.sector}</td>
                  <td className="py-2 text-right text-amber">{h.weight_pct.toFixed(2)}%</td>
                  <td className="py-2 text-right">{formatCurrency(h.amount)}</td>
                  <td className="py-2 text-right">{h.price ? formatCurrency(h.price) : "\u2014"}</td>
                  <td className="py-2 text-right">{h.shares}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <div className="flex gap-6 mt-4 pt-4 border-t border-hairline text-xs">
          <div><span className="text-ink-muted">Remaining Cash: </span><span className="text-ink font-mono">{formatCurrency(result.remaining_cash)}</span></div>
          <div><span className="text-ink-muted">Transaction Cost: </span><span className="text-ink font-mono">{formatCurrency(result.transaction_cost)}</span></div>
          <div>
            <span className="text-ink-muted">Validation: </span>
            {Object.values(result.validation).every(Boolean) ? (
              <span className="text-signal-pos">All checks passed</span>
            ) : (
              <span className="text-signal-neg">Constraint violation detected</span>
            )}
          </div>
        </div>
      </Card>
    </div>
  );
}
