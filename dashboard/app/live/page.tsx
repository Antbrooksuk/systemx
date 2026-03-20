"use client";

import { useLive, LiveOrder, LiveTrade } from "../../hooks/useLive";
import { StatCard } from "../../components/StatCard";

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

  const isLong = signal.direction === "long";
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
              <td className={`py-2 pr-3 ${(o.direction ?? "") === "long" ? "text-profit" : "text-loss"}`}>
                {(o.direction ?? "—").toUpperCase()}
              </td>
              <td className="py-2 pr-3 text-right text-warn">{o.type ?? "LIMIT"}</td>
              <td className="py-2 pr-3 text-right">{formatPip(o.price, o.pair ?? "EURUSD")}</td>
              <td className="py-2 pr-3 text-right text-loss">{formatPip(o.sl, o.pair ?? "EURUSD")}</td>
              <td className="py-2 text-right text-profit">{formatPip(o.tp, o.pair ?? "EURUSD")}</td>
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
              <td className={`py-2 pr-3 ${(t.direction ?? "") === "long" ? "text-profit" : "text-loss"}`}>
                {(t.direction ?? "—").toUpperCase()}
              </td>
              <td className="py-2 pr-3 text-right">{t.units}</td>
              <td className="py-2 pr-3 text-right">{formatPip(t.price, t.pair)}</td>
              <td className="py-2 pr-3 text-right">{formatPip(t.current_price, t.pair)}</td>
              <td className={`py-2 text-right ${(t.unrealized_pl ?? 0) >= 0 ? "text-profit" : "text-loss"}`}>
                {((t.unrealized_pl ?? 0) >= 0 ? "+" : ""}{(t.unrealized_pl ?? 0).toFixed(2)}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  );
}

export default function LivePage() {
  const { state, error } = useLive();

  if (error) {
    return (
      <div className="min-h-screen p-4 md:p-6">
        <div className="bg-card border border-loss rounded-lg p-6 text-center">
          <div className="text-loss font-bold mb-2">Connection Failed</div>
          <div className="text-muted text-sm">{error}</div>
          <div className="text-muted text-xs mt-2">Make sure the bot is running on port 8001</div>
        </div>
      </div>
    );
  }

  if (!state) {
    return (
      <div className="min-h-screen p-4 md:p-6">
        <div className="flex items-center justify-center h-64">
          <div className="w-3 h-3 bg-profit rounded-full animate-pulse mr-3" />
          <span className="text-muted">Connecting to bot...</span>
        </div>
      </div>
    );
  }

  const acc = state.account;
  const pnl = acc ? acc.equity - acc.balance : 0;
  const sessionSeconds = state.session?.seconds_remaining ?? 0;

  return (
    <div className="min-h-screen p-4 md:p-6">
      <div className="space-y-4">
        <header className="flex items-center justify-between border-b border-border pb-4">
          <div>
            <h1 className="text-2xl font-bold">Live Trading</h1>
            <p className="text-muted text-sm">
              Bot uptime: {formatUptime(state.uptime_seconds)} &middot;{" "}
              <span className="text-muted">Updated just now</span>
            </p>
          </div>
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-profit rounded-full animate-pulse" />
            <span className="text-profit text-sm font-mono">LIVE</span>
          </div>
        </header>

        <div className="grid grid-cols-2 md:grid-cols-4 lg:grid-cols-6 gap-3">
          <StatCard
            label="Balance"
            value={acc?.balance != null ? `${acc.currency === "GBP" ? "£" : "$"}${acc.balance.toFixed(0)}` : "—"}
          />
          <StatCard
            label="Equity"
            value={acc?.equity != null ? `${acc.currency === "GBP" ? "£" : "$"}${acc.equity.toFixed(0)}` : "—"}
          />
          <StatCard
            label="Unrealized P&L"
            value={acc ? formatMoney(acc.unrealized_pl, acc.currency) : "—"}
            color={acc && acc.unrealized_pl >= 0 ? "profit" : "loss"}
          />
          <StatCard
            label="Total P&L %"
            value={state.total_pnl_pct.toFixed(2)}
            suffix="%"
            color={state.total_pnl_pct >= 0 ? "profit" : "loss"}
          />
          <StatCard label="Active Orders" value={state.active_orders} />
          <StatCard label="Filled Trades" value={state.filled_trades} />
        </div>

        <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
          <SessionPanel
            session={state.session}
            candleCountdown={state.session?.candle_countdown}
          />
          <SignalPanel signal={state.current_signal} />
          <div className="bg-card border border-border rounded-lg p-4">
            <div className="text-muted text-xs uppercase tracking-wider mb-1">Session Timer</div>
            {state.session ? (
              <div className="text-fg font-mono text-2xl">
                {formatTime(sessionSeconds)}
              </div>
            ) : (
              <div className="text-muted font-mono text-2xl">—</div>
            )}
          </div>
        </div>

        <OrdersTable orders={state.orders} />
        <TradesTable trades={state.trades} />
      </div>
    </div>
  );
}
