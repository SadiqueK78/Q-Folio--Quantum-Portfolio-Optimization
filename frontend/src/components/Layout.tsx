import { NavLink, Outlet } from "react-router-dom";
import { useEffect, useState } from "react";
import { DataStatusPill } from "./DataStatusPill";
import { endpoints, type DataStatus } from "../lib/api";

const NAV = [
  { to: "/", label: "Overview", glyph: "01" },
  { to: "/optimization", label: "Optimization", glyph: "02" },
  { to: "/risk", label: "Risk Analysis", glyph: "03" },
  { to: "/frontier", label: "Efficient Frontier", glyph: "04" },
  { to: "/quantum", label: "Quantum Lab", glyph: "05" },
  { to: "/backtesting", label: "Backtesting", glyph: "06" },
  { to: "/market-data", label: "Market Data", glyph: "07" },
  { to: "/news", label: "News & Events", glyph: "08" },
  { to: "/live-tv", label: "Live TV", glyph: "09" },
  { to: "/settings", label: "Settings", glyph: "10" },
];

export function Layout() {
  const [status, setStatus] = useState<DataStatus | null>(null);

  useEffect(() => {
    endpoints.dataStatus().then(setStatus).catch(() => setStatus(null));
  }, []);

  return (
    <div className="min-h-screen flex bg-canvas">
      <aside className="w-60 shrink-0 border-r border-hairline flex flex-col">
        <div className="px-5 py-5 border-b border-hairline">
          <div className="font-display text-sm font-semibold tracking-wide text-ink">
            PORTFOLIO<span className="text-amber">.</span>QUANTUM
          </div>
          <div className="text-[10px] text-ink-faint mt-1 tracking-wide">
            CLASSICAL + QUBO RESEARCH PLATFORM
          </div>
        </div>
        <nav className="flex-1 py-3">
          {NAV.map((item) => (
            <NavLink
              key={item.to}
              to={item.to}
              end={item.to === "/"}
              className={({ isActive }) =>
                `flex items-center gap-3 px-5 py-2.5 text-sm transition-colors border-l-2 ${
                  isActive
                    ? "border-amber text-ink bg-surface"
                    : "border-transparent text-ink-muted hover:text-ink hover:bg-surface/50"
                }`
              }
            >
              <span className="font-mono text-[10px] text-ink-faint">{item.glyph}</span>
              {item.label}
            </NavLink>
          ))}
        </nav>
        <div className="px-5 py-4 border-t border-hairline text-[10px] text-ink-faint leading-relaxed">
          Research / decision-support tool only.
          <br />Not financial advice.
        </div>
      </aside>

      <div className="flex-1 min-w-0 flex flex-col">
        <header className="h-14 border-b border-hairline flex items-center justify-between px-6 shrink-0">
          <div className="text-xs text-ink-muted">
            10 assets &middot; 10 sectors &middot; ₹ INR
          </div>
          <div className="flex items-center gap-3">
            {status && <DataStatusPill source={status.source_label} />}
          </div>
        </header>
        <main className="flex-1 overflow-y-auto px-6 py-6">
          <Outlet />
        </main>
      </div>
    </div>
  );
}
