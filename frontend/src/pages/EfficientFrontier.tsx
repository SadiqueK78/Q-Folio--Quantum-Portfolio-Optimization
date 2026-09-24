import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { LoadingState, ErrorState } from "../components/States";
import { endpoints, type FrontierResponse, ApiError } from "../lib/api";
import { useSettings } from "../context/SettingsContext";
import { ScatterChart, Scatter, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

export function EfficientFrontier() {
  const { settings } = useSettings();
  const [data, setData] = useState<FrontierResponse | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setLoading(true);
    setError(null);
    endpoints
      .frontier(settings.maxWeight)
      .then(setData)
      .catch((e) => setError(e instanceof ApiError ? String(e.message) : String(e)))
      .finally(() => setLoading(false));
  }, [settings.maxWeight]);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-ink">Efficient Frontier</h1>
        <p className="text-sm text-ink-muted mt-1">Risk/return trade-off across feasible portfolios at max allocation {(settings.maxWeight * 100).toFixed(0)}% per asset.</p>
      </div>

      {loading && <LoadingState label="Sweeping the frontier\u2026" />}
      {error && <ErrorState message={error} />}

      {data && !loading && (
        <Card title="Risk vs. Return">
          <ResponsiveContainer width="100%" height={420}>
            <ScatterChart margin={{ left: 10, right: 20, top: 10, bottom: 10 }}>
              <CartesianGrid stroke="#232838" />
              <XAxis
                type="number" dataKey="risk" name="Risk" unit="%"
                tickFormatter={(v) => (v * 100).toFixed(0)}
                tick={{ fill: "#8992a6", fontSize: 11 }}
                label={{ value: "Volatility", position: "insideBottom", offset: -5, fill: "#8992a6", fontSize: 11 }}
              />
              <YAxis
                type="number" dataKey="return" name="Return" unit="%"
                tickFormatter={(v) => (v * 100).toFixed(0)}
                tick={{ fill: "#8992a6", fontSize: 11 }}
                label={{ value: "Expected Return", angle: -90, position: "insideLeft", fill: "#8992a6", fontSize: 11 }}
              />
              <Tooltip
                contentStyle={{ background: "#171b24", border: "1px solid #232838", borderRadius: 6, fontSize: 12 }}
                formatter={(v) => `${(Number(v) * 100).toFixed(2)}%`}
              />
              <Legend wrapperStyle={{ fontSize: 12 }} />
              <Scatter name="Efficient Frontier" data={data.frontier} fill="#e3a857" line shape="circle" />
              <Scatter name="Min Volatility" data={[data.min_volatility_point]} fill="#4abf8a" shape="star" />
              <Scatter name="Max Sharpe" data={[data.max_sharpe_point]} fill="#8b7fe8" shape="diamond" />
            </ScatterChart>
          </ResponsiveContainer>
        </Card>
      )}
    </div>
  );
}
