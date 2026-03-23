"use client";

import { useState } from "react";
import { Trade } from "../lib/types";
import { ViewToggle } from "./ViewToggle";

interface SessionBreakdownProps {
  trades: Trade[];
}

export function SessionBreakdown({ trades }: SessionBreakdownProps) {
  const [view, setView] = useState<"table" | "markdown">("table");

  const executedTrades = trades.filter(
    (t) => t.signal !== "SKIP" && t.filled !== false,
  );
  const skippedTrades = trades.filter((t) => t.signal === "SKIP");
  const unfilledTrades = trades.filter((t) => t.exit_reason === "LIMIT");

  const slOffsetPips = (trades[0] as any)?.sl_offset_pips;

  const londonTrades = executedTrades.filter((t) => t.session === "london");
  const nyTrades = executedTrades.filter((t) => t.session === "ny");

  const allPairs = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"];

  const getSessionStats = (sessionTrades: Trade[]) => {
    const wins = sessionTrades.filter((t) => (t.pnl_pct ?? 0) > 0);
    const losses = sessionTrades.filter((t) => (t.pnl_pct ?? 0) < 0);
    
    // Find biggest win and loss by P&L% directly
    const maxWin = wins.reduce((max, t) => (t.pnl_pct ?? 0) > (max.pnl_pct ?? -1) ? t : max, { pnl_pct: -Infinity });
    const maxLoss = losses.reduce((min, t) => (t.pnl_pct ?? 0) < (min.pnl_pct ?? Infinity) ? t : min, { pnl_pct: Infinity });
    
    // Use starting capital of £2000 for GBP calculation
    const STARTING_CAPITAL = 2000;
    
    // Calculate GBP from P&L% directly (accounts for compounding)
    const maxWinGBP = maxWin.pnl_pct / 100 * STARTING_CAPITAL;
    const maxLossGBP = Math.abs(maxLoss.pnl_pct / 100 * STARTING_CAPITAL);
    
    const wr = sessionTrades.length
      ? ((wins.length / sessionTrades.length) * 100).toFixed(1)
      : "0.0";
    return {
      total: sessionTrades.length,
      wins: wins.length,
      losses: losses.length,
      wr,
      maxWinGBP,
      maxLossGBP,
    };
  };

  const getPairStats = (pair: string) => {
    const pairTrades = executedTrades.filter((t) => t.pair === pair);
    const wins = pairTrades.filter((t) => (t.pnl_pct ?? 0) > 0).length;
    const losses = pairTrades.filter((t) => (t.pnl_pct ?? 0) < 0).length;
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

  const skipReasonsSection = skipReasons.length > 0 ? `## Skip Reasons

${skipReasons.map(([reason, count]) => `- ${reason}: ${count}`).join("\n")}` : "";

  const unfilledSection = unfilledTrades.length > 0 ? `## Unfilled

${unfilledTrades.length} limit orders not reached` : "";

  const markdownStats = `## Performance Metrics

| Metric | Value |
|---|---|
| Avg Pips/Trade | ${avgPips} |
| Avg Spread | ${avgSpread} pip |
| Avg P&L% | ${avgPnl >= 0 ? "+" : ""}${avgPnl.toFixed(2)}% |

## By Session

| Session | Trades | WR | Biggest Win | Biggest Loss |
|---|---|---|---|---|
| London | ${london.wins}W/${london.losses}L | ${london.wr}% | +£${london.maxWinGBP.toFixed(2)} | -£${london.maxLossGBP.toFixed(2)} |
| New York | ${ny.wins}W/${ny.losses}L | ${ny.wr}% | +£${ny.maxWinGBP.toFixed(2)} | -£${ny.maxLossGBP.toFixed(2)} |

## By Pair

${allPairs.map((pair) => {
  const s = getPairStats(pair);
  return `| ${pair} | ${s.wins}W/${s.losses}L | ${s.wr}% |`;
}).join("\n")}

${skipReasonsSection}

${unfilledSection}`;

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-muted text-xs uppercase tracking-wider">
          Breakdown
          {slOffsetPips && (
            <span className="ml-4 text-profit">SL: {slOffsetPips} pips</span>
          )}
        </div>
        <ViewToggle view={view} onViewChange={setView} />
      </div>

      {view === "table" && (
        <>
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

          <div className="mb-4">
            <div className="text-sm font-medium mb-2">By Session</div>
            <table className="w-full text-sm font-mono">
              <thead>
                <tr className="text-muted text-xs">
                  <th className="text-left pb-1">Session</th>
                  <th className="text-right pb-1">Trades</th>
                  <th className="text-right pb-1">WR</th>
                  <th className="text-right pb-1">Biggest Win</th>
                  <th className="text-right pb-1">Biggest Loss</th>
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
                    <td className="py-1 text-right text-profit">
                      +£{s.maxWinGBP.toFixed(2)}
                    </td>
                    <td className="py-1 text-right text-loss">
                      -£{s.maxLossGBP.toFixed(2)}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>

          <div className="">
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
            <div className="mt-4 pt-3">
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
        </>
      )}

      {view === "markdown" && (
        <div className="prose prose prose-sm max-w-none">
          <div className="text-xs font-mono">
            <pre className="whitespace-pre-wrap break-words bg-card/50 p-4 rounded">{markdownStats}</pre>
          </div>
        </div>
      )}
    </div>
  );
}
