"use client";

import { useState, useEffect } from "react";
import { useLive, LiveOrder, LiveTrade, HistoricalTrade, LiveSignalResult } from "../../hooks/useLive";
import { StatCard } from "../../components/StatCard";
import { TradeLog } from "../../components/TradeLog";
import { SessionBreakdown } from "../../components/SessionBreakdown";
import { EquityCurve } from "../../components/EquityCurve";
import { EquityPoint, State } from "../../lib/types";
import { runBacktest } from "../../lib/api";

function formatTime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  const s = Math.floor(seconds % 60);
  if (h > 0) return `${h}h ${m}m`;
  if (m > 0) return `${m}m ${s}s`;
  return `${s}s`;
}

function formatUptime(seconds: number): string {
  const h = Math.floor(seconds / 3600);
  const m = Math.floor((seconds % 3600) / 60);
  return `${h}h ${m}m`;
}

function formatPip(price: number | undefined | null, pair: string): string {
  if (price == null) return "—";
  const decimals = pair.endsWith("JPY") ? 3 : 5;
  return price.toFixed(decimals);
}

function formatMoney(value: number | undefined | null, currency: string): string {
  if (value == null) return "—";
  const sign = value >= 0 ? "+" : "";
  return `${sign}£${(value ?? 0).toFixed(2)}`;
}

function calculateEVData(historicalTrades: HistoricalTrade[], startingBalance: number) {
  if (historicalTrades.length === 0) return [];

  const filledTrades = historicalTrades.filter(t => t.exit_reason !== "SKIP" && t.exit_time);
  
  const sortedTrades = filledTrades.sort((a, b) => 
    new Date(a.exit_time || a.entry_time).getTime() - new Date(b.exit_time || b.entry_time).getTime()
  );

  const avgWinPnl = sortedTrades
    .filter(t => t.exit_reason === "TP")
    .reduce((sum, t) => sum + t.pnl_pct, 0) / 
    (sortedTrades.filter(t => t.exit_reason === "TP").length || 1);
  
  const avgLossPnl = sortedTrades
    .filter(t => t.exit_reason === "SL")
    .reduce((sum, t) => sum + t.pnl_pct, 0) / 
    (sortedTrades.filter(t => t.exit_reason === "SL").length || 1);
  
  const winRate = sortedTrades.filter(t => t.exit_reason === "TP").length / (sortedTrades.length || 1);
  const evPct = (winRate * avgWinPnl) + ((1 - winRate) * avgLossPnl);
  
  const evData: { trade: number; ev: number; upper: number; lower: number }[] = [
    { trade: 0, ev: startingBalance, upper: startingBalance, lower: startingBalance }
  ];

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

    evData.push({
      trade: index + 1,
      ev: cumulativeEV,
      upper: upperBound,
      lower: Math.max(lowerBound, 0),
    });
  });

  return evData;
}

function SessionPanel({ session, candleCountdown }: { session: any; candleCountdown: number | null | undefined }) {
  if (!session) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="text-muted text-xs uppercase tracking-wider mb-1">Session</div>
        <div className="text-warn text-lg font-mono">Outside trading hours</div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-muted text-xs uppercase tracking-wider mb-1">Session</div>
      <div className="text-profit text-lg font-mono font-bold">{session.name}</div>
      <div className="text-muted text-xs mt-1">
        {session.pairs.join(", ")}
      </div>
      <div className="grid grid-cols-2 gap-2 mt-3">
        <div>
          <div className="text-muted text-xs">Ends in</div>
          <div className="text-fg font-mono">{formatTime(session.seconds_remaining)}</div>
        </div>
        <div>
          <div className="text-muted text-xs">Next candle</div>
          <div className="text-fg font-mono">{candleCountdown}s</div>
        </div>
      </div>
    </div>
  );
}

function SignalPanel({ signal }: { signal: any }) {
  if (!signal) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="text-muted text-xs uppercase tracking-wider mb-1">Signal</div>
        <div className="text-muted text-lg font-mono">—</div>
      </div>
    );
  }

  if (signal.signal === "SKIP" || signal.signal === "ERROR") {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="text-muted text-xs uppercase tracking-wider mb-1">Signal</div>
        <div className="text-warn font-mono">{signal.signal}</div>
        <div className="text-muted text-xs mt-1">{signal.reason || signal.error}</div>
      </div>
    );
  }

  const isLong = signal.direction === "LONG";
  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-muted text-xs uppercase tracking-wider mb-1">Signal</div>
      <div className={`text-lg font-mono font-bold ${isLong ? "text-profit" : "text-loss"}`}>
        {signal.signal} {signal.pair}
      </div>
      <div className="grid grid-cols-2 gap-2 mt-3 text-xs font-mono">
        <div>
          <span className="text-muted">Entry </span>
          <span className="text-fg">{formatPip(signal.entry, signal.pair)}</span>
        </div>
        <div>
          <span className="text-muted">SL </span>
          <span className="text-loss">{formatPip(signal.sl, signal.pair)}</span>
        </div>
        <div>
          <span className="text-muted">TP </span>
          <span className="text-profit">{formatPip(signal.tp, signal.pair)}</span>
        </div>
        <div>
          <span className="text-muted">RR </span>
          <span className="text-fg">{signal.rr?.toFixed(1)}</span>
        </div>
      </div>
    </div>
  );
}

function OrdersTable({ orders }: { orders: LiveOrder[] }) {
  if (orders.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="text-muted text-xs uppercase tracking-wider mb-3">Active Orders</div>
        <div className="text-center text-muted py-4 text-sm">No pending orders</div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-muted text-xs uppercase tracking-wider mb-3">Active Orders ({orders.length})</div>
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="text-muted border-b border-border">
            <th className="text-left pb-2 pr-3">Pair</th>
            <th className="text-left pb-2 pr-3">Dir</th>
            <th className="text-right pb-2 pr-3">Type</th>
            <th className="text-right pb-2 pr-3">Price</th>
            <th className="text-right pb-2 pr-3">SL</th>
            <th className="text-right pb-2">TP</th>
          </tr>
        </thead>
        <tbody>
          {orders.map((o) => (
            <tr key={o.id} className="border-t border-border">
              <td className="py-2 pr-3 text-fg">{o.pair ?? "—"}</td>
              <td className={`py-2 pr-3 ${(o.direction ?? "") === "LONG" ? "text-profit" : "text-loss"}`}>
                {(o.direction ?? "—").toUpperCase()}
              </td>
              <td className="py-2 pr-3 text-right text-warn">{o.type ?? "LIMIT"}</td>
              <td className="py-2 pr-3 text-right">{formatPip(o.price, o.pair ?? "EURUSD")}</td>
              <td className="py-2 pr-3 text-right text-loss">{formatPip(o.sl, o.pair ?? "EURUSD")}</td>
              <td className="py-2 pr-3 text-right text-profit">{formatPip(o.tp, o.pair ?? "EURUSD")}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function TradesTable({ trades }: { trades: LiveTrade[] }) {
  if (trades.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="text-muted text-xs uppercase tracking-wider mb-3">Open Trades</div>
        <div className="text-center text-muted py-4 text-sm">No open trades</div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-muted text-xs uppercase tracking-wider mb-3">Open Trades ({trades.length})</div>
      <table className="w-full text-xs font-mono">
        <thead>
          <tr className="text-muted border-b border-border">
            <th className="text-left pb-2 pr-3">Pair</th>
            <th className="text-left pb-2 pr-3">Dir</th>
            <th className="text-right pb-2 pr-3">Units</th>
            <th className="text-right pb-2 pr-3">Entry</th>
            <th className="text-right pb-2 pr-3">Current</th>
            <th className="text-right pb-2">P&L</th>
          </tr>
        </thead>
        <tbody>
          {trades.map((t) => (
            <tr key={t.id} className="border-t border-border">
              <td className="py-2 pr-3 text-fg">{t.pair}</td>
              <td className={`py-2 pr-3 ${(t.direction ?? "") === "LONG" ? "text-profit" : "text-loss"}`}>
                {(t.direction ?? "—").toUpperCase()}
              </td>
              <td className="py-2 pr-3 text-right">{t.units}</td>
              <td className="py-2 pr-3 text-right">{formatPip(t.price, t.pair)}</td>
              <td className="py-2 pr-3 text-right">{formatPip(t.current_price, t.pair)}</td>
              <td className={`py-2 text-right ${(t.unrealized_pl ?? 0) >= 0 ? "text-profit" : "text-loss"}`}>
                {(t.unrealized_pl ?? 0) >= 0 ? "+" : ""}{(t.unrealized_pl ?? 0).toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

function SignalsTable({ signals, session }: { signals: LiveSignalResult[]; session: string | undefined }) {
  const sessionSignals = signals.filter(s => s.session === session);
  if (sessionSignals.length === 0) {
    return (
      <div className="bg-card border border-border rounded-lg p-4">
        <div className="text-muted text-xs uppercase tracking-wider mb-3">Signal Decisions</div>
        <div className="text-center text-muted py-4 text-sm">No signals checked yet</div>
      </div>
    );
  }

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="text-muted text-xs uppercase tracking-wider mb-3">Signal Decisions ({session || "current"})</div>
      <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 gap-2">
        {sessionSignals.map((s, i) => {
          const isTrade = s.signal === "LONG" || s.signal === "SHORT";
          return (
            <div key={i} className={`border border-border rounded px-3 py-2 ${isTrade ? "border-profit/40 bg-profit/5" : "opacity-70"}`}>
              <div className="flex items-center justify-between">
                <span className="font-mono text-sm font-bold">{s.pair}</span>
                <span className={`text-xs font-mono ${isTrade ? "text-profit" : "text-muted"}`}>
                  {s.signal}
                </span>
              </div>
              {s.reason && (
                <div className="text-xs text-warn mt-1 truncate" title={s.reason}>
                  {s.reason}
                </div>
              )}
            </div>
          );
        })}
      </div>
    </div>
  );
}

function calculateDrawdown(equityCurve: { equity: number }[]): number {
  if (equityCurve.length === 0) return 0;
  
  let maxEquity = equityCurve[0].equity;
  let maxDrawdown = 0;
  
  for (const point of equityCurve) {
    if (point.equity > maxEquity) {
      maxEquity = point.equity;
    }
    const drawdown = ((maxEquity - point.equity) / maxEquity) * 100;
    if (drawdown > maxDrawdown) {
      maxDrawdown = drawdown;
    }
  }
  
  return maxDrawdown;
}

function buildEquityCurve(historicalTrades: HistoricalTrade[], startingBalance: number): { trade: number; equity: number; date: string }[] {
  const filledTrades = historicalTrades.filter(t => t.exit_reason !== "SKIP" && t.exit_time);
  
  const equityCurve: { trade: number; equity: number; date: string }[] = [
    { trade: 0, equity: startingBalance, date: "" }
  ];
  
  let currentEquity = startingBalance;
  
  filledTrades.sort((a, b) => new Date(a.exit_time || a.entry_time).getTime() - new Date(b.exit_time || b.entry_time).getTime());
  
  filledTrades.forEach((trade, index) => {
    const pnlAmount = (trade.pnl_pct / 100) * currentEquity;
    currentEquity += pnlAmount;
    
    equityCurve.push({
      trade: index + 1,
      equity: currentEquity,
      date: trade.exit_time || trade.entry_time
    });
  });
  
  return equityCurve;
}

function LogsPanel({ logs }: { logs: { time: string; level: string; message: string }[] }) {
  const [filter, setFilter] = useState<"all" | "ERROR" | "WARNING">("all");
  
  const filteredLogs = logs.filter(l => 
    filter === "all" || l.level === filter || (filter === "WARNING" && l.level === "WARNING")
  );
  
  const errorLogs = logs.filter(l => l.level === "ERROR");
  const warnLogs = logs.filter(l => l.level === "WARNING");

  return (
    <div className="bg-card border border-border rounded-lg p-4">
      <div className="flex items-center justify-between mb-3">
        <div className="text-muted text-xs uppercase tracking-wider">
          Bot Logs {errorLogs.length > 0 && <span className="text-loss">({errorLogs.length} errors)</span>}
        </div>
        <div className="flex gap-1">
          <button
            onClick={() => setFilter("all")}
            className={`px-2 py-1 text-xs rounded ${filter === "all" ? "bg-border text-fg" : "text-muted hover:text-fg"}`}
          >
            All
          </button>
          <button
            onClick={() => setFilter("ERROR")}
            className={`px-2 py-1 text-xs rounded ${filter === "ERROR" ? "bg-loss/20 text-loss" : "text-muted hover:text-loss"}`}
          >
            Errors ({errorLogs.length})
          </button>
          <button
            onClick={() => setFilter("WARNING")}
            className={`px-2 py-1 text-xs rounded ${filter === "WARNING" ? "bg-warn/20 text-warn" : "text-muted hover:text-warn"}`}
          >
            Warnings ({warnLogs.length})
          </button>
        </div>
      </div>
      <div className="h-48 overflow-y-auto font-mono text-xs space-y-1">
        {filteredLogs.length === 0 ? (
          <div className="text-muted text-center py-4">No logs yet</div>
        ) : (
          filteredLogs.map((log, i) => (
            <div key={i} className={`flex gap-2 ${
              log.level === "ERROR" ? "text-loss" : 
              log.level === "WARNING" ? "text-warn" : 
              log.level === "INFO" ? "text-fg" : "text-muted"
            }`}>
              <span className="text-muted shrink-0">{log.time}</span>
              <span className={`shrink-0 w-14 ${
                log.level === "ERROR" ? "text-loss font-bold" : 
                log.level === "WARNING" ? "text-warn" : 
                "text-muted"
              }`}>{log.level}</span>
              <span className="truncate" title={log.message}>{log.message}</span>
            </div>
          ))
        )}
      </div>
    </div>
  );
}

export default function LivePage() {
  const { state, error, logs } = useLive();
  const [showEV, setShowEV] = useState(false);
  const [backtestState, setBacktestState] = useState<State | null>(null);
  const [loadingBacktest, setLoadingBacktest] = useState(false);
  const isConnected = !!state;

  useEffect(() => {
    const loadBacktestData = async () => {
      setLoadingBacktest(true);
      try {
        const result = await runBacktest(2026, "base", 2000, 0.01);
        setBacktestState(result as State);
      } catch (err) {
        console.error("Failed to load backtest data:", err);
      } finally {
        setLoadingBacktest(false);
      }
    };
    loadBacktestData();
  }, []);
  
  const currentSession = state?.session?.name;
  const STARTING_BALANCE = 2000;
  
  const allTradeEvents = (state?.historicalTrades || []).map((t: HistoricalTrade) => ({
    date: t.exit_time || t.entry_time,
    pair: t.pair,
    session: t.session,
    signal: t.direction || (t.exit_reason === "SKIP" ? "SKIP" : ""),
    skip_reason: t.exit_reason === "SKIP" ? (t.sl > 0 ? "" : "") : null,
    entry: t.entry,
    sl: t.sl,
    tp: t.tp,
    exit_price: t.exit_price,
    exit_reason: t.exit_reason,
    pips: t.pips,
    pnl_pct: t.pnl_pct,
    spread_pips: 0,
    filled: t.exit_reason !== "SKIP",
    units: t.units,
    sl_offset_pips: 3,
  }));
  
  const equityCurveData = buildEquityCurve(state?.historicalTrades || [], STARTING_BALANCE);
  const evData = calculateEVData(state?.historicalTrades || [], STARTING_BALANCE);
  const currentEquity = equityCurveData[equityCurveData.length - 1]?.equity ?? STARTING_BALANCE;
  const totalPnl = currentEquity - STARTING_BALANCE;
  const totalPnlPct = (totalPnl / STARTING_BALANCE) * 100;
  
  const filledTrades = allTradeEvents.filter(t => t.filled);
  const wins = filledTrades.filter(t => 
    t.exit_reason === "TP" || (t.exit_reason === "TIME_STOP" && Math.sign(t.pnl_pct ?? 0) > 0)
  ).length;
  const losses = filledTrades.filter(t => 
    t.exit_reason === "SL" || (t.exit_reason === "TIME_STOP" && Math.sign(t.pnl_pct ?? 0) < 0)
  ).length;
  const totalTrades = filledTrades.length;
  const winRate = totalTrades > 0 ? (wins / totalTrades) * 100 : 0;
  const maxDrawdown = calculateDrawdown(equityCurveData);
  
  const wrColor = winRate >= 71 ? "profit" : winRate >= 60 ? "warn" : "loss";
  const ddColor = maxDrawdown < 15 ? "profit" : "loss";

  const backtestWinRate = backtestState?.win_rate ?? 0;
  const backtestWRDiff = winRate - backtestWinRate;
  const wrDiffColor = backtestWRDiff > 0 ? "text-profit" : backtestWRDiff < 0 ? "text-loss" : "text-muted";
  const backtestROIPct = backtestState?.roi ?? 0;
  const roiDiffColor = totalPnlPct > backtestROIPct ? "text-profit" : totalPnlPct < backtestROIPct ? "text-loss" : "text-muted";

  const acc = state?.account;
  const pnl = acc ? acc.equity - acc.balance : 0;
  const sessionSeconds = state?.session?.seconds_remaining ?? 0;

  if (error) {
    return (
      <div className="min-h-screen p-4 md:p-6">
        <div className="bg-card border border-loss rounded-lg p-6 text-center">
          <div className="text-loss font-bold mb-2">Connection Failed</div>
          <div className="text-muted text-sm">{error}</div>
          <div className="text-muted text-xs mt-2">Make sure bot is running on port 8001</div>
        </div>
      </div>
    );
  }
  
  return (
    <div className="min-h-screen p-4 md:p-6">
      <div className="space-y-4">
        <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              SYSTEM-X
              <span className="text-xs px-2 py-0.5 bg-profit/20 text-profit rounded">LIVE</span>
            </h1>
            <p className="text-muted text-sm">
              Mode X-Base · Bot uptime: {formatUptime(state?.uptime_seconds || 0)}
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className={`w-2 h-2 rounded-full ${isConnected ? 'bg-profit animate-pulse' : 'bg-warn'}`} />
            <span className={`text-sm font-mono ${isConnected ? 'text-profit' : 'text-warn'}`}>
              {isConnected ? 'CONNECTED' : 'DISCONNECTED'}
            </span>
          </div>
        </header>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <StatCard label="Trades" value={totalTrades} />
          <StatCard label="Wins" value={wins} color="profit" />
          <StatCard label="Losses" value={losses} color="loss" />
          <StatCard
            label="Win Rate"
            value={winRate.toFixed(1)}
            suffix="%"
            color={wrColor}
          />
          <StatCard
            label="Account"
            value={acc?.balance != null ? `£${acc.balance.toFixed(2)}` : `£${currentEquity.toFixed(2)}`}
          />
          <StatCard
            label="P&L"
            value={totalPnl >= 0 ? `+£${totalPnl.toFixed(2)}` : `£${totalPnl.toFixed(2)}`}
            color={totalPnl >= 0 ? "profit" : "loss"}
          />
          <StatCard
            label="Max DD"
            value={maxDrawdown.toFixed(1)}
            suffix="%"
            color={ddColor}
          />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SessionPanel
            session={state?.session}
            candleCountdown={state?.session?.candle_countdown}
          />
          <SignalPanel signal={state?.current_signal} />
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-muted text-xs uppercase tracking-wider mb-1">Session Timer</div>
            {state?.session ? (
              <div className="text-fg font-mono text-2xl">
                {formatTime(sessionSeconds)}
              </div>
            ) : (
              <div className="text-muted font-mono text-2xl">—</div>
            )}
          </div>
        </div>

        {backtestState && (
          <div className="bg-card/50 border border-border rounded-lg p-4 mb-4">
            <div className="text-xs text-muted uppercase tracking-wider mb-3">
              Live vs 2026 Backtest
            </div>
            <div className="grid grid-cols-2 md:grid-cols-4 gap-4 text-sm">
              <div>
                <div className="text-muted mb-1">Live WR</div>
                <div className={`font-mono text-lg ${wrColor}`}>{winRate.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-muted mb-1">Backtest WR</div>
                <div className="font-mono text-lg text-muted">{backtestWinRate.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-muted mb-1">Difference</div>
                <div className={`font-mono text-lg ${wrDiffColor}`}>
                  {backtestWRDiff > 0 ? "+" : ""}{Math.abs(backtestWRDiff).toFixed(1)}%
                </div>
              </div>
              <div>
                <div className="text-muted mb-1">Expected ROI</div>
                <div className="font-mono text-lg text-muted">{backtestROIPct.toFixed(1)}%</div>
              </div>
              <div>
                <div className="text-muted mb-1">Actual ROI</div>
                <div className={`font-mono text-lg ${roiDiffColor}`}>{totalPnlPct.toFixed(1)}%</div>
              </div>
            </div>
            <div className="text-xs text-muted mt-2">
              {loadingBacktest ? "Loading backtest data..." : "Based on 2026 X-Base backtest with £2000 starting capital"}
            </div>
          </div>
        )}

        <div className="relative">
          <EquityCurve data={equityCurveData} evData={evData} showEV={showEV} />
          <button
            onClick={() => setShowEV(!showEV)}
            className={`absolute top-4 right-4 px-3 py-1.5 text-xs font-medium rounded-lg transition-colors ${
              showEV
                ? "bg-profit/20 text-profit border border-profit"
                : "bg-card text-muted border border-border hover:bg-border"
            }`}
          >
            {showEV ? "Hide EV" : "Show EV"}
          </button>
        </div>

        <OrdersTable orders={state?.orders || []} />
        <TradesTable trades={state?.trades || []} />
        <LogsPanel logs={logs} />
        <TradeLog trades={allTradeEvents} equityCurve={equityCurveData} />
        <SessionBreakdown trades={allTradeEvents} />
      </div>
    </div>
  );
}
