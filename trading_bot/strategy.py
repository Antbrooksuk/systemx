"""Strategy — wraps SYSTEM-X mode_b.py strategy logic."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "systemx"))

from mode_b import analyse_setup, calculate_entry, set_strategy, Signal

set_strategy("base")


def run_signal(pd_candles_df, session_candles_df, pair: str) -> dict:
    if pd_candles_df is None or session_candles_df is None:
        return {"signal": "SKIP", "reason": "no_data"}

    if pd_candles_df.empty or session_candles_df.empty:
        return {"signal": "SKIP", "reason": "no_data"}

    setup = analyse_setup(pd_candles_df, session_candles_df, pair)

    if setup.signal == Signal.SKIP:
        return {"signal": "SKIP", "reason": setup.skip_reason or "setup_rejected"}

    trade_params = calculate_entry(setup, session_candles_df, pair)
    if trade_params is None:
        return {"signal": "SKIP", "reason": "no_valid_entry"}

    pip_value = 0.0001 if pair != "USDJPY" else 0.01
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
