import { useState, useCallback } from "react";
import { State, Trade, EquityPoint } from "../lib/types";
import {
  getStatus,
  resetState,
  runBacktest,
  streamBacktest,
  getStrategies,
  getYears,
} from "../lib/api";

export interface Strategy {
  key: string;
  label: string;
  description: string;
}

const RISK_OPTIONS = [0.005, 0.01, 0.015, 0.02];
const CAPITAL_OPTIONS = [1000, 2000, 3000, 5000, 10000];

export { RISK_OPTIONS, CAPITAL_OPTIONS };

const initialState: State = {
  starting_capital: 2000,
  current_capital: 2000,
  trades: [],
  equity_curve: [{ trade: 0, equity: 2000, date: "" }],
  wins: 0,
  losses: 0,
  skips: 0,
  win_rate: 0,
  max_drawdown: 0,
  roi: 0,
  running: false,
};

export function useBacktest() {
  const [state, setState] = useState<State>(initialState);
  const [selectedStrategy, setSelectedStrategy] = useState<string>("base");
  const [selectedCapital, setSelectedCapital] = useState<number>(2000);
  const [selectedRisk, setSelectedRisk] = useState<number>(0.01);
  const [selectedYear, setSelectedYear] = useState<number>(0);
  const [availableYears, setAvailableYears] = useState<number[]>([]);
  const [strategies, setStrategies] = useState<Strategy[]>([
    {
      key: "base",
      label: "Mode X-Base",
      description: "Standard extreme entry — max volume",
    },
    { key: "plus", label: "Mode X-Plus", description: "Tighter pullback + SL" },
    {
      key: "elite",
      label: "Mode X-Elite",
      description: "Highest edge — tightest filters",
    },
  ]);

  const fetchStrategies = useCallback(async () => {
    try {
      const [stratData, yearsData] = await Promise.all([getStrategies(), getYears()]);
      const list = Object.entries(stratData).map(([key, cfg]: [string, any]) => ({
        key,
        label: cfg.label,
        description: cfg.description,
      }));
      setStrategies(list);
      setAvailableYears(yearsData.years || []);
    } catch {
      // keep defaults
    }
  }, []);

  const fetchStatus = useCallback(async () => {
    const data = await getStatus();
    setState((prev) => ({
      ...prev,
      starting_capital: data.starting_capital,
      current_capital: data.current_capital,
      wins: data.wins,
      losses: data.losses,
      skips: data.skips,
      win_rate: data.win_rate,
      max_drawdown: data.max_drawdown,
      equity_curve: data.equity_curve,
    }));
  }, []);

  const reset = useCallback(async () => {
    await resetState();
    setState(initialState);
  }, []);

  const runInstant = useCallback(async () => {
    setState((prev) => ({ ...prev, running: true }));
    try {
      const result = await runBacktest(
        selectedYear,
        selectedStrategy,
        selectedCapital,
        selectedRisk,
      );
      setState({
        starting_capital: result.starting_capital,
        current_capital: result.final_capital,
        trades: result.trades,
        equity_curve: result.equity_curve,
        wins: result.wins,
        losses: result.losses,
        skips: result.skips,
        win_rate: result.win_rate,
        max_drawdown: result.max_drawdown,
        roi: result.roi,
        running: false,
      });
    } catch (error) {
      console.error("Backtest error:", error);
      setState((prev) => ({ ...prev, running: false }));
    }
  }, [selectedStrategy, selectedCapital, selectedRisk, selectedYear]);

  const runStream = useCallback(() => {
    setState((prev) => ({
      ...prev,
      running: true,
      trades: [],
      equity_curve: [{ trade: 0, equity: selectedCapital, date: "" }],
    }));

    const ws = streamBacktest(
      (data) => {
        if (data.type === "trade") {
          setState((prev) => {
            const newTrades = [...prev.trades, data as Trade];
            return { ...prev, trades: newTrades };
          });
        } else if (data.type === "complete") {
          setState({
            starting_capital: data.starting_capital,
            current_capital: data.final_capital,
            trades: data.trades || [],
            equity_curve: data.equity_curve,
            wins: data.wins,
            losses: data.losses,
            skips: data.skips,
            win_rate: data.win_rate,
            max_drawdown: data.max_drawdown,
            roi: data.roi,
            running: false,
          });
        } else if (data.type === "error") {
          console.error("Stream error:", data.message);
          setState((prev) => ({ ...prev, running: false }));
        }
      },
      selectedYear,
      selectedStrategy,
      selectedCapital,
      selectedRisk,
    );

    ws.onerror = (error) => {
      console.error("WebSocket error:", error);
      setState((prev) => ({ ...prev, running: false }));
    };

    return () => ws.close();
  }, [selectedStrategy, selectedCapital, selectedRisk, selectedYear]);

  return {
    state,
    strategies,
    availableYears,
    selectedStrategy,
    setSelectedStrategy,
    selectedCapital,
    setSelectedCapital,
    selectedRisk,
    setSelectedRisk,
    selectedYear,
    setSelectedYear,
    fetchStrategies,
    fetchStatus,
    reset,
    runInstant,
    runStream,
  };
}
