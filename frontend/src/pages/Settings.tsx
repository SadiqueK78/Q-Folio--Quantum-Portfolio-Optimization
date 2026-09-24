import { Card } from "../components/Card";
import { useSettings, DEFAULT_SETTINGS } from "../context/SettingsContext";

export function Settings() {
  const { settings, setSettings } = useSettings();

  return (
    <div className="space-y-6">
      <div>
        <h1 className="font-display text-xl text-ink">Settings</h1>
        <p className="text-sm text-ink-muted mt-1">Global defaults used across Overview, Optimization, Backtesting, and Quantum Lab.</p>
      </div>

      <Card title="Investment">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Field label="Default Budget (\u20b9)">
            <input type="number" value={settings.budget} onChange={(e) => setSettings({ ...settings, budget: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Whole Shares Only">
            <select value={settings.wholeShares ? "yes" : "no"} onChange={(e) => setSettings({ ...settings, wholeShares: e.target.value === "yes" })} className="input">
              <option value="yes">Yes (integer shares)</option>
              <option value="no">No (fractional)</option>
            </select>
          </Field>
        </div>
      </Card>

      <Card title="Risk">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Field label="Risk-Free Rate">
            <input type="number" step="0.01" value={settings.riskFreeRate} onChange={(e) => setSettings({ ...settings, riskFreeRate: Number(e.target.value) })} className="input" />
          </Field>
        </div>
      </Card>

      <Card title="Allocation">
        <div className="grid grid-cols-2 md:grid-cols-4 gap-4">
          <Field label="Min Weight / Asset">
            <input type="number" step="0.01" value={settings.minWeight} onChange={(e) => setSettings({ ...settings, minWeight: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Max Weight / Asset">
            <input type="number" step="0.01" value={settings.maxWeight} onChange={(e) => setSettings({ ...settings, maxWeight: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Min Holdings">
            <input type="number" value={settings.minHoldings} onChange={(e) => setSettings({ ...settings, minHoldings: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Max Holdings">
            <input type="number" value={settings.maxHoldings} onChange={(e) => setSettings({ ...settings, maxHoldings: Number(e.target.value) })} className="input" />
          </Field>
        </div>
      </Card>

      <Card title="Optimization">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Field label="Default Frequency">
            <select value={settings.frequency} onChange={(e) => setSettings({ ...settings, frequency: e.target.value as any })} className="input">
              <option value="daily">Daily</option>
              <option value="weekly">Weekly</option>
              <option value="monthly">Monthly</option>
            </select>
          </Field>
          <Field label="Transaction Cost %">
            <input type="number" step="0.0001" value={settings.transactionCostPct} onChange={(e) => setSettings({ ...settings, transactionCostPct: Number(e.target.value) })} className="input" />
          </Field>
        </div>
      </Card>

      <Card title="Quantum">
        <div className="grid grid-cols-2 md:grid-cols-3 gap-4">
          <Field label="QUBO Discretization Step">
            <input type="number" step="0.01" value={settings.weightStep} onChange={(e) => setSettings({ ...settings, weightStep: Number(e.target.value) })} className="input" />
          </Field>
          <Field label="Simulated Annealing Reads">
            <input type="number" step="50" value={settings.numReads} onChange={(e) => setSettings({ ...settings, numReads: Number(e.target.value) })} className="input" />
          </Field>
        </div>
      </Card>

      <button
        onClick={() => setSettings(DEFAULT_SETTINGS)}
        className="text-xs px-4 py-2 rounded border border-hairline text-ink-muted hover:text-ink hover:border-ink-faint transition-colors"
      >
        Reset to defaults
      </button>
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
