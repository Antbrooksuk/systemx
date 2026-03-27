"use client";

import { useState } from "react";
import { Trade } from "../lib/types";
import { ViewToggle } from "./ViewToggle";

interface TradeLogProps {
  trades: Trade[];
  equityCurve?: { trade: number; equity: number }[];
}

function formatPip(price: number | undefined | null, pair: string): string {
  if (price == null) return "—";
  const decimals = pair.endsWith("JPY") ? 3 : 5;
  return price.toFixed(decimals);
}

function formatDate(date: string | null) {
  if (!date) return "-";
  try {
    const d = new Date(date);
    return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", hour: "2-digit", minute: "2-digit" });
  } catch {
    return date.slice(0, 16);
  }
}

function formatTime(date: string | null) {
  if (!date) return "";
  try {
    const d = new Date(date);
    return d.toLocaleTimeString("en-GB", { hour: "2-digit", minute: "2-digit" });
  } catch {
    return "";
  }
}

function getSignalIcon(signal: string) {
  if (signal === "LONG") return "▲";
  if (signal === "SHORT") return "▼";
  return "—";
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

export function TradeDetail({ trade, onClose }: { trade: Trade | null; onClose: () => void }) {
  if (!trade) return null;

  const isSkip = trade.signal === "SKIP";
  const isFilled = !isSkip && trade.exit_reason !== "LIMIT";

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60" onClick={onClose}>
      <div className="bg-[#0a0a0a] border border-[#262626] rounded-lg p-6 w-full max-w-md mx-4" onClick={e => e.stopPropagation()}>
        <div className="flex items-center justify-between mb-4">
          <h3 className="text-lg font-bold font-mono">
            {trade.pair} <span className={getSignalColor(trade.signal)}>{trade.signal}</span>
          </h3>
          <button onClick={onClose} className="text-muted hover:text-fg text-xl leading-none">&times;</button>
        </div>

        <div className="space-y-3 text-sm font-mono">
          <div className="grid grid-cols-2 gap-x-4 gap-y-2">
            <div>
              <div className="text-[#525252] text-xs uppercase">Session</div>
              <div className="text-fg capitalize">{trade.session}</div>
            </div>
            <div>
              <div className="text-[#525252] text-xs uppercase">Date</div>
              <div className="text-fg">{formatDate(trade.date)}</div>
            </div>
          </div>

          {isSkip && (
            <div className="bg-[#141414] border border-[#262626] rounded p-3">
              <div className="text-[#525252] text-xs uppercase mb-1">Skip Reason</div>
              <div className="text-warn">{trade.exit_reason || trade.skip_reason || "No signal"}</div>
            </div>
          )}

          {!isSkip && (
            <>
              <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                <div>
                  <div className="text-[#525252] text-xs uppercase">Entry</div>
                  <div className="text-fg">{formatPip(trade.entry, trade.pair)}</div>
                </div>
                <div>
                  <div className="text-[#525252] text-xs uppercase">Exit</div>
                  <div className={getExitColor(trade.exit_reason)}>{trade.exit_reason}</div>
                </div>
                <div>
                  <div className="text-[#525252] text-xs uppercase">SL</div>
                  <div className="text-loss">{formatPip(trade.sl, trade.pair)}</div>
                </div>
                <div>
                  <div className="text-[#525252] text-xs uppercase">TP</div>
                  <div className="text-profit">{formatPip(trade.tp, trade.pair)}</div>
                </div>
                {trade.units != null && trade.units > 0 && (
                  <div>
                    <div className="text-[#525252] text-xs uppercase">Units</div>
                    <div className="text-fg">{trade.units.toLocaleString()}</div>
                  </div>
                )}
              </div>

              {isFilled && (
                <div className="grid grid-cols-2 gap-x-4 gap-y-2">
                  <div>
                    <div className="text-[#525252] text-xs uppercase">Exit Price</div>
                    <div className="text-fg">{formatPip(trade.exit_price, trade.pair)}</div>
                  </div>
                  <div>
                    <div className="text-[#525252] text-xs uppercase">Pips</div>
                    <div className={trade.pips > 0 ? "text-profit" : trade.pips < 0 ? "text-loss" : "text-muted"}>
                      {trade.pips > 0 ? "+" : ""}{trade.pips?.toFixed(1)}
                    </div>
                  </div>
                  <div>
                    <div className="text-[#525252] text-xs uppercase">P&L %</div>
                    <div className={getPnlColor(trade.pnl_pct, trade.exit_reason)}>
                      {trade.pnl_pct > 0 ? "+" : ""}{trade.pnl_pct.toFixed(4)}%
                    </div>
                  </div>
                  {trade.spread_pips != null && trade.spread_pips > 0 && (
                    <div>
                      <div className="text-[#525252] text-xs uppercase">Spread</div>
                      <div className="text-warn">{trade.spread_pips} pip</div>
                    </div>
                  )}
                </div>
              )}

              {!isFilled && trade.exit_reason === "LIMIT" && (
                <div className="bg-[#141414] border border-[#262626] rounded p-3">
                  <div className="text-[#525252] text-xs uppercase mb-1">Status</div>
                  <div className="text-orange-400">Limit order not reached</div>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  );
}

export function TradeLog({ trades, equityCurve }: TradeLogProps) {
  const [view, setView] = useState<"table" | "markdown">("table");
  const [selectedTrade, setSelectedTrade] = useState<Trade | null>(null);
  const [filter, setFilter] = useState<"all" | "filled" | "skip">("all");

  const sortedTrades = [...trades].sort((a, b) => {
    const dateA = a.date || "";
    const dateB = b.date || "";
    return dateB.localeCompare(dateA);
  });

  const filteredTrades = filter === "all"
    ? sortedTrades
    : filter === "filled"
    ? sortedTrades.filter(t => t.signal !== "SKIP" && t.exit_reason !== "LIMIT")
    : sortedTrades.filter(t => t.signal === "SKIP");

  const filledTrades = sortedTrades.filter(t => t.signal !== "SKIP" && t.filled !== false && t.exit_reason !== "LIMIT");
  const skippedTrades = sortedTrades.filter(t => t.signal === "SKIP");

  const markdownContent = `## Trade Log (${filledTrades.length} trades, ${skippedTrades.length} skips)

### Filled Trades
| # | Date | Pair | Session | Signal | Entry | Exit | Pips | P&L% |
|---|---|---|---|---|---|---|---|
${filledTrades.map((t, i) => {
  const exitEmoji = t.exit_reason === "TP" ? "✅" : t.exit_reason === "SL" ? "❌" : "⏱️";
  return `| ${i + 1} | ${formatDate(t.date)} | ${t.pair} | ${t.session} | ${getSignalIcon(t.signal)} ${t.signal} | ${formatPip(t.entry, t.pair)} | ${exitEmoji} ${t.exit_reason} | ${t.pips?.toFixed(1) || "0"} | ${t.pnl_pct > 0 ? "+" : ""}${t.pnl_pct.toFixed(2)}% |`;
}).join("\n")}

### Skips (${skippedTrades.length})
| Date | Pair | Session | Reason |
|---|---|---|---|
${skippedTrades.map(t => `| ${formatDate(t.date)} | ${t.pair} | ${t.session} | ${t.exit_reason || t.skip_reason || "-"} |`).join("\n")}`;

  return (
    <div className="bg-card border border-border rounded-lg p-4 h-[550px] overflow-hidden flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <div className="flex items-center gap-3">
          <div className="text-muted text-xs uppercase tracking-wider">
            Trade Log
          </div>
          <div className="flex gap-1">
            <button
              onClick={() => setFilter("all")}
              className={`px-2 py-0.5 text-xs rounded ${filter === "all" ? "bg-border text-fg" : "text-muted hover:text-fg"}`}
            >
              All ({sortedTrades.length})
            </button>
            <button
              onClick={() => setFilter("filled")}
              className={`px-2 py-0.5 text-xs rounded ${filter === "filled" ? "bg-border text-fg" : "text-muted hover:text-fg"}`}
            >
              Filled ({filledTrades.length})
            </button>
            <button
              onClick={() => setFilter("skip")}
              className={`px-2 py-0.5 text-xs rounded ${filter === "skip" ? "bg-border text-fg" : "text-muted hover:text-fg"}`}
            >
              Skip ({skippedTrades.length})
            </button>
          </div>
        </div>
        <ViewToggle view={view} onViewChange={setView} />
      </div>
      <div className="flex-1 overflow-y-auto">
        {view === "table" ? (
          <table className="w-full text-xs font-mono">
            <thead className="sticky top-0 bg-card border-b border-border z-10">
              <tr className="text-muted text-xs">
                <th className="text-left pb-2 pr-3">Time</th>
                <th className="text-left pb-2 pr-3">Pair</th>
                <th className="text-left pb-2 pr-3">Session</th>
                <th className="text-left pb-2 pr-3">Signal</th>
                <th className="text-right pb-2 pr-3">Entry</th>
                <th className="text-right pb-2 pr-3">Exit</th>
                <th className="text-right pb-2 pr-3">Pips</th>
                <th className="text-right pb-2">P&L%</th>
              </tr>
            </thead>
            <tbody>
              {filteredTrades.map((trade, idx) => {
                const isSkip = trade.signal === "SKIP";
                return (
                  <tr
                    key={idx}
                    className={`border-t border-border cursor-pointer hover:bg-border/30 transition-colors ${isSkip ? "opacity-50" : ""}`}
                    onClick={() => setSelectedTrade(trade)}
                  >
                    <td className="py-1.5 pr-3 text-muted whitespace-nowrap">
                      {formatTime(trade.date)}
                    </td>
                    <td className="py-1.5 pr-3 text-fg">{trade.pair}</td>
                    <td className="py-1.5 pr-3 text-muted capitalize">{trade.session}</td>
                    <td className={`py-1.5 pr-3 ${getSignalColor(trade.signal)}`}>
                      {isSkip ? "SKIP" : `${getSignalIcon(trade.signal)} ${trade.signal}`}
                    </td>
                    <td className="py-1.5 pr-3 text-right">
                      {isSkip ? "—" : formatPip(trade.entry, trade.pair)}
                    </td>
                    <td className={`py-1.5 pr-3 text-right ${isSkip ? "text-muted" : getExitColor(trade.exit_reason)}`}>
                      {isSkip ? (trade.exit_reason || trade.skip_reason || "—") : trade.exit_reason}
                    </td>
                    <td className={`py-1.5 pr-3 text-right ${isSkip ? "" : trade.pips > 0 ? "text-profit" : trade.pips < 0 ? "text-loss" : ""}`}>
                      {isSkip ? "—" : `${trade.pips > 0 ? "+" : ""}${trade.pips?.toFixed(1) || "0"}`}
                    </td>
                    <td className={`py-1.5 text-right ${isSkip ? "" : getPnlColor(trade.pnl_pct, trade.exit_reason)}`}>
                      {isSkip ? "—" : `${trade.pnl_pct > 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}%`}
                    </td>
                  </tr>
                );
              })}
              {filteredTrades.length === 0 && (
                <tr>
                  <td colSpan={8} className="text-center text-muted py-8">
                    No trades yet
                  </td>
                </tr>
              )}
            </tbody>
          </table>
        ) : (
          <div className="text-xs font-mono p-2">
            <pre className="whitespace-pre-wrap break-words">{markdownContent}</pre>
          </div>
        )}
      </div>
      <TradeDetail trade={selectedTrade} onClose={() => setSelectedTrade(null)} />
    </div>
  );
}
