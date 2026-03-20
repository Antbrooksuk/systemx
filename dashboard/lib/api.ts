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

export async function runBacktest(year = 0, strategy = "base", startingCapital = 2000, riskPct = 0.01) {
  const params = new URLSearchParams({ year: String(year), strategy, starting_capital: String(startingCapital), risk_pct: String(riskPct) });
  const res = await fetch(`${API_URL}/backtest?${params}`);
  return res.json();
}

export async function getYears() {
  const res = await fetch(`${API_URL}/years`);
  return res.json();
}

export function streamBacktest(onMessage: (data: any) => void, year = 0, strategy = "base", startingCapital = 2000, riskPct = 0.01) {
  const ws = new WebSocket(`${API_URL.replace("http", "ws")}/ws/backtest/stream`);
  
  ws.onopen = () => {
    ws.send(JSON.stringify({ year, strategy, starting_capital: startingCapital, risk_pct: riskPct }));
  };
  
  ws.onmessage = (event) => {
    const data = JSON.parse(event.data);
    onMessage(data);
  };
  
  return ws;
}
