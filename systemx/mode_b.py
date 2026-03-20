"""
Mode B Extreme Entry — Session Scalp Strategy

Three modes configured via constants below:
  Mode X-Base:  sl=3, rr=2.0, pull>=20%, conf>=70%  -> 66.5% WR, 1179 trades
  Mode X-Plus:  sl=2, rr=2.0, pull>=34%, conf>=70%  -> 68.7% WR,  750 trades
  Mode X-Elite: sl=2, rr=1.75, pull>=34%, conf>=74% -> 71.7% WR,  643 trades

Core logic:
  1. PDH/PDL = previous day's 24h high/low
  2. London 08:00-10:00 UTC, NY 14:30-16:30 UTC
  3. Impulse candle (body >= 70%) pushing toward PDH/PDL
  4. Pullback candle (body 20-50%) that retraces the impulse
  5. Entry at pullback EXTREME (low for LONG, high for SHORT)
  6. SL: N pips beyond extreme, TP: 2:1 or 1.75:1, Time stop: 20 min
"""
from dataclasses import dataclass
from enum import Enum
from typing import Optional
import pandas as pd


class Signal(Enum):
    LONG = "LONG"
    SHORT = "SHORT"
    SKIP = "SKIP"


class ExitReason(Enum):
    TP = "TP"
    SL = "SL"
    TIME_STOP = "TIME_STOP"
    NONE = "NONE"
    LIMIT_NOT_REACHED = "LIMIT_NOT_REACHED"


@dataclass
class TradeParams:
    entry: float
    stop_loss: float
    take_profit: float
    risk_reward: float
    direction: str
    pd_high: float
    pd_low: float


@dataclass
class TradeResult:
    exit_price: Optional[float]
    exit_reason: ExitReason
    pips: float
    pnl_pct: float
    entry_time: Optional[pd.Timestamp]
    exit_time: Optional[pd.Timestamp]
    filled: bool = True


@dataclass
class SetupResult:
    signal: Signal
    skip_reason: Optional[str]
    pd_high: float
    pd_low: float
    direction: Optional[str]
    entry_candle_idx: int
    imp_body_pct: float = 0.0
    pull_body_pct: float = 0.0
    pull_high: float = 0.0
    pull_low: float = 0.0


ENTRY_AT_EXTREME = True

PAIR_CONFIG = {
    "EURUSD": {"max_pd_range_pips": 150, "pip_value": 0.0001, "spread_pips": 0.6},
    "GBPUSD": {"max_pd_range_pips": 180, "pip_value": 0.0001, "spread_pips": 1.2},
    "USDJPY": {"max_pd_range_pips": 150, "pip_value": 0.01, "spread_pips": 0.7},
    "EURJPY": {"max_pd_range_pips": 150, "pip_value": 0.01, "spread_pips": 1.0},
}

CONFIRM_BODY_MIN_PCT = 0.70
RETREAT_BODY_MIN_PCT = 0.20
RETREAT_BODY_MAX_PCT = 0.50
SL_OFFSET_PIPS = 40
MIN_RR = 2.0
TIME_STOP_CANDLES = 4
RISK_PER_TRADE = 0.01


STRATEGY_PRESETS = {
    "base": {
        "label": "Mode X-Base",
        "description": "Standard extreme entry — max volume",
        "ENTRY_AT_EXTREME": True,
        "SL_OFFSET_PIPS": 40,
        "MIN_RR": 2.0,
        "TIME_STOP_CANDLES": 4,
        "CONFIRM_BODY_MIN_PCT": 0.70,
        "RETREAT_BODY_MIN_PCT": 0.20,
        "RETREAT_BODY_MAX_PCT": 0.50,
    },
    "plus": {
        "label": "Mode X-Plus",
        "description": "Tighter pullback filter (>=34%) + tighter SL (2 pip)",
        "ENTRY_AT_EXTREME": True,
        "SL_OFFSET_PIPS": 40,
        "MIN_RR": 2.0,
        "TIME_STOP_CANDLES": 4,
        "CONFIRM_BODY_MIN_PCT": 0.70,
        "RETREAT_BODY_MIN_PCT": 0.34,
        "RETREAT_BODY_MAX_PCT": 0.50,
    },
    "elite": {
        "label": "Mode X-Elite",
        "description": "Highest edge — tightest filters + 1.75:1 R:R",
        "ENTRY_AT_EXTREME": True,
        "SL_OFFSET_PIPS": 40,
        "MIN_RR": 1.75,
        "TIME_STOP_CANDLES": 4,
        "CONFIRM_BODY_MIN_PCT": 0.74,
        "RETREAT_BODY_MIN_PCT": 0.34,
        "RETREAT_BODY_MAX_PCT": 0.50,
    }
}


def set_strategy(name: str) -> None:
    """Apply a strategy preset by name. Call before run_backtest()."""
    preset = STRATEGY_PRESETS.get(name)
    if preset is None:
        raise ValueError(f"Unknown strategy: {name}. Available: {list(STRATEGY_PRESETS.keys())}")
    for key, value in preset.items():
        globals()[key] = value


def get_current_strategy() -> dict:
    """Return the current strategy config as a dict."""
    return {
        "ENTRY_AT_EXTREME": ENTRY_AT_EXTREME,
        "SL_OFFSET_PIPS": SL_OFFSET_PIPS,
        "MIN_RR": MIN_RR,
        "TIME_STOP_CANDLES": TIME_STOP_CANDLES,
        "CONFIRM_BODY_MIN_PCT": CONFIRM_BODY_MIN_PCT,
        "RETREAT_BODY_MIN_PCT": RETREAT_BODY_MIN_PCT,
        "RETREAT_BODY_MAX_PCT": RETREAT_BODY_MAX_PCT,
    }


def pips_to_price(pips: float, pair: str) -> float:
    return pips * PAIR_CONFIG[pair]["pip_value"]


def price_to_pips(price_diff: float, pair: str) -> float:
    return abs(price_diff / PAIR_CONFIG[pair]["pip_value"])


def analyse_setup(
    pd_candles: pd.DataFrame,
    session_candles: pd.DataFrame,
    pair: str
) -> SetupResult:
    """
    Plan-faithful impulse + pullback pattern:
    1. Strong impulse candle (body >= 70%) moving toward PDH/PDL
    2. Pullback candle (body >= 20%, <= 50%) that retraces the impulse
    3. Direction: impulse direction (toward PDH = LONG, toward PDL = SHORT)
    """
    if pd_candles.empty or session_candles.empty:
        return SetupResult(signal=Signal.SKIP, skip_reason="no_data", pd_high=0, pd_low=0, direction=None, entry_candle_idx=0)

    pip_value = PAIR_CONFIG[pair]["pip_value"]
    max_range_pips = PAIR_CONFIG[pair]["max_pd_range_pips"]

    pd_high = float(pd_candles["High"].max())
    pd_low = float(pd_candles["Low"].min())

    if price_to_pips(pd_high - pd_low, pair) > max_range_pips:
        return SetupResult(signal=Signal.SKIP, skip_reason="wide_pd_range", pd_high=pd_high, pd_low=pd_low, direction=None, entry_candle_idx=0)

    if len(session_candles) < 2:
        return SetupResult(signal=Signal.SKIP, skip_reason="no_data", pd_high=pd_high, pd_low=pd_low, direction=None, entry_candle_idx=0)

    for i in range(len(session_candles) - 1):
        imp = session_candles.iloc[i]
        imp_h, imp_l = float(imp["High"]), float(imp["Low"])
        imp_c, imp_o = float(imp["Close"]), float(imp["Open"])
        imp_r = imp_h - imp_l
        imp_b = abs(imp_c - imp_o)
        imp_bp = imp_b / imp_r if imp_r > 0 else 0

        if imp_r < pip_value:
            continue
        if imp_bp < CONFIRM_BODY_MIN_PCT:
            continue

        direction = None
        if imp_c > imp_o and imp_h >= pd_high - pip_value:
            direction = "LONG"
        elif imp_c < imp_o and imp_l <= pd_low + pip_value:
            direction = "SHORT"

        if direction is None:
            continue

        if i + 1 >= len(session_candles):
            continue

        pull = session_candles.iloc[i + 1]
        pull_h, pull_l = float(pull["High"]), float(pull["Low"])
        pull_c, pull_o = float(pull["Close"]), float(pull["Open"])
        pull_r = pull_h - pull_l
        pull_b = abs(pull_c - pull_o)
        pull_bp = pull_b / pull_r if pull_r > 0 else 0

        if pull_bp < RETREAT_BODY_MIN_PCT:
            continue
        if pull_bp > RETREAT_BODY_MAX_PCT:
            continue

        return SetupResult(
            signal=Signal.LONG if direction == "LONG" else Signal.SHORT,
            skip_reason=None,
            pd_high=pd_high, pd_low=pd_low, direction=direction,
            entry_candle_idx=i + 1,
            imp_body_pct=imp_bp,
            pull_body_pct=pull_bp,
            pull_high=pull_h,
            pull_low=pull_l,
        )

    return SetupResult(signal=Signal.SKIP, skip_reason="no_setup", pd_high=pd_high, pd_low=pd_low, direction=None, entry_candle_idx=0)


def calculate_entry(
    setup: SetupResult,
    session_candles: pd.DataFrame,
    pair: str
) -> Optional[TradeParams]:
    """
    Entry = pullback extreme (low for LONG, high for SHORT) if ENTRY_AT_EXTREME
            pullback candle close otherwise
    SL = 3 pips beyond pullback extreme
    TP = 2:1 R:R
    """
    if setup.signal == Signal.SKIP:
        return None

    pip_value = PAIR_CONFIG[pair]["pip_value"]
    pull_candle = session_candles.iloc[setup.entry_candle_idx]

    if ENTRY_AT_EXTREME:
        if setup.direction == "LONG":
            entry = setup.pull_low
            sl = setup.pull_low - SL_OFFSET_PIPS * pip_value
        else:
            entry = setup.pull_high
            sl = setup.pull_high + SL_OFFSET_PIPS * pip_value
    else:
        entry = float(pull_candle["Close"])
        if setup.direction == "LONG":
            sl = setup.pull_low - SL_OFFSET_PIPS * pip_value
        else:
            sl = setup.pull_high + SL_OFFSET_PIPS * pip_value

    risk = abs(entry - sl)
    tp_distance = risk * MIN_RR

    if setup.direction == "LONG":
        tp = entry + tp_distance
    else:
        tp = entry - tp_distance

    return TradeParams(
        entry=entry,
        stop_loss=sl,
        take_profit=tp,
        risk_reward=MIN_RR,
        direction=setup.direction,
        pd_high=setup.pd_high,
        pd_low=setup.pd_low,
    )


def simulate_trade(
    trade_params: TradeParams,
    post_candles: pd.DataFrame,
    pair: str,
    risk_pct: float = 1.0,
    max_candles: int = 18
) -> TradeResult:
    if trade_params is None or post_candles.empty:
        return TradeResult(
            exit_price=None,
            exit_reason=ExitReason.NONE,
            pips=0,
            pnl_pct=0,
            entry_time=None,
            exit_time=None,
            filled=False,
        )

    entry = trade_params.entry
    sl = trade_params.stop_loss
    tp = trade_params.take_profit
    direction = trade_params.direction
    pip_value = PAIR_CONFIG[pair]["pip_value"]
    spread_pips = PAIR_CONFIG[pair]["spread_pips"]
    spread_value = spread_pips * pip_value
    sl_slippage_value = 0.3 * pip_value

    if direction == "LONG":
        effective_entry = entry + spread_value
        effective_tp = tp + spread_value
        effective_sl = sl - spread_value - sl_slippage_value
    else:
        effective_entry = entry - spread_value
        effective_tp = tp - spread_value
        effective_sl = sl + spread_value + sl_slippage_value

    risk_pips = abs(effective_entry - effective_sl) / pip_value

    entry_time = None
    exit_price = None
    exit_reason = ExitReason.NONE
    candles_scanned = 0

    for i in range(len(post_candles)):
        candle = post_candles.iloc[i]
        high = float(candle["High"])
        low = float(candle["Low"])
        close = float(candle["Close"])
        candles_scanned += 1

        if entry_time is None:
            entry_time = candle.name
            if direction == "LONG":
                if low > entry:
                    continue
            else:
                if entry > high:
                    continue
            continue

        if direction == "LONG":
            if low <= effective_sl:
                exit_price = effective_sl
                exit_reason = ExitReason.SL
                break
            elif high >= effective_tp:
                exit_price = effective_tp
                exit_reason = ExitReason.TP
                break
        else:
            if high >= effective_sl:
                exit_price = effective_sl
                exit_reason = ExitReason.SL
                break
            elif low <= effective_tp:
                exit_price = effective_tp
                exit_reason = ExitReason.TP
                break

        if candles_scanned >= max_candles:
            exit_price = close
            exit_reason = ExitReason.TIME_STOP
            break

    if entry_time is None or exit_reason == ExitReason.NONE:
        return TradeResult(
            exit_price=None,
            exit_reason=ExitReason.LIMIT_NOT_REACHED,
            pips=0,
            pnl_pct=0,
            entry_time=entry_time,
            exit_time=None,
            filled=False,
        )

    if direction == "LONG":
        pips = (exit_price - effective_entry) / pip_value
    else:
        pips = (effective_entry - exit_price) / pip_value

    pnl_pct = (pips / risk_pips) * 100.0 * risk_pct if risk_pips > 0 else 0

    return TradeResult(
        exit_price=exit_price,
        exit_reason=exit_reason,
        pips=round(pips, 1),
        pnl_pct=round(pnl_pct, 4),
        entry_time=entry_time,
        exit_time=post_candles.index[-1] if exit_price else None,
        filled=True,
    )
