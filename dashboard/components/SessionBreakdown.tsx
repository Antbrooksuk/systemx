"use client";

import { Trade } from "../lib/types";

interface SessionBreakdownProps {
  trades: Trade[];
}

export function SessionBreakdown({ trades }: SessionBreakdownProps) {
  const executedTrades = trades.filter((t) => t.signal !== "SKIP" && t.filled !== false);
  const skippedTrades = trades.filter((t) => t.signal === "SKIP");
  const unfilledTrades = trades.filter((t) => t.exit_reason === "LIMIT");

  const londonTrades = executedTrades.filter((t) => t.session === "london");
  const nyTrades = executedTrades.filter((t) => t.session === "ny");

  const allPairs = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"];

  const getSessionStats = (sessionTrades: Trade[]) => {
    const wins = sessionTrades.filter((t) => t.exit_reason === "TP").length;
    const losses = sessionTrades.filter(
      (t) => t.exit_reason !== "TP" && t.exit_reason !== "NONE",
    ).length;
    const wr = sessionTrades.length
      ? ((wins / sessionTrades.length) * 100).toFixed(1)
      : "0.0";
    return { total: sessionTrades.length, wins, losses, wr };
  };

  const getPairStats = (pair: string) => {
    const pairTrades = executedTrades.filter((t) => t.pair === pair);
    const wins = pairTrades.filter((t) => t.exit_reason === "TP").length;
    const losses = pairTrades.filter(
      (t) => t.exit_reason !== "TP" && t.exit_reason !== "NONE",
    ).length;
    const wr = pairTrades.length
      ? ((wins / pairTrades.length) * 100).toFixed(1)
      : "0.0";
    return { total: pairTrades.length, wins, losses, wr };
  };

  const london = getSessionStats(londonTrades);
  const ny = getSessionStats(nyTrades);

  const avgPips = executedTrades.length
    ? (
        executedTrades.reduce((sum, t) => sum + t.pips, 0) /
        executedTrades.length
      ).toFixed(2)
    : "0.00";
  const avgSpread = executedTrades.length
    ? (
        executedTrades.reduce((sum, t) => sum + (t.spread_pips || 0), 0) /
        executedTrades.length
      ).toFixed(1)
    : "0.0";
  const avgPnl = executedTrades.length
    ? executedTrades.reduce((sum, t) => sum + t.pnl_pct, 0) /
      executedTrades.length
    : 0;

  const skipReasons = Object.entries(
    skippedTrades.reduce(
      (acc, t) => {
        const reason = t.skip_reason?.split(" ")[0] || "unknown";
        acc[reason] = (acc[reason] || 0) + 1;
        return acc;
      },
      {} as Record<string, number>,
    ),
  )
    .sort((a, b) => b[1] - a[1])
    .slice(0, 3);

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-muted text-xs uppercase tracking-wider mb-3">
        Breakdown
      </div>

      <div className="grid grid-cols-3 gap-4 mb-4">
        <div className="text-center">
          <div className="text-xs text-muted mb-1">Avg Pips/Trade</div>
          <div
            className={`text-lg font-mono font-bold ${parseFloat(avgPips) >= 0 ? "text-profit" : "text-loss"}`}
          >
            {avgPips}
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-muted mb-1">Avg Spread</div>
          <div className="text-lg font-mono font-bold text-warn">
            {avgSpread} pip
          </div>
        </div>
        <div className="text-center">
          <div className="text-xs text-muted mb-1">Avg P&L%</div>
          <div
            className={`text-lg font-mono font-bold ${avgPnl >= 0 ? "text-profit" : "text-loss"}`}
          >
            {avgPnl >= 0 ? "+" : ""}
            {avgPnl.toFixed(2)}%
          </div>
        </div>
      </div>

      <div className="grid grid-cols-1 sm:grid-cols-3 gap-4">
        <div>
          <div className="text-sm font-medium mb-2">By Session</div>
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="text-muted text-xs">
                <th className="text-left pb-1">Session</th>
                <th className="text-right pb-1">Trades</th>
                <th className="text-right pb-1">WR</th>
              </tr>
            </thead>
            <tbody>
              {[
                { label: "London", s: london },
                { label: "New York", s: ny },
              ].map(({ label, s }) => (
                <tr key={label} className="border-t border-border">
                  <td className="py-1 text-muted">{label}</td>
                  <td className="py-1 text-right">
                    <span className="text-profit">{s.wins}W</span>
                    <span className="text-muted"> / </span>
                    <span className="text-loss">{s.losses}L</span>
                  </td>
                  <td className="py-1 text-right">{s.wr}%</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        <div className="sm:col-span-2">
          <div className="text-sm font-medium mb-2">By Pair</div>
          <table className="w-full text-sm font-mono">
            <thead>
              <tr className="text-muted text-xs">
                <th className="text-left pb-1">Pair</th>
                <th className="text-right pb-1">Trades</th>
                <th className="text-right pb-1">WR</th>
              </tr>
            </thead>
            <tbody>
              {allPairs.map((pair) => {
                const s = getPairStats(pair);
                return (
                  <tr key={pair} className="border-t border-border">
                    <td className="py-1 text-muted">{pair}</td>
                    <td className="py-1 text-right">
                      <span className="text-profit">{s.wins}W</span>
                      <span className="text-muted"> / </span>
                      <span className="text-loss">{s.losses}L</span>
                    </td>
                    <td className="py-1 text-right">{s.wr}%</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </div>

      {(skipReasons.length > 0 || unfilledTrades.length > 0) && (
        <div className="mt-4 pt-3 border-t border-border">
          {unfilledTrades.length > 0 && (
            <div className="mb-2 text-xs font-mono">
              <span className="text-orange-400">Unfilled: </span>
              <span className="text-muted">
                {unfilledTrades.length} limit orders not reached
              </span>
            </div>
          )}
          {skipReasons.length > 0 && (
            <div className="flex flex-wrap gap-2">
              {skipReasons.map(([reason, count]) => (
                <span
                  key={reason}
                  className="text-xs font-mono bg-border px-2 py-1 rounded text-muted"
                >
                  {reason}: {count}
                </span>
              ))}
            </div>
          )}
        </div>
      )}
    </div>
  );
}
