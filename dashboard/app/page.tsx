"use client";

import { useState, useEffect } from "react";
import Link from "next/link";
import {
  useBacktest,
  RISK_OPTIONS,
  CAPITAL_OPTIONS,
} from "../hooks/useBacktest";
import { StatCard } from "../components/StatCard";
import { EquityCurve } from "../components/EquityCurve";
import { TradeDetail } from "../components/TradeLog";
import { Trade } from "../lib/types";

function wrColor(wr: number) {
  if (wr >= 71) return "profit";
  if (wr >= 60) return "warn";
  return "loss";
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) return `${value >= 0 ? "+" : ""}£${(value / 1000000).toFixed(2)}M`;
  if (Math.abs(value) >= 1000) return `${value >= 0 ? "+" : ""}£${(value / 1000).toFixed(1)}K`;
  return `${value >= 0 ? "+" : ""}£${value.toFixed(2)}`;
}

function formatPip(price: number | undefined | null, pair: string): string {
  if (price == null) return "—";
  return price.toFixed(pair.endsWith("JPY") ? 3 : 5);
}

function formatTimeOnly(date: string | null) {
  if (!date) return "";
  try { return new Date(date).toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" }); }
  catch { return ""; }
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

type BottomTab = "trades" | "breakdown";

export default function Dashboard() {
  const {
    state,
    strategies,
    selectedStrategy,
    setSelectedStrategy,
    selectedCapital,
    setSelectedCapital,
    selectedRisk,
    setSelectedRisk,
    selectedYear,
    setSelectedYear,
    availableYears,
    fetchStrategies,
    runInstant,
  } = useBacktest();

  const [bottomTab, setBottomTab] = useState<BottomTab>("trades");
  const [tradeFilter, setTradeFilter] = useState<"all" | "filled" | "skip">("all");
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [showEV, setShowEV] = useState(false);

  useEffect(() => { fetchStrategies(); }, [fetchStrategies]);

  const pnl = state.current_capital - state.starting_capital;
  const pnlColor = pnl >= 0 ? "profit" : "loss";

  const filledTrades = state.trades.filter(t => t.signal !== "SKIP" && t.filled !== false && t.exit_reason !== "LIMIT");
  const skippedTrades = state.trades.filter(t => t.signal === "SKIP");
  const sortedTrades = [...state.trades].sort((a, b) => (b.date || "").localeCompare(a.date || ""));

  const filteredTrades = tradeFilter === "all" ? sortedTrades
    : tradeFilter === "filled" ? sortedTrades.filter(t => t.signal !== "SKIP" && t.exit_reason !== "LIMIT")
    : sortedTrades.filter(t => t.signal === "SKIP");

  const wins = filledTrades.filter(t => (t.pnl_pct ?? 0) > 0).length;
  const losses = filledTrades.filter(t => (t.pnl_pct ?? 0) < 0).length;
  const winRate = filledTrades.length > 0 ? (wins / filledTrades.length) * 100 : 0;
  const maxDrawdown = (() => {
    const curve = state.equity_curve;
    if (!curve.length) return 0;
    let max = curve[0].equity, dd = 0;
    for (const p of curve) {
      if (p.equity > max) max = p.equity;
      const d = ((max - p.equity) / max) * 100;
      if (d > dd) dd = d;
    }
    return dd;
  })();

  return (
    <div className="h-screen flex flex-col p-2 gap-2 overflow-hidden">
      {/* Header */}
      <header className="flex items-center gap-4">
        <span className="text-sm font-bold">SYSTEM-X</span>
        <Link href="/live" className="px-3 py-1 text-xs font-medium text-muted hover:text-fg rounded hover:bg-border transition-colors">Live</Link>
        <Link href="/" className="px-3 py-1 text-xs font-medium text-fg bg-border rounded">Backtest</Link>
        <div className="flex-1" />
        <div className="flex gap-2 items-center">
          <select value={selectedStrategy} onChange={(e) => setSelectedStrategy(e.target.value)} disabled={state.running}
            className="px-2 py-1 bg-card border border-border rounded text-[10px] text-fg focus:outline-none disabled:opacity-50">
            {strategies.map((s) => <option key={s.key} value={s.key}>{s.label}</option>)}
          </select>
          <select value={selectedCapital} onChange={(e) => setSelectedCapital(Number(e.target.value))} disabled={state.running}
            className="px-2 py-1 bg-card border border-border rounded text-[10px] text-fg focus:outline-none disabled:opacity-50">
            {CAPITAL_OPTIONS.map((c) => <option key={c} value={c}>£{c.toLocaleString()}</option>)}
          </select>
          <select value={selectedRisk} onChange={(e) => setSelectedRisk(Number(e.target.value))} disabled={state.running}
            className="px-2 py-1 bg-card border border-border rounded text-[10px] text-fg focus:outline-none disabled:opacity-50">
            {RISK_OPTIONS.map((r) => <option key={r} value={r}>{(r * 100).toFixed(1)}%</option>)}
          </select>
          <select value={selectedYear} onChange={(e) => setSelectedYear(Number(e.target.value))} disabled={state.running}
            className="px-2 py-1 bg-card border border-border rounded text-[10px] text-fg focus:outline-none disabled:opacity-50">
            {availableYears.map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
          <button onClick={runInstant} disabled={state.running}
            className="px-3 py-1 bg-card border border-border rounded hover:bg-border disabled:opacity-50 disabled:cursor-not-allowed text-[10px] font-medium">
            {state.running ? "..." : "Run"}
          </button>
        </div>
      </header>

      {/* Stats */}
      <div className="grid grid-cols-8 gap-2">
        <StatCard label="Trades" value={filledTrades.length} />
        <StatCard label="W" value={wins} color="profit" />
        <StatCard label="L" value={losses} color="loss" />
        <StatCard label="WR" value={`${winRate.toFixed(1)}%`} color={wrColor(winRate)} />
        <StatCard label="P&L" value={formatCurrency(pnl)} color={pnlColor} />
        <StatCard label="DD" value={`${maxDrawdown.toFixed(1)}%`} color={maxDrawdown < 15 ? "profit" : "loss"} />
        <StatCard label="Skips" value={skippedTrades.length} />
        <StatCard label="Account" value={formatCurrency(state.current_capital)} />
      </div>

      {/* Middle: Equity + Trade Log */}
      <div className="flex-1 grid grid-cols-2 gap-2 min-h-0">
        <div className="bg-card border border-border rounded-lg p-2.5 min-h-0">
          <div className="flex items-center justify-between mb-1">
            <div className="text-muted text-[10px] uppercase tracking-wider">Equity</div>
            <button onClick={() => setShowEV(!showEV)}
              className={`text-[10px] px-1.5 py-0.5 rounded ${showEV ? "bg-profit/20 text-profit" : "text-muted hover:text-fg"}`}>
              {showEV ? "Hide EV" : "EV"}
            </button>
          </div>
          <EquityCurve data={state.equity_curve} showEV={showEV} />
        </div>

        <div className="bg-card border border-border rounded-lg p-2.5 min-h-0 flex flex-col">
          <div className="flex items-center justify-between mb-1">
            <div className="text-muted text-[10px] uppercase tracking-wider">
              Trades
              <span className="ml-2 flex gap-1">
                {(["all", "filled", "skip"] as const).map(f => (
                  <button key={f} onClick={() => setTradeFilter(f)}
                    className={`px-1.5 py-0 text-[9px] rounded ${tradeFilter === f ? "bg-border text-fg" : "text-muted"}`}>
                    {f} {f === "all" ? sortedTrades.length : f === "filled" ? filledTrades.length : skippedTrades.length}
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
                    <tr key={i} className={`border-t border-border cursor-pointer hover:bg-border/30 ${isSkip ? "opacity-40" : ""}`}
                      onClick={() => setSelectedTrade(t)}>
                      <td className="py-0.5 pr-1 text-muted whitespace-nowrap">{formatTimeOnly(t.date)}</td>
                      <td className="py-0.5 pr-1 text-fg">{t.pair}</td>
                      <td className="py-0.5 pr-1 text-muted capitalize">{t.session?.slice(0, 3)}</td>
                      <td className={`py-0.5 pr-1 ${getSignalColor(t.signal)}`}>{isSkip ? "—" : t.signal.slice(0, 1)}</td>
                      <td className={`py-0.5 pr-1 text-right ${isSkip ? "text-muted" : getExitColor(t.exit_reason)}`}>
                        {isSkip ? (t.skip_reason?.slice(0, 12) || "—") : t.exit_reason}
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

      {/* Bottom */}
      <div className="h-72 flex flex-col">
        <div className="flex gap-1 mb-1">
          {(["trades", "breakdown"] as const).map(tab => (
            <button key={tab} onClick={() => setBottomTab(tab)}
              className={`px-2 py-0.5 text-[10px] rounded uppercase tracking-wider ${bottomTab === tab ? "bg-border text-fg" : "text-muted hover:text-fg"}`}>
              {tab}
            </button>
          ))}
        </div>
        <div className="flex-1 bg-card border border-border rounded-lg p-2 overflow-y-auto">
          {bottomTab === "trades" && (
            <table className="w-full text-[10px] font-mono">
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
          {bottomTab === "breakdown" && (
            <div className="text-[10px] font-mono space-y-3">
              <div className="grid grid-cols-3 gap-4">
                <div className="text-center">
                  <div className="text-muted text-[9px] uppercase">Avg Pips</div>
                  <div className={`text-sm font-bold ${filledTrades.length ? (filledTrades.reduce((s, t) => s + t.pips, 0) / filledTrades.length) >= 0 ? "text-profit" : "text-loss" : ""}`}>
                    {filledTrades.length ? (filledTrades.reduce((s, t) => s + t.pips, 0) / filledTrades.length).toFixed(2) : "—"}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-muted text-[9px] uppercase">Avg P&L%</div>
                  <div className={`text-sm font-bold ${filledTrades.length ? (filledTrades.reduce((s, t) => s + t.pnl_pct, 0) / filledTrades.length) >= 0 ? "text-profit" : "text-loss" : ""}`}>
                    {filledTrades.length ? `${(filledTrades.reduce((s, t) => s + t.pnl_pct, 0) / filledTrades.length) >= 0 ? "+" : ""}${(filledTrades.reduce((s, t) => s + t.pnl_pct, 0) / filledTrades.length).toFixed(2)}%` : "—"}
                  </div>
                </div>
                <div className="text-center">
                  <div className="text-muted text-[9px] uppercase">Skips</div>
                  <div className="text-sm font-bold text-muted">{skippedTrades.length}</div>
                </div>
              </div>
              <div className="grid grid-cols-2 gap-4">
                <div>
                  <div className="text-muted text-[9px] uppercase mb-1">By Session</div>
                  {["london", "ny"].map(ses => {
                    const st = filledTrades.filter(t => t.session === ses);
                    const w = st.filter(t => (t.pnl_pct ?? 0) > 0).length;
                    const l = st.filter(t => (t.pnl_pct ?? 0) < 0).length;
                    return (
                      <div key={ses} className="flex justify-between text-[10px] border-t border-border py-0.5">
                        <span className="text-muted capitalize">{ses}</span>
                        <span><span className="text-profit">{w}W</span> / <span className="text-loss">{l}L</span> ({st.length ? ((w / st.length) * 100).toFixed(0) : 0}%)</span>
                      </div>
                    );
                  })}
                </div>
                <div>
                  <div className="text-muted text-[9px] uppercase mb-1">By Pair</div>
                  {["EURUSD", "GBPUSD", "USDJPY", "EURJPY"].map(pair => {
                    const pt = filledTrades.filter(t => t.pair === pair);
                    const w = pt.filter(t => (t.pnl_pct ?? 0) > 0).length;
                    const l = pt.filter(t => (t.pnl_pct ?? 0) < 0).length;
                    return (
                      <div key={pair} className="flex justify-between text-[10px] border-t border-border py-0.5">
                        <span className="text-muted">{pair}</span>
                        <span><span className="text-profit">{w}W</span> / <span className="text-loss">{l}L</span></span>
                      </div>
                    );
                  })}
                </div>
              </div>
              <div>
                <div className="text-muted text-[9px] uppercase mb-1">Skip Reasons</div>
                {(() => {
                  const reasons: Record<string, number> = {};
                  skippedTrades.forEach(t => {
                    const r = t.skip_reason?.split(" ")[0] || "unknown";
                    reasons[r] = (reasons[r] || 0) + 1;
                  });
                  return Object.entries(reasons).sort((a, b) => b[1] - a[1]).map(([reason, count]) => (
                    <span key={reason} className="inline-block text-[10px] font-mono bg-border px-2 py-0.5 rounded text-muted mr-1 mb-1">
                      {reason}: {count}
                    </span>
                  ));
                })()}
              </div>
            </div>
          )}
        </div>
      </div>

      <TradeDetail trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
    </div>
  );
}
