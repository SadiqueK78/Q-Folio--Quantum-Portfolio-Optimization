export function DataStatusPill({ source }: { source: string }) {
  const map: Record<string, { label: string; color: string; dot: string }> = {
    live: { label: "Live \u00b7 Yahoo Finance", color: "text-signal-pos", dot: "bg-signal-pos" },
    cached_stale: { label: "Cached (stale)", color: "text-amber", dot: "bg-amber" },
    synthetic: { label: "Synthetic \u00b7 illustrative", color: "text-quantum", dot: "bg-quantum" },
    live_rss: { label: "Live \u00b7 RSS feeds", color: "text-signal-pos", dot: "bg-signal-pos" },
  };
  const cfg = map[source] || { label: source, color: "text-ink-muted", dot: "bg-ink-faint" };
  return (
    <div className="flex items-center gap-2 text-xs px-2.5 py-1 rounded-full border border-hairline bg-surface-raised">
      <span className={`relative flex h-1.5 w-1.5`}>
        {source === "live" && (
          <span className={`animate-ping absolute inline-flex h-full w-full rounded-full ${cfg.dot} opacity-60`} />
        )}
        <span className={`relative inline-flex rounded-full h-1.5 w-1.5 ${cfg.dot}`} />
      </span>
      <span className={cfg.color}>{cfg.label}</span>
    </div>
  );
}
