"""
Parameter Sweep Backtest — Find optimal TIME_STOP and ENTRY_AT_EXTREME values
Tests 16 combinations (8 time stops × 2 entry methods)
"""
import json
import pandas as pd
from pathlib import Path
from mode_b import (
    analyse_setup, calculate_entry, simulate_trade,
    SetupResult, TradeParams, TradeResult, Signal, ExitReason,
    TIME_STOP_CANDLES, set_strategy, STRATEGY_PRESETS, PAIR_CONFIG,
    SL_OFFSET_PIPS, MIN_RR, ENTRY_AT_EXTREME,
)
from config import PAIRS, STARTING_CAPITAL, RISK_PER_TRADE


DATA_DIR = Path(__file__).parent / "data"


SESSION_PAIRS = {
    "london": ["EURUSD", "GBPUSD"],
    "ny": ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"],
}


SESSION_WINDOWS = {
    "london": ("08:00", "09:30"),
    "ny": ("14:30", "16:00"),
}


def load_data(year: int = 0) -> dict:
    import re
    data = {}
    for pair in PAIRS:
        if year > 0:
            file = DATA_DIR / f"{pair}_{year}.parquet"
        else:
            files = sorted(DATA_DIR.glob(f"{pair}_*.parquet"), key=lambda f: f.name)
            file = files[-1] if files else None
        if not file or not file.exists():
            print(f"Skipping {pair}: data file not found")
            continue
        df = pd.read_parquet(file)
        df.index = pd.to_datetime(df.index)
        df = df.sort_index()
        data[pair] = df
    return data


def get_pd_candles(df: pd.DataFrame, target_date) -> pd.DataFrame:
    from datetime import timedelta
    tz = df.index.tz
    pd_end = pd.Timestamp(target_date, tz=tz)
    pd_start = pd_end - timedelta(days=1)
    return df[(df.index >= pd_start) & (df.index < pd_end)]


def extract_session(df: pd.DataFrame, target_date, window: str) -> pd.DataFrame:
    df_day = df[df.index.date == target_date]
    start, end = SESSION_WINDOWS[window]
    return df_day.between_time(start, end)


def run_single_backtest(time_stop_candles: int, entry_at_extreme: bool, data: dict) -> dict:
    import mode_b
    
    mode_b.TIME_STOP_CANDLES = time_stop_candles
    mode_b.ENTRY_AT_EXTREME = entry_at_extreme
    
    capital = STARTING_CAPITAL
    max_capital = capital
    max_dd = 0.0
    wins = 0
    losses = 0
    skips = 0
    unfilled = 0
    trade_num = 0
    opportunities = 0
    trades = []
    
    all_dates = sorted(set(data[PAIRS[0]].index.date))
    
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
                    continue
                
                trade_params = calculate_entry(setup, session_candles, pair)
                
                if trade_params is None:
                    skips += 1
                    continue
                
                entry_idx = setup.entry_candle_idx
                post_candles = session_candles.iloc[entry_idx + 1:entry_idx + 1 + time_stop_candles]
                
                result = simulate_trade(
                    trade_params=trade_params,
                    post_candles=post_candles,
                    pair=pair,
                    account_gbp=capital,
                    risk_pct=RISK_PER_TRADE,
                    max_candles=time_stop_candles
                )
                
                if result.exit_reason == ExitReason.NONE:
                    continue
                
                if result.exit_reason == ExitReason.LIMIT_NOT_REACHED:
                    unfilled += 1
                    continue
                
                trade_num += 1
                capital *= (1 + result.pnl_pct / 100)
                
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
                })
    
    total_trades = wins + losses
    win_rate = round((wins / total_trades) * 100, 1) if total_trades > 0 else 0.0
    roi = round((capital - STARTING_CAPITAL) / STARTING_CAPITAL * 100, 1)
    max_dd_pct = round(max_dd * 100, 1)
    
    unfilled_rate = round(unfilled / (total_trades + unfilled) * 100, 1) if (total_trades + unfilled) > 0 else 0.0
    
    avg_rr = 0.0
    if trades:
        total_pnl = sum(t["pnl_pct"] for t in trades if t["filled"])
        total_rr = abs(sum(t["pips"] for t in trades if t["filled"]))
        avg_rr = round(total_rr / len([t for t in trades if t["filled"]]), 2) if trades else 0.0
    
    return {
        "time_stop_candles": time_stop_candles,
        "time_stop_minutes": time_stop_candles * 5,
        "entry_at_extreme": entry_at_extreme,
        "starting_capital": STARTING_CAPITAL,
        "final_capital": round(capital, 2),
        "roi": roi,
        "max_drawdown": max_dd_pct,
        "total_opportunities": opportunities,
        "trades_taken": total_trades,
        "wins": wins,
        "losses": losses,
        "skips": skips,
        "unfilled": unfilled,
        "unfilled_rate": unfilled_rate,
        "win_rate": win_rate,
        "avg_rr": avg_rr,
    }


def main():
    print("=" * 80)
    print("PARAMETER SWEEP BACKTEST - Testing 16 Combinations")
    print("=" * 80)
    print()
    
    data = load_data()
    if not data:
        print("ERROR: No data loaded")
        return
    
    time_stops = [4, 6, 8, 10, 12, 14, 16, 18]
    entry_methods = [True, False]
    
    results = []
    
    print(f"Testing {len(time_stops)} × {len(entry_methods)} = {len(time_stops) * len(entry_methods)} combinations")
    print(f"Time stops: {time_stops} candles ({[t*5 for t in time_stops]} minutes)")
    print(f"Entry methods: EXTREME={entry_methods}")
    print()
    
    rank = 1
    for time_stop in time_stops:
        for entry_extreme in entry_methods:
            print(f"Running test {rank}/16: time_stop={time_stop} ({time_stop*5}min), entry_at_extreme={entry_extreme}")
            
            result = run_single_backtest(time_stop, entry_extreme, data)
            result["rank"] = rank
            results.append(result)
            rank += 1
    
    print()
    print("=" * 80)
    print("RESULTS RANKED BY WIN RATE")
    print("=" * 80)
    print()
    
    results_filtered = [r for r in results if r["max_drawdown"] < 15.0]
    
    print(f"{len(results_filtered)} combinations meet max drawdown < 15% criterion")
    print()
    
    sorted_results = sorted(results_filtered, key=lambda x: (-x["win_rate"], x["avg_rr"]))
    
    print(f"{'Rank':<6} {'Time':<10} {'Entry':<8} {'Win%':<7} {'R:R':<7} {'DD%':<6} {'Unfilled%':<11} {'Trades':<8}")
    print("-" * 80)
    
    for r in sorted_results[:15]:
        time_str = f"{r['time_stop_candles']} ({r['time_stop_minutes']}min)"
        entry_str = "EXTREME" if r['entry_at_extreme'] else "CLOSE"
        
        print(f"{r['rank']:>5} {time_str:>8} {entry_str:>8} {r['win_rate']:>6.1f}% {r['avg_rr']:>6.2f} {r['max_drawdown']:>5.1f}% {r['unfilled_rate']:>9.1f}% {r['trades_taken']:>8}")
    
    print()
    print("=" * 80)
    print("TOP 3 RECOMMENDATIONS")
    print("=" * 80)
    print()
    
    top3 = sorted_results[:3]
    for i, r in enumerate(top3, 1):
        time_str = f"{r['time_stop_minutes']} minutes ({r['time_stop_candles']} candles)"
        entry_str = "pullback EXTREME (LOW/HIGH)" if r['entry_at_extreme'] else "pullback CLOSE"
        
        print(f"#{i} WIN RATE: {r['win_rate']:.1f}%")
        print(f"    Time stop: {time_str}")
        print(f"    Entry method: {entry_str}")
        print(f"    Trades taken: {r['trades_taken']}")
        print(f"    Unfilled: {r['unfilled']} ({r['unfilled_rate']:.1f}%)")
        print(f"    R:R: {r['avg_rr']:.2f}")
        print(f"    Max DD: {r['max_drawdown']:.1f}%")
        print(f"    ROI: {r['roi']:.1f}%")
        print()
    
    print("=" * 80)
    print("RECOMMENDATION SUMMARY")
    print("=" * 80)
    print()
    
    best = sorted_results[0]
    print(f"✓ OPTIMAL CONFIGURATION:")
    print(f"  Time stop: {best['time_stop_candles']} candles ({best['time_stop_minutes']} minutes)")
    print(f"  Entry at: {'EXTREME (pullback low/high)' if best['entry_at_extreme'] else 'CLOSE (pullback candle close)'}")
    print(f"  Expected win rate: {best['win_rate']:.1f}%")
    print(f"  Unfilled rate: {best['unfilled_rate']:.1f}%")
    print()
    print(f"To apply these settings:")
    print(f"  1. Update mode_b.py: TIME_STOP_CANDLES = {best['time_stop_candles']}")
    print(f"  2. Update mode_b.py: ENTRY_AT_EXTREME = {best['entry_at_extreme']}")
    print(f"  3. Update trading_bot/orders.py: MAX_CANDLES = {best['time_stop_candles']}")
    print(f"  4. Update trading_bot/session.py: Session windows to match {best['time_stop_minutes']} minutes")
    print(f"  5. Update trading_bot/oanda.py: GTD time to {best['time_stop_minutes']} minutes")
    print()


if __name__ == "__main__":
    main()
