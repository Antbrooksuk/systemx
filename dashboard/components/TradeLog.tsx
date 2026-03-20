"use client";

import { Trade } from "../lib/types";

interface TradeLogProps {
  trades: Trade[];
}

export function TradeLog({ trades }: TradeLogProps) {
  const sortedTrades = [...trades].reverse();

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

  const getPnlColor = (pnl: number) => {
    if (pnl > 0) return "text-profit";
    if (pnl < 0) return "text-loss";
    return "text-muted";
  };

  const formatDate = (date: string | null) => {
    if (!date) return "-";
    try {
      const d = new Date(date);
      return d.toLocaleDateString("en-GB", { day: "2-digit", month: "short" });
    } catch {
      return date.slice(0, 10);
    }
  };

  return (
    <div className="bg-card border border-border rounded-lg p-4 h-[500px] overflow-hidden flex flex-col">
      <div className="text-muted text-xs uppercase tracking-wider mb-2">Trade Log ({trades.length} trades)</div>
      <div className="flex-1 overflow-y-auto">
        <table className="w-full text-xs font-mono">
          <thead className="sticky top-0 bg-card border-b border-border z-10">
            <tr className="text-muted text-xs">
              <th className="text-left pb-2 pr-4">#</th>
              <th className="text-left pb-2 pr-4">Date</th>
              <th className="text-left pb-2 pr-4">Pair</th>
              <th className="text-left pb-2 pr-4">Session</th>
              <th className="text-left pb-2 pr-4">Signal</th>
              <th className="text-right pb-2 pr-4">Units</th>
              <th className="text-right pb-2 pr-4">Entry</th>
              <th className="text-right pb-2 pr-4">Exit</th>
              <th className="text-right pb-2 pr-4">Pips</th>
              <th className="text-right pb-2">P&L%</th>
            </tr>
          </thead>
          <tbody>
            {sortedTrades.map((trade, idx) => (
              <tr
                key={idx}
                className={`border-t border-border ${trade.exit_reason === "LIMIT" ? "opacity-50" : ""}`}
              >
                <td className="py-1.5 pr-4 text-muted">{trades.length - idx}</td>
                <td className="py-1.5 pr-4 text-muted">{formatDate(trade.date)}</td>
                <td className="py-1.5 pr-4 text-fg">{trade.pair}</td>
                <td className="py-1.5 pr-4 text-muted capitalize">{trade.session}</td>
                <td className={`py-1.5 pr-4 ${getSignalColor(trade.signal)}`}>
                  {trade.signal === "SKIP" ? "SKIP" : trade.signal}
                </td>
                <td className="py-1.5 pr-4 text-right text-muted">{trade.units ? `${trade.units}k` : "-"}</td>
                <td className="py-1.5 pr-4 text-right">{trade.entry?.toFixed(5) || "-"}</td>
                <td className={`py-1.5 pr-4 text-right ${getExitColor(trade.exit_reason)}`} title={trade.skip_reason || undefined}>
                  {trade.exit_reason === "SKIP" && trade.skip_reason ? (
                    <span className="text-warn">{trade.skip_reason}</span>
                  ) : (
                    trade.exit_reason
                  )}
                </td>
                <td className="py-1.5 pr-4 text-right">
                  <span className={trade.pips > 0 ? "text-profit" : trade.pips < 0 ? "text-loss" : ""}>
                    {trade.pips?.toFixed(1) || "0"}
                  </span>
                </td>
                <td className={`py-1.5 text-right ${getPnlColor(trade.pnl_pct)}`}>
                  {trade.pnl_pct > 0 ? "+" : ""}
                  {trade.pnl_pct.toFixed(2)}%
                </td>
              </tr>
            ))}
            {sortedTrades.length === 0 && (
              <tr>
                <td colSpan={10} className="text-center text-muted py-8">
                  No trades yet
                </td>
              </tr>
            )}
          </tbody>
        </table>
      </div>
    </div>
  );
}
