"""Strategy — wraps SYSTEM-X mode_b.py strategy logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "systemx"))

from mode_b import analyse_setup, calculate_entry, set_strategy, Signal, check_first_candle_in_range, PAIR_CONFIG


set_strategy("base")


def get_pd_range(pd_candles_df) -> tuple[float, float]:
    """Extract previous day high/low from PD candles."""
    if pd_candles_df is None or pd_candles_df.empty:
        return 0.0, 0.0
    pd_high = float(pd_candles_df["High"].max())
    pd_low = float(pd_candles_df["Low"].min())
    return pd_high, pd_low


def run_signal(pd_candles_df, session_candles_df, pair: str) -> dict:
    if pd_candles_df is None or session_candles_df is None:
        return {"signal": "SKIP", "reason": "no_data"}

    if pd_candles_df.empty or session_candles_df.empty:
        return {"signal": "SKIP", "reason": "no_data"}

    pd_high, pd_low = get_pd_range(pd_candles_df)
    if pd_high == 0 or pd_low == 0:
        return {"signal": "SKIP", "reason": "no_pd_data"}

    if len(session_candles_df) < 1:
        return {"signal": "SKIP", "reason": "no_session_candles"}

    first_candle = session_candles_df.iloc[0]
    skip_reason = check_first_candle_in_range(first_candle, pd_high, pd_low, pair)
    if skip_reason:
        return {"signal": "SKIP", "reason": skip_reason}

    setup = analyse_setup(pd_candles_df, session_candles_df, pair)

    if setup.signal == Signal.SKIP:
        return {"signal": "SKIP", "reason": setup.skip_reason or "setup_rejected"}

    trade_params = calculate_entry(setup, session_candles_df, pair)
    if trade_params is None:
        return {"signal": "SKIP", "reason": "no_valid_entry"}

    pip_value = PAIR_CONFIG[pair]["pip_value"]
    pip_str = "%.5f" if pip_value < 0.001 else "%.3f"

    return {
        "signal": setup.signal.value,
        "pair": pair,
        "entry": float(trade_params.entry),
        "entry_formatted": pip_str % trade_params.entry,
        "sl": float(trade_params.stop_loss),
        "sl_formatted": pip_str % trade_params.stop_loss,
        "tp": float(trade_params.take_profit),
        "tp_formatted": pip_str % trade_params.take_profit,
        "rr": trade_params.risk_reward,
        "direction": trade_params.direction,
    }
