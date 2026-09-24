export function LoadingState({ label = "Loading data\u2026" }: { label?: string }) {
  return (
    <div className="flex items-center gap-3 py-10 justify-center text-ink-muted">
      <span className="relative flex h-2.5 w-2.5">
        <span className="animate-ping absolute inline-flex h-full w-full rounded-full bg-amber opacity-60" />
        <span className="relative inline-flex rounded-full h-2.5 w-2.5 bg-amber" />
      </span>
      <span className="text-sm">{label}</span>
    </div>
  );
}

export function ErrorState({ message, onRetry }: { message: string; onRetry?: () => void }) {
  return (
    <div className="border border-signal-neg/30 bg-signal-neg/5 rounded-lg p-5 text-sm">
      <div className="text-signal-neg font-medium mb-1">Unable to complete this request</div>
      <div className="text-ink-muted whitespace-pre-wrap">{message}</div>
      {onRetry && (
        <button
          onClick={onRetry}
          className="mt-3 text-xs px-3 py-1.5 rounded border border-hairline hover:border-signal-neg/50 text-ink transition-colors"
        >
          Retry
        </button>
      )}
    </div>
  );
}

export function EmptyState({ title, description }: { title: string; description: string }) {
  return (
    <div className="border border-dashed border-hairline rounded-lg p-10 text-center">
      <div className="text-ink font-display text-sm mb-1">{title}</div>
      <div className="text-ink-muted text-xs">{description}</div>
    </div>
  );
}
