from datetime import date, timedelta
from typing import Dict
import pandas as pd
from pathlib import Path

from mode_b import (
    analyse_setup, calculate_entry, simulate_trade,
    SetupResult, TradeParams, TradeResult, Signal, ExitReason,
    TIME_STOP_CANDLES, set_strategy, STRATEGY_PRESETS, PAIR_CONFIG,
)
from config import (
    PAIRS,
    STARTING_CAPITAL,
    RISK_PER_TRADE,
)


DATA_DIR = Path(__file__).parent / "data"


SESSION_PAIRS = {
    "london": ["EURUSD", "GBPUSD"],
    "ny": ["EURUSD", "GBPUSD", "USDJPY"],
}

SESSION_WINDOWS = {
    "london": ("08:00", "10:00"),
    "ny": ("14:30", "16:30"),
}


def load_data() -> Dict[str, pd.DataFrame]:
    data = {}
    for pair in PAIRS:
        oanda_file = DATA_DIR / f"{pair}_oanda.parquet"
        yf_file = DATA_DIR / f"{pair}.parquet"
        file = oanda_file if oanda_file.exists() else yf_file
        if not file.exists():
            raise FileNotFoundError(f"Missing {file}. Run: python3 fetch_data.py first")
        df = pd.read_parquet(file)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        data[pair] = df
    return data


def get_pd_candles(df: pd.DataFrame, target_date: date) -> pd.DataFrame:
    """Get previous day's 24h candles (ending at midnight before target)."""
    tz = df.index.tz
    pd_end = pd.Timestamp(target_date, tz=tz)
    pd_start = pd_end - timedelta(days=1)
    return df[(df.index >= pd_start) & (df.index < pd_end)]


def extract_session(df: pd.DataFrame, target_date: date, window: str) -> pd.DataFrame:
    """Extract session window candles."""
    df_day = df[df.index.date == target_date]
    start, end = SESSION_WINDOWS[window]
    return df_day.between_time(start, end)


def run_backtest(period_days: int = 0, strategy: str = "base", starting_capital: float = 2000.0, risk_pct: float = 0.01) -> Dict:
    set_strategy(strategy)
    data = load_data()

    capital = starting_capital
    max_capital = capital
    max_dd = 0.0
    equity_curve = [{"trade": 0, "equity": capital, "date": ""}]
    trades = []
    wins = 0
    losses = 0
    skips = 0
    unfilled = 0
    trade_num = 0
    opportunities = 0

    all_dates = sorted(set(data[PAIRS[0]].index.date))

    if period_days > 0:
        data_end = max(all_dates)
        cutoff = pd.Timestamp(data_end) - timedelta(days=period_days)
        all_dates = [d for d in all_dates if d >= cutoff.date()]

    for target_date in all_dates:
        for session_name in SESSION_WINDOWS:
            for pair in SESSION_PAIRS[session_name]:
                df = data[pair]

                pd_candles = get_pd_candles(df, target_date)
                session_candles = extract_session(df, target_date, session_name)

                if pd_candles.empty or session_candles.empty:
                    continue

                opportunities += 1

                setup = analyse_setup(pd_candles, session_candles, pair)

                if setup.signal == Signal.SKIP:
                    skips += 1
                    trades.append({
                        "date": str(target_date),
                        "pair": pair,
                        "session": session_name,
                        "signal": "SKIP",
                        "skip_reason": setup.skip_reason,
                        "entry": None,
                        "sl": None,
                        "tp": None,
                        "exit_price": None,
                        "exit_reason": None,
                        "pips": 0,
                        "pnl_pct": 0
                    })
                    continue

                trade_params = calculate_entry(setup, session_candles, pair)

                if trade_params is None:
                    skips += 1
                    trades.append({
                        "date": str(target_date),
                        "pair": pair,
                        "session": session_name,
                        "signal": "SKIP",
                        "skip_reason": "no_valid_entry",
                        "entry": None,
                        "sl": None,
                        "tp": None,
                        "exit_price": None,
                        "exit_reason": None,
                        "pips": 0,
                        "pnl_pct": 0
                    })
                    continue

                entry_idx = setup.entry_candle_idx
                post_candles = session_candles.iloc[entry_idx + 1:entry_idx + 1 + TIME_STOP_CANDLES]

                result = simulate_trade(
                    trade_params=trade_params,
                    post_candles=post_candles,
                    pair=pair,
                    risk_pct=risk_pct,
                    max_candles=TIME_STOP_CANDLES
                )

                if result.exit_reason == ExitReason.NONE:
                    continue

                if result.exit_reason == ExitReason.LIMIT_NOT_REACHED:
                    unfilled += 1
                    trades.append({
                        "date": str(target_date),
                        "pair": pair,
                        "session": session_name,
                        "signal": trade_params.direction,
                        "skip_reason": "LIMIT_NOT_REACHED",
                        "entry": round(trade_params.entry, 5),
                        "sl": round(trade_params.stop_loss, 5),
                        "tp": round(trade_params.take_profit, 5),
                        "exit_price": None,
                        "exit_reason": "LIMIT",
                        "pips": 0,
                        "pnl_pct": 0,
                        "spread_pips": PAIR_CONFIG[pair]["spread_pips"],
                        "filled": False,
                        "imp_body_pct": setup.imp_body_pct,
                        "pull_body_pct": setup.pull_body_pct,
                    })
                    continue

                trade_num += 1
                capital *= (1 + result.pnl_pct / 100)
                equity_curve.append({
                    "trade": trade_num,
                    "equity": round(capital, 2),
                    "date": str(target_date)
                })

                if capital > max_capital:
                    max_capital = capital

                dd = (max_capital - capital) / max_capital
                if dd > max_dd:
                    max_dd = dd

                if result.pnl_pct > 0:
                    wins += 1
                else:
                    losses += 1

                trades.append({
                    "date": str(target_date),
                    "pair": pair,
                    "session": session_name,
                    "signal": trade_params.direction,
                    "skip_reason": None,
                    "entry": round(trade_params.entry, 5),
                    "sl": round(trade_params.stop_loss, 5),
                    "tp": round(trade_params.take_profit, 5),
                    "exit_price": round(result.exit_price, 5) if result.exit_price else None,
                    "exit_reason": result.exit_reason.value,
                    "pips": result.pips,
                    "pnl_pct": round(result.pnl_pct, 4),
                    "spread_pips": PAIR_CONFIG[pair]["spread_pips"],
                    "filled": result.filled,
                    "imp_body_pct": setup.imp_body_pct,
                    "pull_body_pct": setup.pull_body_pct,
                })

    total_trades = wins + losses
    win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0.0

    roi = round((capital - starting_capital) / starting_capital * 100, 1)
    max_dd_pct = round(max_dd * 100, 1)

    return {
        "starting_capital": starting_capital,
        "final_capital": round(capital, 2),
        "roi": roi,
        "max_drawdown": max_dd_pct,
        "total_opportunities": opportunities,
        "trades_taken": total_trades,
        "wins": wins,
        "losses": losses,
        "skips": skips,
        "unfilled": unfilled,
        "win_rate": win_rate,
        "equity_curve": equity_curve,
        "trades": trades,
        "strategy": strategy,
        "strategy_label": STRATEGY_PRESETS[strategy]["label"],
    }


def get_status() -> Dict:
    return {
        "starting_capital": STARTING_CAPITAL,
        "current_capital": STARTING_CAPITAL,
        "trades_taken": 0,
        "wins": 0,
        "losses": 0,
        "skips": 0,
        "win_rate": 0,
        "max_drawdown": 0.0,
        "equity_curve": [{"trade": 0, "equity": STARTING_CAPITAL}],
        "trades": [],
    }
