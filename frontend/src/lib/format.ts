export function formatCurrency(value: number, currency = "INR"): string {
  const symbol = currency === "INR" ? "₹" : "$";
  return `${symbol}${value.toLocaleString("en-IN", { maximumFractionDigits: 0 })}`;
}

export function formatPct(value: number, decimals = 2): string {
  return `${value.toFixed(decimals)}%`;
}

export function formatNum(value: number, decimals = 2): string {
  return value.toLocaleString("en-IN", { minimumFractionDigits: decimals, maximumFractionDigits: decimals });
}

export function signColor(value: number): string {
  if (value > 0) return "text-signal-pos";
  if (value < 0) return "text-signal-neg";
  return "text-ink-muted";
}

export function signPrefix(value: number): string {
  return value > 0 ? "+" : "";
}
