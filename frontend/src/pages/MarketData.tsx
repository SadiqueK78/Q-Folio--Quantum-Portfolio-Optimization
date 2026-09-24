import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { LoadingState, ErrorState } from "../components/States";
import { endpoints, type Asset, type Quote, type PriceRange, ApiError } from "../lib/api";
import { formatCurrency } from "../lib/format";
import { DataStatusPill } from "../components/DataStatusPill";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer, Legend } from "recharts";

const RANGES: PriceRange[] = ["1m", "3m", "6m", "1y", "2y", "5y", "10y", "max"];
const LINE_COLORS = ["#e3a857", "#8b7fe8", "#4abf8a", "#e1665b", "#5b8dee", "#c98bd9", "#e0c05a", "#7fb0e8", "#e88b7f", "#8ae8d4"];

const STATUS_LABEL: Record<string, { label: string; color: string }> = {
  latest_available: { label: "Latest Available", color: "text-signal-pos" },
  market_closed: { label: "Market Closed", color: "text-amber" },
  unavailable: { label: "Unavailable", color: "text-ink-faint" },
};

export function MarketData() {
  const [assets, setAssets] = useState<Asset[] | null>(null);
  const [quotes, setQuotes] = useState<Quote[] | null>(null);
  const [selected, setSelected] = useState<string>("TCS.NS");
  const [range, setRange] = useState<PriceRange>("1y");
  const [mode, setMode] = useState<"single" | "compare">("single");
  const [singleSeries, setSingleSeries] = useState<{ date: string; price: number }[] | null>(null);
  const [compareSeries, setCompareSeries] = useState<Record<string, any>[] | null>(null);
  const [compareSymbols, setCompareSymbols] = useState<string[]>([]);
  const [dataSource, setDataSource] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([endpoints.assets(), endpoints.marketData()])
      .then(([a, q]) => {
        setAssets(a);
        setQuotes(q);
      })
      .catch(() => {});
  }, []);

  useEffect(() => {
    setLoading(true);
    setError(null);
    if (mode === "single") {
      endpoints
        .priceSeries(selected, range)
        .then((res) => {
          setSingleSeries(Object.entries(res.series).map(([date, price]) => ({ date, price })));
          setDataSource(res.data_source);
        })
        .catch((e) => setError(e instanceof ApiError ? String(e.message) : String(e)))
        .finally(() => setLoading(false));
    } else {
      endpoints
        .allPrices(range)
        .then((res) => {
          setCompareSymbols(res.symbols);
          setDataSource(res.data_source);
          setCompareSeries(Object.entries(res.series).map(([date, row]) => ({ date, ...row })));
        })
        .catch((e) => setError(e instanceof ApiError ? String(e.message) : String(e)))
        .finally(() => setLoading(false));
    }
  }, [selected, range, mode]);

  const quote = quotes?.find((q) => q.symbol === selected);
  const asset = assets?.find((a) => a.symbol === selected);

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-ink">Market Data</h1>
        <p className="text-sm text-ink-muted mt-1">Historical price charts and latest quotes, sourced from Yahoo Finance.</p>
      </div>

      {quotes && (
        <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
          {quotes.map((q) => {
            const cfg = STATUS_LABEL[q.status] || STATUS_LABEL.unavailable;
            return (
              <button
                key={q.symbol}
                onClick={() => { setSelected(q.symbol); setMode("single"); }}
                className={`text-left bg-surface-raised border rounded-lg px-3 py-2.5 transition-colors ${
                  selected === q.symbol && mode === "single" ? "border-amber" : "border-hairline hover:border-ink-faint"
                }`}
              >
                <div className="text-[10px] font-mono text-ink-muted">{q.symbol.replace(".NS", "")}</div>
                <div className="font-mono text-sm text-ink mt-0.5">{q.price ? formatCurrency(q.price) : "\u2014"}</div>
                <div className={`text-[10px] mt-0.5 ${cfg.color}`}>{cfg.label}</div>
              </button>
            );
          })}
        </div>
      )}

      <Card
        title={mode === "single" ? `${asset?.name || selected} \u2014 Price History` : "All Assets (normalized to 100)"}
        subtitle={mode === "single" ? asset?.sector : "Overlay comparison, indexed to the start of the selected range"}
        action={
          <div className="flex items-center gap-2">
            {dataSource && <DataStatusPill source={dataSource} />}
            <button
              onClick={() => setMode("single")}
              className={`text-xs px-3 py-1.5 rounded border ${mode === "single" ? "border-amber text-amber" : "border-hairline text-ink-muted"}`}
            >
              Single Asset
            </button>
            <button
              onClick={() => setMode("compare")}
              className={`text-xs px-3 py-1.5 rounded border ${mode === "compare" ? "border-amber text-amber" : "border-hairline text-ink-muted"}`}
            >
              Compare All
            </button>
          </div>
        }
      >
        <div className="flex gap-2 mb-4">
          {RANGES.map((r) => (
            <button
              key={r}
              onClick={() => setRange(r)}
              className={`text-xs px-2.5 py-1 rounded ${range === r ? "bg-amber text-canvas" : "text-ink-muted hover:text-ink"}`}
            >
              {r.toUpperCase()}
            </button>
          ))}
        </div>

        {loading && <LoadingState label="Loading price history\u2026" />}
        {error && <ErrorState message={error} />}

        {!loading && !error && mode === "single" && singleSeries && (
          <ResponsiveContainer width="100%" height={360}>
            <LineChart data={singleSeries}>
              <CartesianGrid strokeDasharray="3 3" stroke="#232838" />
              <XAxis dataKey="date" tick={{ fill: "#8992a6", fontSize: 10 }} minTickGap={60} />
              <YAxis tick={{ fill: "#8992a6", fontSize: 11 }} domain={["auto", "auto"]} tickFormatter={(v) => `\u20b9${v}`} />
              <Tooltip
                contentStyle={{ background: "#171b24", border: "1px solid #232838", borderRadius: 6, fontSize: 12 }}
                formatter={(v) => formatCurrency(Number(v))}
              />
              <Line type="monotone" dataKey="price" stroke="#e3a857" dot={false} strokeWidth={2} />
            </LineChart>
          </ResponsiveContainer>
        )}

        {!loading && !error && mode === "compare" && compareSeries && (
          <ResponsiveContainer width="100%" height={400}>
            <LineChart data={compareSeries}>
              <CartesianGrid strokeDasharray="3 3" stroke="#232838" />
              <XAxis dataKey="date" tick={{ fill: "#8992a6", fontSize: 10 }} minTickGap={60} />
              <YAxis tick={{ fill: "#8992a6", fontSize: 11 }} />
              <Tooltip contentStyle={{ background: "#171b24", border: "1px solid #232838", borderRadius: 6, fontSize: 12 }} />
              <Legend wrapperStyle={{ fontSize: 10 }} />
              {compareSymbols.map((s, i) => (
                <Line key={s} type="monotone" dataKey={s} name={s.replace(".NS", "")} stroke={LINE_COLORS[i % LINE_COLORS.length]} dot={false} strokeWidth={1.5} connectNulls />
              ))}
            </LineChart>
          </ResponsiveContainer>
        )}
      </Card>

      {quote && mode === "single" && (
        <Card title="Latest Quote">
          <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
            <div><div className="text-xs text-ink-muted">Price</div><div className="font-mono text-ink mt-1">{quote.price ? formatCurrency(quote.price) : "\u2014"}</div></div>
            <div><div className="text-xs text-ink-muted">Status</div><div className={`mt-1 ${STATUS_LABEL[quote.status]?.color}`}>{STATUS_LABEL[quote.status]?.label}</div></div>
            <div><div className="text-xs text-ink-muted">Market State</div><div className="text-ink mt-1">{quote.market_state}</div></div>
            <div><div className="text-xs text-ink-muted">As Of</div><div className="text-ink-muted mt-1 text-xs">{quote.as_of}</div></div>
          </div>
        </Card>
      )}
    </div>
  );
}
