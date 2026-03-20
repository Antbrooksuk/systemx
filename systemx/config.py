PAIRS = ["EURUSD", "GBPUSD", "USDJPY", "EURJPY"]

PIP_SIZES = {
    "EURUSD": 0.0001,
    "GBPUSD": 0.0001,
    "USDJPY": 0.01,
    "EURJPY": 0.01,
}

ASIAN_RANGE_MAX_PIPS = {
    "EURUSD": 60,
    "GBPUSD": 80,
    "USDJPY": 70,
    "EURJPY": 100,
}

BREAKOUT_BODY_MIN_PCT = 0.60

RETEST_ZONE_PIPS = 3
RETEST_TIMEOUT_CANDLES = 4

SL_OFFSET_PIPS = 3
MIN_RR = 2.0
TIME_STOP_MINUTES = 30
RISK_PER_TRADE = 0.01

SESSIONS = {
    "asian": {"start": 0, "end": 7},
    "london": {"start": 8, "end": 10.5},
    "ny": {"start": 13, "end": 16.5}
}

STARTING_CAPITAL = 2000.0
