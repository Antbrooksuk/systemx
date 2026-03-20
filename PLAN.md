# Openclaw — Mode B Simulator & Dashboard Spec

> **Mechanical forex session scalper with historical backtesting and live dashboard.
> Validate the edge before risking a penny.**

---

## Overview

Openclaw trades two forex session opens per day using a mechanical
price-action setup. Before going live, every rule is stress-tested through
historical backtesting using real M5 data. A Next.js dashboard presents results.

**No sentiment. No LLM. Pure price action.**

---

## Trading Logic — Session Scalp

### Concept

Each trading day has two high-probability windows: London open and NY open.
The previous day's high/low acts as a magnet for price. Openclaw waits for
price to revisit that zone, then enters on a strong retest confirmation.
Only trades the first 90 minutes of each session window.

### Sessions

| Session      | Window (ET)    | Window (GMT)   | Pairs                       |
| ------------ | -------------- | -------------- | --------------------------- |
| London open  | 03:00–04:30    | 08:00–09:30    | EUR/USD, GBP/USD            |
| NY open      | 09:30–11:00    | 14:30–16:00    | EUR/USD, GBP/USD, USD/JPY   |
| Dead zone    | 11:00–03:00    | 16:00–08:00    | No trades                   |

### 5-Step Trade Rule

1. **Reference** — Measure previous day's 24h high and low
2. **Session open** — Watch the first candle at session open (08:00 GMT / 14:30 GMT)
3. **In-range check** — Confirm price has moved into or through the previous day's range
4. **Retest confirmation** — Wait for price to pull back to the reference zone, then enter on strong PA candle
5. **Manage** — TP / SL / 90-min time stop

### Skip Conditions (No Trade)

| Rule                 | Threshold                                  |
| -------------------- | ------------------------------------------ |
| No in-range move     | Session open candle closes outside PD range |
| Weak retest          | Retest candle has <60% body                |
| No clear PA confirm  | No candle confirms direction after retest  |
| Range too wide       | PD range >80 pips (EUR/USD), >100 (others) |

### Trade Parameters

| Parameter   | Value                                 |
| ----------- | ------------------------------------- |
| Entry       | Retest confirmation candle close      |
| Stop loss   | 3 pips beyond retest candle low/high  |
| Take profit | 2× risk (min 2:1 R:R)                |
| Time stop   | 90 minutes from session open          |
| Risk/trade  | 1% of current account (compounding)   |
| Max trades  | 1 per session per pair                |

---

## Account & Compounding Model

| Week | Stake/Trade | Expected Weekly P&L |
| ---- | ----------- | ------------------- |
| 1    | £20         | £61                 |
| 13   | £29         | £88                 |
| 26   | £43         | £131                |
| 52   | £94         | £287                |

Starting capital £2,000 → ~£9,600 end of year (expected value, 71% win rate, 1.85 R:R).
Risk is always 1% of current account — compounding is automatic.

---

## Backtesting

Tests every aspect of the logic against real historical price data.

### Data Source

- **Provider**: Yahoo Finance (yfinance)
- **Pairs**: EUR/USD, GBP/USD, USD/JPY
- **Timeframe**: 5-minute candles (M5)
- **Period**: Last 60 days (yfinance M5 limit)
- **Expected trades**: ~240-360 trade opportunities (after skips filtered)

### Backtest Workflow

1. **Fetch M5 data** for all three pairs via yfinance
2. **Identify trading days** in the 60-day period
3. **For each day and session:**
   - Extract previous day's data → measure 24h high/low
   - Extract London window (08:00-09:30 GMT)
   - Extract NY window (14:30-16:00 GMT)
4. **Apply strategy logic** to each session:
   - Check if session open candle moves into PD range
   - Detect retest and PA confirmation
   - Simulate trade to exit (TP/SL/time stop)
5. **Record outcomes**: entry, exit, pips, win/loss/skip, R:R
6. **Aggregate** across all trades

### Output Metrics

| Metric       | Target    | Notes                           |
| ------------ | --------- | ------------------------------- |
| Win rate     | ≥71%      | PLAN target                     |
| Avg R:R      | ≥1.85     | PLAN target                     |
| Max drawdown | <15%      | Peak-to-trough equity           |
| Sample size  | ≥1000     | Trade opportunities scanned     |
| Skip rate    | ~60-70%   | Expected from skip conditions   |

---

## Architecture

```
openclaw/
│
├── mode_b.py          # Pure trade logic (no broker, no I/O)
│   ├── analyse_setup()     → Signal or skip + reason
│   ├── calculate_entry()   → Entry / SL / TP
│   └── simulate_trade()    → Walk price series, resolve exit
│
├── backtest.py        # Historical data fetch + backtest runner
│   ├── fetch_data()        → Download M5 data via yfinance
│   ├── extract_sessions()  → Split data into trading sessions
│   └── run_backtest()      → Run strategy over historical data
│
├── main.py            # FastAPI — serves dashboard + WebSocket stream
│   ├── GET  /backtest              → Run full backtest
│   ├── GET  /backtest/stream       → WebSocket stream with delay
│   ├── GET  /status                → Bot/sim status
│   └── POST /reset                 → Clear state, reset to £2,000
│
├── requirements.txt
│
└── dashboard/         # Next.js 14 + TypeScript + Tailwind
    ├── app/
    │   └── page.tsx           # Main dashboard page
    ├── components/
    │   ├── StatCard.tsx       # KPI stat cards
    │   ├── EquityCurve.tsx    # Recharts equity chart
    │   ├── TradeLog.tsx       # Scrollable trade history table
    │   └── SessionBreakdown.tsx  # Per-session/pair performance
    ├── hooks/
    │   └── useBacktest.ts     # State hook (trades, equity, running)
    ├── lib/
    │   └── api.ts             # REST + WebSocket calls to FastAPI
    ├── .env.local
    └── package.json
```

---

## Dashboard Layout

```
┌──────────────────────────────────────────────────────────────────────┐
│ 🦅 OPENCLAW   MODE B — SESSION SCALP    [Run Backtest] [Reset]       │
├──────────────────────────────────────────────────────────────────────┤
│  Trades │  Wins  │ Losses │ Win Rate │ Account │  P&L  │ ROI │ MaxDD│
├──────────────────────────────────────────────────────────────────────┤
│                     EQUITY CURVE (Recharts)                          │
├──────────────────────────────────────────────────────────────────────┤
│   SESSION BREAKDOWN              │          TRADE LOG                │
│                                  │                                   │
│  London: W/L/Skip   NY: W/L/Skip │  # | Date | Pair | Dir | P&L     │
│  EUR/USD: ...                    │  ← scrollable, newest at top      │
│  GBP/USD: ...                    │                                   │
│  USD/JPY: ...                    │                                   │
└──────────────────────────────────────────────────────────────────────┘
```

Dark theme. Monospace font for all prices and numbers.
Green = TP / profit. Red = SL / loss. Amber = skip.

### Dashboard Controls

| Button       | Action                                              |
| ------------ | --------------------------------------------------- |
| Run Backtest | Fetches data, runs full 60-day backtest, shows stats|
| Stream       | Runs backtest with 400ms delay per trade (WebSocket)|
| Reset        | Clears all state, back to £2,000                    |

### Session Breakdown

- Win/Loss/Skip counts per session (London vs NY)
- Win/Loss/Skip counts per pair (EUR/USD, GBP/USD, USD/JPY)
- Helps identify which sessions/pairs perform best

---

## Tech Stack

| Layer          | Tool                               |
| -------------- | ---------------------------------- |
| Trade logic    | Python 3.11+ (pure functions)      |
| Data fetch     | yfinance (Yahoo Finance)           |
| API server     | FastAPI + uvicorn                  |
| Realtime       | WebSocket (FastAPI native)         |
| Frontend       | Next.js 14 + TypeScript + Tailwind |
| Charts         | Recharts                           |
| Storage        | In-memory during simulation        |
| Deployment     | Git-based to openclaw server       |
| Broker (live)  | OANDA v20 REST API (oandapyV20)    |

---

## How to Run

```bash
# Backend
cd openclaw
pip install -r requirements.txt
uvicorn main:app --reload --port 8000

# Dashboard
cd openclaw/dashboard
npm install
npm run dev
# → http://localhost:3000
```

---

## Validation Gate (Backtest → Paper Trading → Live)

All thresholds must be met before connecting to OANDA:

| Metric       | Threshold         |
| ------------ | ----------------- |
| Win rate     | ≥ 71%             |
| Sample size  | ≥ 1000 trades     |
| Avg R:R      | ≥ 1.85            |
| Max drawdown | < 15% of account  |
| All 4 skips  | Firing correctly  |
| Time stop    | Resolving cleanly |

Once all pass: wire `mode_b.py` to OANDA demo account for paper trading,
then deploy to openclaw server, fund with £2,000, start at 0.5% risk for
first 2 weeks.

---

## Phase Plan

### Phase 1 — Backtesting (Now)

- [ ] Rewrite `mode_b.py` — new PD-range strategy
- [ ] Update `backtest.py` — fetch + store previous day data
- [ ] Update `main.py` — FastAPI + WebSocket
- [ ] Dashboard — equity curve, trade log, session breakdown
- [ ] Run full 60-day backtest, confirm ≥71% win rate
- [ ] Verify skip rules fire as expected
- [ ] Verify SL and time stop resolve correctly

### Phase 2 — Paper Trading

- [ ] Connect `mode_b.py` to OANDA demo account
- [ ] Replace historical prices with live M5 candles
- [ ] Run 30–50 paper trades, log results to SQLite
- [ ] Dashboard reads from SQLite instead of in-memory
- [ ] Validate live win rate matches backtest

### Phase 3 — Go Live

- [ ] Fund OANDA with £2,000
- [ ] Start at 0.5% risk per trade (£10)
- [ ] Move to 1% after 30 live trades above 71% win rate
- [ ] Daily markdown report auto-generated
- [ ] Dashboard deployed to openclaw server, accessible remotely
