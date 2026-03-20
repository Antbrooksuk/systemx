"use client";

import { useEffect } from "react";
import {
  useBacktest,
  RISK_OPTIONS,
  CAPITAL_OPTIONS,
} from "../hooks/useBacktest";
import { StatCard } from "../components/StatCard";
import { EquityCurve } from "../components/EquityCurve";
import { TradeLog } from "../components/TradeLog";
import { SessionBreakdown } from "../components/SessionBreakdown";

const WR_THRESHOLDS = [
  { min: 71, color: "profit" as const },
  { min: 60, color: "warn" as const },
  { min: 0, color: "loss" as const },
];

function wrColor(wr: number) {
  for (const t of WR_THRESHOLDS) {
    if (wr >= t.min) return t.color;
  }
  return "loss";
}

function formatCurrency(value: number): string {
  if (Math.abs(value) >= 1000000) {
    return `${value >= 0 ? "+" : ""}£${(value / 1000000).toFixed(2)}M`;
  }
  if (Math.abs(value) >= 1000) {
    return `${value >= 0 ? "+" : ""}£${(value / 1000).toFixed(1)}K`;
  }
  return `${value >= 0 ? "+" : ""}£${value.toFixed(2)}`;
}

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
    reset,
    runInstant,
    runStream,
  } = useBacktest();

  useEffect(() => {
    fetchStrategies();
  }, [fetchStrategies]);

  const pnl = state.current_capital - state.starting_capital;
  const pnlColor = pnl >= 0 ? "profit" : "loss";
  const currentStrategy = strategies.find((s) => s.key === selectedStrategy);

  return (
    <div className="min-h-screen p-4 md:p-6">
      <div className="space-y-4">
        <header className="flex flex-col md:flex-row md:items-center md:justify-between gap-4 border-b border-border pb-4">
          <div>
            <h1 className="text-2xl font-bold flex items-center gap-2">
              SYSTEM-X
            </h1>
            <p className="text-muted text-sm">
              {currentStrategy ? (
                <span title={currentStrategy.description}>
                  {currentStrategy.label}
                </span>
              ) : (
                "Mode B — Session Scalp"
              )}
            </p>
          </div>

          <div className="flex flex-wrap gap-2 items-center">
            <select
              value={selectedStrategy}
              onChange={(e) => setSelectedStrategy(e.target.value)}
              disabled={state.running}
              className="px-3 py-2 bg-card border border-border rounded-lg text-sm font-medium text-fg focus:outline-none focus:ring-2 focus:ring-border disabled:opacity-50 min-w-[180px]"
            >
              {strategies.map((s) => (
                <option key={s.key} value={s.key}>
                  {s.label}
                </option>
              ))}
            </select>

            <select
              value={selectedCapital}
              onChange={(e) => setSelectedCapital(Number(e.target.value))}
              disabled={state.running}
              className="px-3 py-2 bg-card border border-border rounded-lg text-sm font-medium text-fg focus:outline-none focus:ring-2 focus:ring-border disabled:opacity-50 min-w-[100px]"
            >
              {CAPITAL_OPTIONS.map((c) => (
                <option key={c} value={c}>
                  £{c.toLocaleString()}
                </option>
              ))}
            </select>

            <select
              value={selectedRisk}
              onChange={(e) => setSelectedRisk(Number(e.target.value))}
              disabled={state.running}
              className="px-3 py-2 bg-card border border-border rounded-lg text-sm font-medium text-fg focus:outline-none focus:ring-2 focus:ring-border disabled:opacity-50 min-w-[80px]"
            >
              {RISK_OPTIONS.map((r) => (
                <option key={r} value={r}>
                  {(r * 100).toFixed(1)}%
                </option>
              ))}
            </select>

            <select
              value={selectedYear}
              onChange={(e) => setSelectedYear(Number(e.target.value))}
              disabled={state.running}
              className="px-3 py-2 bg-card border border-border rounded-lg text-sm font-medium text-fg focus:outline-none focus:ring-2 focus:ring-border disabled:opacity-50 min-w-[90px]"
            >
              <option value={0}>All</option>
              {availableYears.map((y) => (
                <option key={y} value={y}>
                  {y}
                </option>
              ))}
            </select>

            <button
              onClick={runInstant}
              disabled={state.running}
              className="px-4 py-2 bg-card border border-border rounded-lg hover:bg-border disabled:opacity-50 disabled:cursor-not-allowed text-sm font-medium"
            >
              {state.running ? "Running..." : "Run Backtest"}
            </button>
          </div>
        </header>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-7 gap-3">
          <StatCard label="Trades" value={state.wins + state.losses} />
          <StatCard label="Wins" value={state.wins} color="profit" />
          <StatCard label="Losses" value={state.losses} color="loss" />
          <StatCard
            label="Win Rate"
            value={(state.win_rate ?? 0).toFixed(1)}
            suffix="%"
            color={wrColor(state.win_rate ?? 0)}
          />
          <StatCard
            label="Account"
            value={formatCurrency(state.current_capital ?? 2000)}
          />
          <StatCard label="P&L" value={formatCurrency(pnl)} color={pnlColor} />
          <StatCard
            label="Max DD"
            value={(state.max_drawdown ?? 0).toFixed(1)}
            suffix="%"
            color={(state.max_drawdown ?? 0) < 15 ? "profit" : "loss"}
          />
        </div>

        <EquityCurve data={state.equity_curve} />

        <TradeLog trades={state.trades} />

        <SessionBreakdown trades={state.trades} />

        {state.running && (
          <div className="fixed bottom-4 right-4 bg-card border border-border rounded-lg px-4 py-2 shadow-lg">
            <div className="flex items-center gap-2">
              <div className="w-2 h-2 bg-profit rounded-full animate-pulse" />
              <span className="text-sm">
                Processing {currentStrategy?.label ?? ""}...
              </span>
            </div>
          </div>
        )}
      </div>
    </div>
  );
}
