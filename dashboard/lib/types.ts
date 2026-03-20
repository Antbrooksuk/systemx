export interface Trade {
  date: string | null;
  pair: string;
  session: string;
  signal: string;
  skip_reason: string | null;
  entry: number | null;
  sl: number | null;
  tp: number | null;
  exit_price: number | null;
  exit_reason: string;
  pips: number;
  pnl_pct: number;
  spread_pips: number;
  filled: boolean;
}

export interface EquityPoint {
  trade: number;
  equity: number;
  date: string;
}

export interface BacktestResult {
  starting_capital: number;
  final_capital: number;
  total_opportunities: number;
  trades_taken: number;
  skips: number;
  wins: number;
  losses: number;
  win_rate: number;
  avg_pnl_pct: number;
  max_drawdown: number;
  roi: number;
  equity_curve: EquityPoint[];
  trades: Trade[];
}

export interface State {
  starting_capital: number;
  current_capital: number;
  trades: Trade[];
  equity_curve: EquityPoint[];
  wins: number;
  losses: number;
  skips: number;
  win_rate: number;
  max_drawdown: number;
  roi: number;
  running: boolean;
}
