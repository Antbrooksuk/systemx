"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import { useLive, LiveTrade, HistoricalTrade } from "../../hooks/useLive";
import { StatCard } from "../../components/StatCard";
import { TradeDetail } from "../../components/TradeLog";
import { EquityCurve } from "../../components/EquityCurve";
import { EquityPoint } from "../../lib/types";

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatPip(price: number | undefined | null, pair: string): string {
  if (price == null) return "—";
  const decimals = pair.endsWith("JPY") ? 3 : 5;
  return price.toFixed(decimals);
}

function formatTimeOnly(date: string | null) {
  if (!date) return "";
  try {
    return new Date(date).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  } catch { return ""; }
}

function getSignalColor(signal: string) {
  if (signal === "LONG") return "text-profit";
  if (signal === "SHORT") return "text-loss";
  return "text-muted";
}

function getExitColor(reason: string) {
  if (reason === "TP") return "text-profit";
  if (reason === "SL") return "text-loss";
  if (reason === "TIME_STOP") return "text-warn";
  return "text-muted";
}

function getPnlColor(pnl: number, exitReason: string) {
  if (exitReason === "TP") return "text-profit";
  if (exitReason === "SL") return "text-loss";
  if (exitReason === "TIME_STOP") {
    if (pnl > 0) return "text-profit";
    if (pnl < 0) return "text-loss";
  }
  return "text-muted";
}

function calculateEVData(historicalTrades: HistoricalTrade[], startingBalance: number) {
  if (historicalTrades.length === 0) return [];
  const filledTrades = historicalTrades.filter(t => t.exit_reason !== "SKIP" && t.exit_time);
  const sortedTrades = filledTrades.sort((a, b) =>
    new Date(a.exit_time || a.entry_time).getTime() - new Date(b.exit_time || b.entry_time).getTime()
  );
  const avgWinPnl = sortedTrades.filter(t => t.exit_reason === "TP").reduce((s, t) => s + t.pnl_pct, 0) / (sortedTrades.filter(t => t.exit_reason === "TP").length || 1);
  const avgLossPnl = sortedTrades.filter(t => t.exit_reason === "SL").reduce((s, t) => s + t.pnl_pct, 0) / (sortedTrades.filter(t => t.exit_reason === "SL").length || 1);
  const winRate = sortedTrades.filter(t => t.exit_reason === "TP").length / (sortedTrades.length || 1);
  const evPct = (winRate * avgWinPnl) + ((1 - winRate) * avgLossPnl);
  const evData: { trade: number; ev: number; upper: number; lower: number }[] = [{ trade: 0, ev: startingBalance, upper: startingBalance, lower: startingBalance }];
  let currentEquity = startingBalance;
  let cumulativeEV = startingBalance;
  let upperBound = startingBalance;
  let lowerBound = startingBalance;
  sortedTrades.forEach((trade, index) => {
    currentEquity += (trade.pnl_pct / 100) * currentEquity;
    cumulativeEV += (evPct / 100) * cumulativeEV;
    const variance = Math.sqrt(index + 1) * Math.abs(evPct) * 0.5;
    upperBound = cumulativeEV + variance * 0.15;
    lowerBound = cumulativeEV - variance * 0.15;
    evData.push({ trade: index + 1, ev: cumulativeEV, upper: upperBound, lower: Math.max(lowerBound, 0) });
  });
  return evData;
}

function calculateDrawdown(equityCurve: { equity: number }[]): number {
  if (equityCurve.length === 0) return 0;
  let maxEquity = equityCurve[0].equity;
  let maxDrawdown = 0;
  for (const point of equityCurve) {
    if (point.equity > maxEquity) maxEquity = point.equity;
    const dd = ((maxEquity - point.equity) / maxEquity) * 100;
    if (dd > maxDrawdown) maxDrawdown = dd;
  }
  return maxDrawdown;
}

function buildEquityCurve(historicalTrades: HistoricalTrade[], startingBalance: number) {
  const filledTrades = historicalTrades.filter(t => t.exit_reason !== "SKIP" && t.exit_time);
  const curve: { trade: number; equity: number; date: string }[] = [{ trade: 0, equity: startingBalance, date: "" }];
  let eq = startingBalance;
  filledTrades.sort((a, b) => new Date(a.exit_time || a.entry_time).getTime() - new Date(b.exit_time || b.entry_time).getTime());
  filledTrades.forEach((trade, i) => {
    eq += (trade.pnl_pct / 100) * eq;
    curve.push({ trade: i + 1, equity: eq, date: trade.exit_time || trade.entry_time });
  });
  return curve;
}

type BottomTab = "trades" | "reports" | "logs";

export default function LivePage() {
  const { state, error, logs } = useLive();
  const [showEV, setShowEV] = useState(false);
  const [bottomTab, setBottomTab] = useState<BottomTab>("trades");
  const [tradeFilter, setTradeFilter] = useState<"all" | "filled" | "skip">("all");
  const [selectedTrade, setSelectedTrade] = useState<any>(null);
  const [sessionReports, setSessionReports] = useState("");
  const isConnected = !!state;

  const STARTING_BALANCE = 2000;

  useEffect(() => {
    const fetchReports = async () => {
      try {
        const res = await fetch(`${process.env.NEXT_PUBLIC_BOT_API_URL}/session-reports`);
        const data = await res.json();
        setSessionReports(data.reports || "No session reports yet.");
      } catch { setSessionReports("Failed to load."); }
    };
    fetchReports();
  }, []);

  const allTradeEvents = (state?.historicalTrades || []).map((t: HistoricalTrade) => ({
    date: t.exit_time || t.entry_time,
    pair: t.pair,
    session: t.session,
    signal: t.direction || (t.exit_reason === "SKIP" ? "SKIP" : ""),
    skip_reason: t.exit_reason === "SKIP" ? (t.exit_reason || "") : null,
    entry: t.entry,
    sl: t.sl,
    tp: t.tp,
    exit_price: t.exit_price,
    exit_reason: t.exit_reason,
    pips: t.pips,
    pnl_pct: t.pnl_pct,
    spread_pips: 0,
    filled: t.exit_reason !== "SKIP" && t.exit_reason !== "LIMIT",
    units: t.units,
    sl_offset_pips: 3,
  }));

  const sortedTrades = [...allTradeEvents].sort((a, b) => (b.date || "").localeCompare(a.date || ""));
  const filteredTrades = tradeFilter === "all" ? sortedTrades
    : tradeFilter === "filled" ? sortedTrades.filter(t => t.signal !== "SKIP" && t.exit_reason !== "LIMIT")
    : sortedTrades.filter(t => t.signal === "SKIP");

  const filledTrades = allTradeEvents.filter(t => t.filled);
  const wins = filledTrades.filter(t => t.exit_reason === "TP" || (t.exit_reason === "TIME_STOP" && Math.sign(t.pnl_pct ?? 0) > 0)).length;
  const losses = filledTrades.filter(t => t.exit_reason === "SL" || (t.exit_reason === "TIME_STOP" && Math.sign(t.pnl_pct ?? 0) < 0)).length;
  const winRate = filledTrades.length > 0 ? (wins / filledTrades.length) * 100 : 0;
  const maxDrawdown = calculateDrawdown(buildEquityCurve(state?.historicalTrades || [], STARTING_BALANCE));
  const equityCurveData = buildEquityCurve(state?.historicalTrades || [], STARTING_BALANCE);
  const evData = calculateEVData(state?.historicalTrades || [], STARTING_BALANCE);
  const currentEquity = equityCurveData[equityCurveData.length - 1]?.equity ?? STARTING_BALANCE;
  const totalPnl = currentEquity - STARTING_BALANCE;
  const acc = state?.account;

  const errorLogs = logs.filter(l => l.level === "ERROR");

  if (error) {
    return (
      <div className="min-h-screen p-4 flex items-center justify-center">
        <div className="bg-card border border-loss rounded-lg p-6 text-center">
          <div className="text-loss font-bold mb-2">Connection Failed</div>
          <div className="text-muted text-sm">{error}</div>
        </div>
      </div>
    );
  }

  return (
    <div className="h-screen flex flex-col p-2 gap-2 overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-4">
          <span className="text-sm font-bold">SYSTEM-X</span>
          <Link href="/live" className="px-3 py-1 text-xs font-medium text-fg bg-border rounded">
            Live
          </Link>
          <Link href="/" className="px-3 py-1 text-xs font-medium text-muted hover:text-fg rounded hover:bg-border transition-colors">
            Backtest
          </Link>
        </div>
        <div className="flex items-center gap-4">
          {state?.session && (
            <span className="text-xs font-mono text-muted">
              {state.session.name} · {formatTime(state.session.seconds_remaining)} remaining
            </span>
          )}
          <span className={`text-xs font-mono flex items-center gap-1.5 ${isConnected ? "text-profit" : "text-warn"}`}>
            <span className={`w-1.5 h-1.5 rounded-full ${isConnected ? "bg-profit animate-pulse" : "bg-warn"}`} />
            {acc ? `£${acc.balance.toFixed(2)}` : "—"}
          </span>
        </div>
      </div>

      {/* Stats Row */}
      <div className="grid grid-cols-8 gap-2">
        <StatCard label="Trades" value={filledTrades.length} />
        <StatCard label="W" value={wins} color="profit" />
        <StatCard label="L" value={losses} color="loss" />
        <StatCard label="WR" value={`${winRate.toFixed(1)}%`} color={winRate >= 60 ? "profit" : "loss"} />
        <StatCard label="P&L" value={`${totalPnl >= 0 ? "+" : ""}£${totalPnl.toFixed(0)}`} color={totalPnl >= 0 ? "profit" : "loss"} />
        <StatCard label="DD" value={`${maxDrawdown.toFixed(1)}%`} color={maxDrawdown < 15 ? "profit" : "loss"} />
        <StatCard label="Orders" value={state?.orders?.length || 0} />
        <StatCard label="Errors" value={errorLogs.length} color={errorLogs.length > 0 ? "loss" : undefined} />
      </div>

      {/* Middle: Equity + Trade Log */}
      <div className="flex-1 grid grid-cols-2 gap-2 min-h-0">
        {/* Left: Equity Curve */}
        <div className="bg-card border border-border rounded-lg p-2.5 min-h-0">
          <div className="flex items-center justify-between mb-1">
            <div className="text-muted text-[10px] uppercase tracking-wider">Equity</div>
            <button
              onClick={() => setShowEV(!showEV)}
              className={`text-[10px] px-1.5 py-0.5 rounded ${showEV ? "bg-profit/20 text-profit" : "text-muted hover:text-fg"}`}
            >
              {showEV ? "Hide EV" : "EV"}
            </button>
          </div>
          <EquityCurve data={equityCurveData} evData={evData} showEV={showEV} />
        </div>

        {/* Right: Trade Log */}
        <div className="bg-card border border-border rounded-lg p-2.5 min-h-0 flex flex-col">
          <div className="flex items-center justify-between mb-1">
            <div className="text-muted text-[10px] uppercase tracking-wider">
              Trades
              <span className="ml-2 flex gap-1">
                {(["all", "filled", "skip"] as const).map(f => (
                  <button
                    key={f}
                    onClick={() => setTradeFilter(f)}
                    className={`px-1.5 py-0 text-[9px] rounded ${tradeFilter === f ? "bg-border text-fg" : "text-muted"}`}
                  >
                    {f} {f === "all" ? sortedTrades.length : f === "filled" ? filledTrades.length : sortedTrades.filter(t => t.signal === "SKIP").length}
                  </button>
                ))}
              </span>
            </div>
          </div>
          <div className="flex-1 overflow-y-auto">
            <table className="w-full text-[10px] font-mono">
              <thead className="sticky top-0 bg-card">
                <tr className="text-muted text-[9px]">
                  <th className="text-left pb-1 pr-1">Time</th>
                  <th className="text-left pb-1 pr-1">Pair</th>
                  <th className="text-left pb-1 pr-1">Ses</th>
                  <th className="text-left pb-1 pr-1">Sig</th>
                  <th className="text-right pb-1 pr-1">Exit</th>
                  <th className="text-right pb-1">P&L</th>
                </tr>
              </thead>
              <tbody>
                {filteredTrades.map((t, i) => {
                  const isSkip = t.signal === "SKIP";
                  return (
                    <tr
                      key={i}
                      className={`border-t border-border cursor-pointer hover:bg-border/30 ${isSkip ? "opacity-40" : ""}`}
                      onClick={() => setSelectedTrade(t)}
                    >
                      <td className="py-0.5 pr-1 text-muted whitespace-nowrap">{formatTimeOnly(t.date)}</td>
                      <td className="py-0.5 pr-1 text-fg">{t.pair}</td>
                      <td className="py-0.5 pr-1 text-muted capitalize">{t.session?.slice(0, 3)}</td>
                      <td className={`py-0.5 pr-1 ${getSignalColor(t.signal)}`}>
                        {isSkip ? "—" : t.signal.slice(0, 1)}
                      </td>
                      <td className={`py-0.5 pr-1 text-right ${isSkip ? "text-muted" : getExitColor(t.exit_reason)}`}>
                        {isSkip ? (t.exit_reason?.slice(0, 12) || "—") : t.exit_reason}
                      </td>
                      <td className={`py-0.5 text-right ${isSkip ? "" : getPnlColor(t.pnl_pct, t.exit_reason)}`}>
                        {isSkip ? "—" : `${t.pnl_pct > 0 ? "+" : ""}${t.pnl_pct.toFixed(2)}%`}
                      </td>
                    </tr>
                  );
                })}
              </tbody>
            </table>
          </div>
        </div>
      </div>

      {/* Bottom: Tabs */}
      <div className="h-72 flex flex-col">
        <div className="flex gap-1 mb-1">
          {(["trades", "reports", "logs"] as const).map(tab => (
            <button
              key={tab}
              onClick={() => setBottomTab(tab)}
              className={`px-2 py-0.5 text-[10px] rounded uppercase tracking-wider ${bottomTab === tab ? "bg-border text-fg" : "text-muted hover:text-fg"}`}
            >
              {tab} {tab === "logs" && errorLogs.length > 0 ? `(${errorLogs.length})` : ""}
            </button>
          ))}
        </div>
        <div className="flex-1 bg-card border border-border rounded-lg p-2 overflow-y-auto font-mono text-[10px]">
          {bottomTab === "logs" && (
            <div className="space-y-0.5">
              {logs.length === 0 ? (
                <div className="text-muted">No logs</div>
              ) : (
                logs.map((l, i) => (
                  <div key={i} className={`flex gap-2 ${
                    l.level === "ERROR" ? "text-loss" :
                    l.level === "WARNING" ? "text-warn" : "text-muted"
                  }`}>
                    <span className="shrink-0 text-[9px]">{l.time}</span>
                    <span className={`shrink-0 w-12 text-[9px] ${l.level === "ERROR" ? "font-bold" : ""}`}>{l.level}</span>
                    <span className="truncate">{l.message}</span>
                  </div>
                ))
              )}
            </div>
          )}
          {bottomTab === "reports" && (
            <pre className="whitespace-pre-wrap text-muted">{sessionReports || "No reports yet."}</pre>
          )}
          {bottomTab === "trades" && (
            <div>
              {sortedTrades.length === 0 ? (
                <div className="text-muted">No trades yet</div>
              ) : (
                <table className="w-full">
                  <thead>
                    <tr className="text-muted text-[9px] border-b border-border">
                      <th className="text-left pb-1 pr-2">Time</th>
                      <th className="text-left pb-1 pr-2">Pair</th>
                      <th className="text-left pb-1 pr-2">Session</th>
                      <th className="text-left pb-1 pr-2">Signal</th>
                      <th className="text-left pb-1 pr-2">Entry</th>
                      <th className="text-left pb-1 pr-2">SL</th>
                      <th className="text-left pb-1 pr-2">TP</th>
                      <th className="text-right pb-1 pr-2">Pips</th>
                      <th className="text-right pb-1">P&L%</th>
                    </tr>
                  </thead>
                  <tbody>
                    {sortedTrades.map((t, i) => {
                      const isSkip = t.signal === "SKIP";
                      return (
                        <tr key={i} className={`border-t border-border cursor-pointer hover:bg-border/30 ${isSkip ? "opacity-40" : ""}`}
                          onClick={() => setSelectedTrade(t)}>
                          <td className="py-0.5 pr-2 text-muted">{formatTimeOnly(t.date)}</td>
                          <td className="py-0.5 pr-2 text-fg">{t.pair}</td>
                          <td className="py-0.5 pr-2 text-muted capitalize">{t.session}</td>
                          <td className={`py-0.5 pr-2 ${getSignalColor(t.signal)}`}>{t.signal}</td>
                          <td className="py-0.5 pr-2">{isSkip ? "—" : formatPip(t.entry, t.pair)}</td>
                          <td className="py-0.5 pr-2 text-loss">{isSkip ? "—" : formatPip(t.sl, t.pair)}</td>
                          <td className="py-0.5 pr-2 text-profit">{isSkip ? "—" : formatPip(t.tp, t.pair)}</td>
                          <td className={`py-0.5 pr-2 text-right ${isSkip ? "" : t.pips > 0 ? "text-profit" : t.pips < 0 ? "text-loss" : ""}`}>
                            {isSkip ? "—" : `${t.pips > 0 ? "+" : ""}${t.pips?.toFixed(1)}`}
                          </td>
                          <td className={`py-0.5 text-right ${isSkip ? "" : getPnlColor(t.pnl_pct, t.exit_reason)}`}>
                            {isSkip ? "—" : `${t.pnl_pct > 0 ? "+" : ""}${t.pnl_pct.toFixed(2)}%`}
                          </td>
                        </tr>
                      );
                    })}
                  </tbody>
                </table>
              )}
            </div>
          )}
        </div>
      </div>

      <TradeDetail trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
    </div>
  );
}
