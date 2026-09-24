import { createContext, useContext, useState, type ReactNode } from "react";
import type { OptimizeParams } from "../lib/api";

export interface Settings {
  budget: number;
  minWeight: number;
  maxWeight: number;
  minHoldings: number;
  maxHoldings: number;
  transactionCostPct: number;
  frequency: "daily" | "weekly" | "monthly";
  riskFreeRate: number;
  wholeShares: boolean;
  strategy: "equal_weight" | "min_volatility" | "max_sharpe" | "risk_parity";
  // QUBO / quantum
  riskAversion: number;
  penaltyBudget: number;
  penaltyHoldings: number;
  penaltySector: number;
  weightStep: number;
  numReads: number;
}

export const DEFAULT_SETTINGS: Settings = {
  budget: 100_000,
  minWeight: 0,
  maxWeight: 0.2,
  minHoldings: 5,
  maxHoldings: 10,
  transactionCostPct: 0.001,
  frequency: "monthly",
  riskFreeRate: 0.06,
  wholeShares: true,
  strategy: "max_sharpe",
  riskAversion: 3.0,
  penaltyBudget: 8.0,
  penaltyHoldings: 4.0,
  penaltySector: 4.0,
  weightStep: 0.05,
  numReads: 200,
};

interface Ctx {
  settings: Settings;
  setSettings: (s: Settings) => void;
  toOptimizeParams: () => OptimizeParams;
}

const SettingsContext = createContext<Ctx | null>(null);

export function SettingsProvider({ children }: { children: ReactNode }) {
  const [settings, setSettings] = useState<Settings>(DEFAULT_SETTINGS);

  const toOptimizeParams = (): OptimizeParams => ({
    budget: settings.budget,
    min_weight: settings.minWeight,
    max_weight: settings.maxWeight,
    min_holdings: settings.minHoldings,
    max_holdings: settings.maxHoldings,
    transaction_cost_pct: settings.transactionCostPct,
    sector_bounds: [],
    frequency: settings.frequency,
    risk_free_rate: settings.riskFreeRate,
    strategy: settings.strategy,
    whole_shares: settings.wholeShares,
  });

  return (
    <SettingsContext.Provider value={{ settings, setSettings, toOptimizeParams }}>
      {children}
    </SettingsContext.Provider>
  );
}

export function useSettings() {
  const ctx = useContext(SettingsContext);
  if (!ctx) throw new Error("useSettings must be used within SettingsProvider");
  return ctx;
}
