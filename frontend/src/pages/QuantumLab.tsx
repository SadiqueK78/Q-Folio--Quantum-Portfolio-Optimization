import { useState } from "react";
import { Card } from "../components/Card";
import { Heatmap } from "../components/Heatmap";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { endpoints, type ComparisonRow, ApiError } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { formatPct } from "../lib/format";
import { BarChart, Bar, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

export function QuantumLab() {
  const { settings, setSettings, toOptimizeParams } = useSettings();
  const [table, setTable] = useState<ComparisonRow[] | null>(null);
  const [matrix, setMatrix] = useState<number[][] | null>(null);
  const [qubovars, setQubovars] = useState<number | null>(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function run() {
    setLoading(true);
    setError(null);
    setTable(null);
    try {
      const [compareResp, quboResp] = await Promise.all([
        endpoints.compare({
          ...toOptimizeParams(),
          risk_aversion: settings.riskAversion, penalty_budget: settings.penaltyBudget,
          penalty_holdings: settings.penaltyHoldings, penalty_sector: settings.penaltySector,
          weight_step: settings.weightStep, num_reads: settings.numReads, solver: "simulated_annealing",
          include_qaoa: true, qaoa_p_layers: 2,
        }),
        endpoints.optimizeQubo({
          ...toOptimizeParams(),
          risk_aversion: settings.riskAversion, penalty_budget: settings.penaltyBudget,
          penalty_holdings: settings.penaltyHoldings, penalty_sector: settings.penaltySector,
          weight_step: settings.weightStep, num_reads: settings.numReads, solver: "simulated_annealing",
        }),
      ]);
      setTable(compareResp.comparison_table);
      setMatrix(quboResp.qubo?.matrix_preview ?? null);
      setQubovars(quboResp.qubo?.n_binary_variables ?? null);
    } catch (e) {
      setError(e instanceof ApiError ? JSON.stringify(e.detail) : String(e));
    } finally {
      setLoading(false);
    }
  }

  const chartData = (table || [])
    .filter((r) => !r.error)
    .map((r) => ({ strategy: r.strategy, return: r.return_pct, risk: r.risk_pct, sharpe: r.sharpe }));

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-quantum">Quantum Lab</h1>
        <p className="text-sm text-ink-muted mt-1">
          Portfolio optimization as a QUBO: binary weight-discretization &rarr; penalty-encoded constraints &rarr; simulated-annealing / QAOA solver.
        </p>
      </div>

      <Card title="Problem &rarr; QUBO Pipeline">
        <div className="flex flex-wrap gap-2 text-xs font-mono">
          {["Portfolio Problem", "Discretize Weights", "Binary Encoding", "QUBO Matrix Q", "Annealing / QAOA", "Decode Solution"].map((step, i, arr) => (
            <div key={step} className="flex items-center gap-2">
              <span className="px-3 py-1.5 rounded border border-quantum-dim bg-quantum-dim/10 text-quantum">{step}</span>
              {i < arr.length - 1 && <span className="text-ink-faint">&rarr;</span>}
            </div>
          ))}
        </div>
      </Card>

      <Card title="QUBO Configuration">
        <div className="grid grid-cols-2 md:grid-cols-5 gap-4">
          <Field label="Weight Step">
            <input type="number" step="0.01" value={settings.weightStep}
              onChange={(e) => setSettings({ ...settings, weightStep: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Risk Aversion (\u03b2)">
            <input type="number" step="0.5" value={settings.riskAversion}
              onChange={(e) => setSettings({ ...settings, riskAversion: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Budget Penalty (\u03b3)">
            <input type="number" step="0.5" value={settings.penaltyBudget}
              onChange={(e) => setSettings({ ...settings, penaltyBudget: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Holdings Penalty (\u03b5)">
            <input type="number" step="0.5" value={settings.penaltyHoldings}
              onChange={(e) => setSettings({ ...settings, penaltyHoldings: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Simulated Annealing Reads">
            <input type="number" step="50" value={settings.numReads}
              onChange={(e) => setSettings({ ...settings, numReads: Number(e.target.value) })} className="input" />
          </Field>
        </div>
        <button
          onClick={run}
          disabled={loading}
          className="mt-5 px-4 py-2 bg-quantum text-canvas font-display text-sm font-medium rounded hover:bg-quantum/90 transition-colors disabled:opacity-50"
        >
          {loading ? "Solving\u2026" : "Run Classical vs QUBO vs QAOA"}
        </button>
      </Card>

      {loading && <LoadingState label="Solving QUBO via simulated annealing\u2026" />}
      {error && <ErrorState message={error} onRetry={run} />}
      {!loading && !error && !table && (
        <EmptyState title="No comparison run yet" description="Configure penalty coefficients above and run the comparison." />
      )}

      {table && !loading && (
        <>
          <Card title="Classical vs QUBO vs QAOA" subtitle="Reported honestly \u2014 no quantum advantage is assumed">
            <table className="w-full text-sm mb-4">
              <thead>
                <tr className="text-left text-ink-muted text-xs uppercase tracking-wider border-b border-hairline">
                  <th className="pb-2 font-normal">Strategy</th>
                  <th className="pb-2 font-normal text-right">Return</th>
                  <th className="pb-2 font-normal text-right">Risk</th>
                  <th className="pb-2 font-normal text-right">Sharpe</th>
                  <th className="pb-2 font-normal text-right">Runtime (s)</th>
                  <th className="pb-2 font-normal text-right">Holdings</th>
                </tr>
              </thead>
              <tbody className="font-mono">
                {table.map((r) => (
                  <tr key={r.strategy} className="border-b border-hairline/50">
                    <td className={`py-2 ${r.strategy.includes("Quantum") || r.strategy.includes("QAOA") ? "text-quantum" : "text-ink"}`}>{r.strategy}</td>
                    {r.error ? (
                      <td colSpan={5} className="py-2 text-ink-faint font-body text-xs">{r.error}</td>
                    ) : (
                      <>
                        <td className="py-2 text-right text-signal-pos">{formatPct(r.return_pct!)}</td>
                        <td className="py-2 text-right text-amber">{formatPct(r.risk_pct!)}</td>
                        <td className="py-2 text-right">{r.sharpe!.toFixed(3)}</td>
                        <td className="py-2 text-right text-ink-muted">{r.runtime_sec!.toFixed(4)}</td>
                        <td className="py-2 text-right text-ink-muted">{r.n_holdings}</td>
                      </>
                    )}
                  </tr>
                ))}
              </tbody>
            </table>
            <ResponsiveContainer width="100%" height={240}>
              <BarChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="#232838" />
                <XAxis dataKey="strategy" tick={{ fill: "#8992a6", fontSize: 10 }} interval={0} angle={-15} textAnchor="end" height={60} />
                <YAxis tick={{ fill: "#8992a6", fontSize: 11 }} />
                <Tooltip contentStyle={{ background: "#171b24", border: "1px solid #232838", borderRadius: 6, fontSize: 12 }} />
                <Legend wrapperStyle={{ fontSize: 11 }} />
                <Bar dataKey="return" name="Return %" fill="#4abf8a" radius={[3, 3, 0, 0]} />
                <Bar dataKey="risk" name="Risk %" fill="#e3a857" radius={[3, 3, 0, 0]} />
              </BarChart>
            </ResponsiveContainer>
          </Card>

          {matrix && (
            <Card title="QUBO Matrix" subtitle={`${qubovars} binary variables total \u00b7 showing first ${matrix.length}\u00d7${matrix.length} preview`}>
              <Heatmap labels={matrix.map((_, i) => `x${i}`)} matrix={matrix} colorMode="diverging" cellSize={38} />
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
