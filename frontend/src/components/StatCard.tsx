import { signColor, signPrefix } from "../lib/format";

export function StatCard({ label, value, delta, deltaSuffix = "%", hint }: {
  label: string; value: string; delta?: number; deltaSuffix?: string; hint?: string;
}) {
  return (
    <div className="bg-surface border border-hairline rounded-lg p-4">
      <div className="text-xs text-ink-muted uppercase tracking-wider">{label}</div>
      <div className="font-mono text-2xl mt-1.5 text-ink">{value}</div>
      {delta !== undefined && (
        <div className={`text-xs mt-1 mono-num ${signColor(delta)}`}>
          {signPrefix(delta)}{delta.toFixed(2)}{deltaSuffix}
        </div>
      )}
      {hint && <div className="text-xs text-ink-faint mt-1">{hint}</div>}
    </div>
  );
}
