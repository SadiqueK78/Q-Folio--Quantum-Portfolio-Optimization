import { useEffect, useState } from "react";
import { Card } from "../components/Card";
import { LoadingState, ErrorState, EmptyState } from "../components/States";
import { endpoints, type EventEntry, type ReoptimizeResult, ApiError } from "../lib/api";
import { DataStatusPill } from "../components/DataStatusPill";
import { useSettings } from "../context/SettingsContext";
import { formatPct } from "../lib/format";

const EVENT_ICON: Record<string, string> = { company: "\ud83d\udd35", sector: "\ud83d\udfe1", market: "\ud83d\udd34" };

export function NewsEvents() {
  const { toOptimizeParams } = useSettings();
  const [events, setEvents] = useState<EventEntry[] | null>(null);
  const [impact, setImpact] = useState<Record<string, number> | null>(null);
  const [dataSource, setDataSource] = useState<string>("");
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

  const [reopt, setReopt] = useState<ReoptimizeResult | null>(null);
  const [reoptLoading, setReoptLoading] = useState(false);
  const [reoptError, setReoptError] = useState<string | null>(null);

  useEffect(() => {
    Promise.all([endpoints.events(), endpoints.eventsImpact()])
      .then(([ev, imp]) => {
        setEvents(ev);
        setImpact(imp.adjustments);
        setDataSource(imp.data_source);
      })
      .catch((e) => setError(e instanceof ApiError ? String(e.message) : String(e)))
      .finally(() => setLoading(false));
  }, []);

  async function checkReoptimization() {
    setReoptLoading(true);
    setReoptError(null);
    try {
      const result = await endpoints.reoptimize({
        ...toOptimizeParams(), strategy: "max_sharpe", apply_news_adjustment: true, current_weights: null,
      });
      setReopt(result);
    } catch (e) {
      setReoptError(e instanceof ApiError ? JSON.stringify(e.detail) : String(e));
    } finally {
      setReoptLoading(false);
    }
  }

  return (
    <div className="space-y-6">
      <div className="flex items-center justify-between">
        <div>
          <h1 className="font-display text-xl text-ink">News & Events</h1>
          <p className="text-sm text-ink-muted mt-1">3 agent roles over free RSS sources: Market, Company, Sector.</p>
        </div>
        {dataSource && <DataStatusPill source={dataSource === "live_rss" ? "live_rss" : "synthetic"} />}
      </div>

      {loading && <LoadingState label="Fetching and classifying news\u2026" />}
      {error && <ErrorState message={error} />}

      {events && !loading && (
        <>
          {events.length === 0 ? (
            <EmptyState title="No events detected" description="No RSS entries matched a market, company, or sector keyword right now." />
          ) : (
            <Card title="Event Timeline">
              <div className="space-y-3">
                {events.map((e, i) => (
                  <div key={i} className="flex items-start gap-3 pb-3 border-b border-hairline/50 last:border-0">
                    <span className="text-sm mt-0.5">{EVENT_ICON[e.event_type] || "\u26aa"}</span>
                    <div className="flex-1 min-w-0">
                      <div className="text-sm text-ink">{e.headline}</div>
                      <div className="flex flex-wrap gap-x-3 gap-y-1 mt-1 text-[11px] text-ink-muted">
                        <span>{e.agent}</span>
                        {e.company && <span className="text-amber">{e.company}</span>}
                        {e.sector && <span className="text-quantum">{e.sector}</span>}
                        <span>sentiment {e.sentiment > 0 ? "+" : ""}{e.sentiment.toFixed(2)}</span>
                        <span>severity {e.severity.toFixed(2)}</span>
                        <span>confidence {e.confidence.toFixed(2)}</span>
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          {impact && (
            <Card title="Event Impact on Portfolio" subtitle="Bounded adjustment score per asset \u2014 signal for review, not a price predictor">
              <div className="grid grid-cols-2 md:grid-cols-5 gap-3">
                {Object.entries(impact).map(([symbol, value]) => (
                  <div key={symbol} className="bg-surface-raised border border-hairline rounded-lg px-3 py-2.5">
                    <div className="text-[10px] text-ink-muted font-mono">{symbol}</div>
                    <div className={`font-mono text-sm mt-0.5 ${value > 0 ? "text-signal-pos" : value < 0 ? "text-signal-neg" : "text-ink-muted"}`}>
                      {value > 0 ? "+" : ""}{value.toFixed(3)}
                    </div>
                  </div>
                ))}
              </div>
            </Card>
          )}

          <Card
            title="Dynamic Reoptimization"
            subtitle="Compares an equal-weight baseline against a Max-Sharpe recommendation using event-adjusted expected returns"
            action={
              <button
                onClick={checkReoptimization}
                disabled={reoptLoading}
                className="text-xs px-3 py-1.5 rounded bg-amber text-canvas font-display font-medium hover:bg-amber/90 transition-colors disabled:opacity-50"
              >
                {reoptLoading ? "Checking\u2026" : "Check for Reoptimization"}
              </button>
            }
          >
            {reoptLoading && <LoadingState label="Adjusting expected returns and re-solving\u2026" />}
            {reoptError && <ErrorState message={reoptError} onRetry={checkReoptimization} />}
            {!reoptLoading && !reoptError && !reopt && (
              <EmptyState title="No reoptimization check run yet" description="Click Check for Reoptimization to see how current events would shift the recommended allocation." />
            )}
            {reopt && !reoptLoading && (
              <div className="space-y-4">
                <div className="text-xs text-ink-muted">{reopt.note}</div>
                {reopt.diff.length === 0 ? (
                  <div className="text-sm text-signal-pos">No material allocation changes recommended right now.</div>
                ) : (
                  <table className="w-full text-sm">
                    <thead>
                      <tr className="text-left text-ink-muted text-xs uppercase tracking-wider border-b border-hairline">
                        <th className="pb-2 font-normal">Symbol</th>
                        <th className="pb-2 font-normal text-right">Current</th>
                        <th className="pb-2 font-normal text-right">Recommended</th>
                        <th className="pb-2 font-normal text-right">Change</th>
                        <th className="pb-2 font-normal">Reason</th>
                      </tr>
                    </thead>
                    <tbody className="font-mono">
                      {reopt.diff.map((row) => (
                        <tr key={row.symbol} className="border-b border-hairline/50 align-top">
                          <td className="py-2 text-ink whitespace-nowrap">{row.symbol}</td>
                          <td className="py-2 text-right text-ink-muted">{formatPct(row.current_pct)}</td>
                          <td className="py-2 text-right text-amber">{formatPct(row.recommended_pct)}</td>
                          <td className={`py-2 text-right ${row.change_pct > 0 ? "text-signal-pos" : row.change_pct < 0 ? "text-signal-neg" : "text-ink-muted"}`}>
                            {row.change_pct > 0 ? "+" : ""}{formatPct(row.change_pct)}
                          </td>
                          <td className="py-2 text-ink-muted font-body text-xs max-w-md">{row.reason}</td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                )}
              </div>
            )}
          </Card>
        </>
      )}
    </div>
  );
}
