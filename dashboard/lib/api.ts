const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getStatus() {
  const res = await fetch(`${API_URL}/status`);
  return res.json();
}

export async function resetState() {
  const res = await fetch(`${API_URL}/reset`, { method: "POST" });
  return res.json();
}

export async function getStrategies() {
  const res = await fetch(`${API_URL}/strategies`);
  return res.json();
}

export async function runBacktest(periodDays = 0, years = 0, strategy = "base", startingCapital = 2000, riskPct = 0.01) {
  const params = new URLSearchParams({ period_days: String(periodDays), years: String(years), strategy, starting_capital: String(startingCapital), risk_pct: String(riskPct) });
  const res = await fetch(`${API_URL}/backtest?${params}`);
  return res.json();
}

export function streamBacktest(onMessage: (data: any) => void, years = 0, strategy = "base", periodDays = 0, startingCapital = 2000, riskPct = 0.01) {
  const ws = new WebSocket(`${API_URL.replace("http", "ws")}/ws/backtest/stream`);
  
  ws.onopen = () => {
    ws.send(JSON.stringify({ years, strategy, period_days: periodDays, starting_capital: startingCapital, risk_pct: riskPct }));
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };
  
  return ws;
}
