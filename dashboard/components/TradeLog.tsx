"use client";

import { useState } from "react";
import { Trade } from "../lib/types";
import { ViewToggle } from "./ViewToggle";

interface TradeLogProps {
  trades: Trade[];
  equityCurve?: { trade: number; equity: number }[];
}

export function TradeLog({ trades, equityCurve }: TradeLogProps) {
  const [view, setView] = useState<"table" | "markdown">("table");

  // Filter to filled trades only and sort chronologically
  const filledTrades = [...trades].filter(t => t.signal !== "SKIP" && t.filled !== false)
    .sort((a, b) => {
      const dateA = a.date || "";
      const dateB = b.date || "";
      return dateA.localeCompare(dateB);
    });

  // Build capital before map from filled trades (indices 0 to filledTrades.length-1)
  const capitalBeforeTrade: Record<number, number> = {};
  if (equityCurve) {
    for (let i = 0; i < equityCurve.length && i < filledTrades.length; i++) {
      capitalBeforeTrade[i + 1] = equityCurve[i]?.equity || 2000;
    }
  }

  const getRiskGBP = (trade: Trade, tradeIndex: number): string => {
    // For filled trades, get capital before this trade
    const capitalBefore = capitalBeforeTrade[tradeIndex] || 2000;
    const riskGBP = capitalBefore * 0.01;
    
    return `£${riskGBP.toFixed(2)}`;
  };

  const getPnlGBP = (trade: Trade, tradeIndex: number): string => {
    // For filled trades, get capital before this trade
    const capitalBefore = capitalBeforeTrade[tradeIndex] || 2000;
    
    // Calculate P&L in GBP based on actual account change
    const pnlGBP = (trade.pnl_pct / 100) * capitalBefore;

    return `£${pnlGBP.toFixed(2)}`;
  };

  const getSignalColor = (signal: string) => {
    if (signal === "LONG") return "text-profit";
    if (signal === "SHORT") return "text-loss";
    return "text-warn";
  };

  const getExitColor = (reason: string) => {
    if (reason === "TP") return "text-profit";
    if (reason === "SL") return "text-loss";
    if (reason === "TIME_STOP") return "text-warn";
    if (reason === "LIMIT") return "text-orange-400";
    return "text-muted";
  };

  const getPnlColor = (pnl: number, exitReason: string) => {
    if (exitReason === "TP") return "text-profit";
    if (exitReason === "SL") return "text-loss";
    if (exitReason === "TIME_STOP") {
      const sign = Math.sign(pnl);
      if (sign > 0) return "text-profit";
      if (sign < 0) return "text-loss";
    }
    return "text-muted";
  };

  const formatDate = (date: string | null) => {
    if (!date) return "-";
    try {
      const d = new Date(date);
      return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short", year: "numeric" });
    } catch {
      return date.slice(0, 10);
    }
  };

  const markdownContent = `| # | Date | Pair | Session | Signal | Risk (£) | Entry | Exit | Pips | P&L% | P&L (£) |
|---|---|---|---|---|---|---|---|---|---|
${filledTrades.map((trade, idx) => {
  const tradeIndex = idx + 1;
  const riskColor = trade.signal === "LONG" ? "🟢" : trade.signal === "SHORT" ? "🔴" : "⚪";
  const exitEmoji = trade.exit_reason === "TP" ? "✅" : trade.exit_reason === "SL" ? "❌" : trade.exit_reason === "TIME_STOP" ? "⏱️" : "⏸️";
  return `| ${tradeIndex} | ${formatDate(trade.date)} | ${trade.pair} | ${trade.session} | ${riskColor} ${trade.signal} | ${getRiskGBP(trade, tradeIndex)} | ${trade.entry?.toFixed(5) || "-"} | ${exitEmoji} ${trade.exit_reason} | ${trade.pips?.toFixed(1) || "0"} | ${trade.pnl_pct > 0 ? "+" : ""}${trade.pnl_pct.toFixed(2)}% | ${getPnlGBP(trade, tradeIndex)} |`;
}).join("\n")}`;

  return (
    <div className="bg-card border border-border rounded-lg p-4 h-[550px] overflow-hidden flex flex-col">
      <div className="flex items-center justify-between mb-2">
        <div className="text-muted text-xs uppercase tracking-wider">
          Trade Log ({filledTrades.length} trades)
        </div>
        <ViewToggle view={view} onViewChange={setView} />
      </div>
      <div className="flex-1 overflow-y-auto">
        {view === "table" ? (
          <table className="w-full text-xs font-mono">
            <thead className="sticky top-0 bg-card border-b border-border z-10">
              <tr className="text-muted text-xs">
                <th className="text-left pb-2 pr-4">#</th>
                <th className="text-left pb-2 pr-4">Date</th>
                <th className="text-left pb-2 pr-4">Pair</th>
                <th className="text-left pb-2 pr-4">Session</th>
                <th className="text-left pb-2 pr-4">Signal</th>
                <th className="text-right pb-2 pr-4">Risk (£)</th>
                <th className="text-right pb-2 pr-4">Entry</th>
                <th className="text-right pb-2 pr-4">Exit</th>
                <th className="text-right pb-2 pr-4">Pips</th>
                <th className="text-right pb-2 pr-4">P&L%</th>
                <th className="text-right pb-2 pr-4">P&L (£)</th>
              </tr>
            </thead>
            <tbody>
              {filledTrades.map((trade, idx) => {
                const tradeIndex = idx + 1;
                return (
                <tr
                  key={idx}
                  className={`border-t border-border ${trade.exit_reason === "LIMIT" ? "opacity-50" : ""}`}
                >
                  <td className="py-1.5 pr-4 text-muted">{tradeIndex}</td>
                  <td className="py-1.5 pr-4 text-muted">
                    {formatDate(trade.date)}
                  </td>
                  <td className="py-1.5 pr-4 text-fg">{trade.pair}</td>
                  <td className="py-1.5 pr-4 text-muted capitalize">
                    {trade.session}
                  </td>
                  <td className={`py-1.5 pr-4 ${getSignalColor(trade.signal)}`}>
                    {trade.signal}
                  </td>
                  <td className="py-1.5 pr-4 text-right text-muted">
                    {getRiskGBP(trade, tradeIndex)}
                  </td>
                  <td className="py-1.5 pr-4 text-right">
                    {trade.entry?.toFixed(5) || "-"}
                  </td>
                  <td
                    className={`py-1.5 pr-4 text-right ${getExitColor(trade.exit_reason)}`}
                    title={trade.skip_reason || undefined}
                    >
                    {trade.exit_reason}
                  </td>
                  <td className="py-1.5 pr-4 text-right">
                    <span
                      className={
                        trade.pips > 0
                          ? "text-profit"
                          : trade.pips < 0
                            ? "text-loss"
                            : ""
                      }
                    >
                      {trade.pips?.toFixed(1) || "0"}
                    </span>
                  </td>
                  <td
                    className={`py-1.5 pr-4 text-right ${getPnlColor(trade.pnl_pct, trade.exit_reason)}`}
                     >
                    {trade.pnl_pct > 0 ? "+" : ""}
                    {trade.pnl_pct.toFixed(2)}%
                  </td>
                  <td
                    className={`py-1.5 pr-4 text-right ${getPnlColor(trade.pnl_pct, trade.exit_reason)}`}
                     >
                    {getPnlGBP(trade, tradeIndex)}
                  </td>
                </tr>
              );
              })}
              {filledTrades.length === 0 && (
                <tr>
                  <td colSpan={11} className="text-center text-muted py-8">
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
    </div>
  );
}
