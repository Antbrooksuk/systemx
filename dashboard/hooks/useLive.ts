"use client";

import { useState, useEffect, useCallback } from "react";

export interface LiveSignal {
  signal: string;
  pair: string;
  entry: number;
  sl: number;
  tp: number;
  rr: number;
  direction: string;
  reason?: string;
  error?: string;
}

export interface LiveOrder {
  id: string;
  pair: string;
  direction: string;
  type: string;
  price: number;
  units: number;
  sl: number;
  tp: number;
  trade_id: string;
}

export interface LiveTrade {
  id: string;
  pair: string;
  direction: string;
  units: number;
  price: number;
  current_price: number;
  unrealized_pl: number;
  open_time: string;
  oanda_trade_id?: string;
}

export interface HistoricalTrade {
  pair: string;
  session: string;
  direction: string;
  units: number;
  entry_time: string;
  entry: number;
  sl: number;
  tp: number;
  exit_time: string | null;
  exit_price: number | null;
  exit_reason: string;
  pips: number;
  pnl_pct: number;
  oanda_trade_id: string;
}

export interface LiveSignalResult {
  pair: string;
  session: string;
  signal: string;
  direction: string | null;
  entry: number | null;
  sl: number | null;
  tp: number | null;
  reason: string | null;
  checked_at: string;
}

export interface LiveState {
  session: {
    name: string;
    pairs: string[];
    seconds_remaining: number;
    candle_countdown: number;
  } | null;
  active_orders: number;
  filled_trades: number;
  total_pnl_pct: number;
  uptime_seconds: number;
  account: {
    balance: number;
    equity: number;
    unrealized_pl: number;
    currency: string;
  } | null;
  current_signal: LiveSignal | null;
  orders: LiveOrder[];
  trades: LiveTrade[];
  historicalTrades: HistoricalTrade[];
  signals: LiveSignalResult[];
}

export function useLive() {
  const [state, setState] = useState<LiveState | null>(null);
  const [error, setError] = useState<string | null>(null);

  const fetchAll = useCallback(async () => {
    try {
      const [statusRes, ordersRes, tradesRes, histRes] = await Promise.all([
        fetch(`${process.env.NEXT_PUBLIC_BOT_API_URL}/status`),
        fetch(`${process.env.NEXT_PUBLIC_BOT_API_URL}/orders`),
        fetch(`${process.env.NEXT_PUBLIC_BOT_API_URL}/live-trades`),
        fetch(`${process.env.NEXT_PUBLIC_BOT_API_URL}/trades`),
      ]);

      const [status, ordersData, tradesData, histData] = await Promise.all([
        statusRes.json(),
        ordersRes.json(),
        tradesRes.json(),
        histRes.json(),
      ]);

      setState({
        ...status,
        orders: ordersData.orders || [],
        trades: tradesData.trades || [],
        historicalTrades: histData.trades || [],
        signals: [],
      });
      setError(null);
    } catch (e: any) {
      setError(e.message || "Connection failed");
    }
  }, []);

  useEffect(() => {
    fetchAll();
    const interval = setInterval(fetchAll, 5000);
    return () => clearInterval(interval);
  }, [fetchAll]);

  return { state, error };
}
