/** Matrix heatmap — used for correlation, covariance, and the QUBO matrix.
 * Uses the amber<->quantum-violet axis so "classical" and "quantum" data
 * reads consistently across the whole app: negative/cool values lean
 * violet, positive/warm values lean amber, centered on a neutral surface. */
export function Heatmap({ labels, matrix, colorMode = "diverging", cellSize = 42 }: {
  labels: string[];
  matrix: number[][];
  colorMode?: "diverging" | "sequential";
  cellSize?: number;
}) {
  const flat = matrix.flat().filter((v) => Number.isFinite(v));
  const max = Math.max(...flat.map(Math.abs), 1e-9);

  function cellColor(v: number): string {
    if (!Number.isFinite(v)) return "#171b24";
    const t = Math.min(Math.abs(v) / max, 1);
    if (colorMode === "diverging") {
      if (v >= 0) {
        // amber ramp
        const r = Math.round(23 + t * (227 - 23));
        const g = Math.round(27 + t * (168 - 27));
        const b = Math.round(36 + t * (87 - 36));
        return `rgb(${r},${g},${b})`;
      } else {
        const r = Math.round(23 + t * (139 - 23));
        const g = Math.round(27 + t * (127 - 27));
        const b = Math.round(36 + t * (232 - 36));
        return `rgb(${r},${g},${b})`;
      }
    }
    const r = Math.round(23 + t * (227 - 23));
    const g = Math.round(27 + t * (168 - 27));
    const b = Math.round(36 + t * (87 - 36));
    return `rgb(${r},${g},${b})`;
  }

  return (
    <div className="overflow-x-auto">
      <div className="inline-block">
        <div className="flex" style={{ marginLeft: cellSize * 1.6 }}>
          {labels.map((l) => (
            <div
              key={l}
              className="text-ink-faint text-[10px] font-mono flex items-end justify-center pb-1"
              style={{ width: cellSize, height: cellSize * 1.6, writingMode: "vertical-rl" }}
            >
              {l.replace(".NS", "")}
            </div>
          ))}
        </div>
        {matrix.map((row, i) => (
          <div key={i} className="flex items-center">
            <div
              className="text-ink-faint text-[10px] font-mono text-right pr-2 flex items-center justify-end"
              style={{ width: cellSize * 1.6, height: cellSize }}
            >
              {labels[i]?.replace(".NS", "")}
            </div>
            {row.map((v, j) => (
              <div
                key={j}
                title={`${labels[i]} / ${labels[j]}: ${v.toFixed(3)}`}
                className="flex items-center justify-center text-[9px] font-mono border border-canvas/60"
                style={{ width: cellSize, height: cellSize, background: cellColor(v), color: Math.abs(v) / max > 0.55 ? "#0a0c10" : "#c7cbd6" }}
              >
                {v.toFixed(2)}
              </div>
            ))}
          </div>
        ))}
      </div>
    </div>
  );
}
