# Openclaw Build Tasks

## Phase 1: Local Build & Backtesting

### 1.1 Data Setup
- [x] Create `openclaw/data/` directory
- [x] Create `fetch_data.py` — download 60 days M5 data via yfinance
- [x] Run `fetch_data.py` to cache data as parquet files
- [x] Verify data integrity (EURUSD.parquet, GBPUSD.parquet, USDJPY.parquet)

### 1.2 Python Backend Core
- [ ] Create `config.py`:
  - [ ] PIP_SIZES, ASIAN_RANGE_MAX_PIPS per pair
  - [ ] BREAKOUT_BODY_MIN_PCT = 0.60
  - [ ] RETEST_ZONE_PIPS = 3, RETEST_TIMEOUT_CANDLES = 4
  - [ ] SL_OFFSET_PIPS = 3, MIN_RR = 2.0, TIME_STOP_MINUTES = 30
  - [ ] SESSIONS (asian 0-7, london 8-10.5, ny 13-16.5 GMT)
  - [ ] STARTING_CAPITAL = 2000, RISK_PER_TRADE = 0.01
- [ ] Create `mode_b.py`:
  - [ ] `analyse_setup()` — detect signal or skip with reason
    - [ ] Check Asian range width skip
    - [ ] Check breakout candle (close outside range, body ≥60%)
    - [ ] Detect retest within 4 candles (3-pip zone, directional close)
  - [ ] `calculate_entry()` — compute entry/SL/TP prices
    - [ ] Entry: retest candle close
    - [ ] SL: 3 pips beyond max(breakout extreme, retest extreme)
    - [ ] TP: opposite Asian extreme (min 2:1 R:R)
  - [ ] `simulate_trade()` — walk price series to exit
    - [ ] Check SL hit (conservative fill)
    - [ ] Check TP hit
    - [ ] Check time stop (30 min from entry)
    - [ ] Return exit_price, reason, pips, pnl_pct
- [ ] Rewrite `backtest.py`:
  - [ ] `load_data()` — read parquet files from data/
  - [ ] `extract_sessions()` — split day into Asian/London/NY
  - [ ] `get_asian_range()` — high/low for 00:00-07:00 GMT
  - [ ] `run_backtest()` — main loop over all days/sessions/pairs
  - [ ] Equity curve calculation with compounding
  - [ ] Return results matching dashboard API format
- [ ] Update `main.py`:
  - [ ] Wire to new backtest.py
  - [ ] Remove synthetic.py imports
- [ ] Delete `synthetic.py`

### 1.3 Next.js Dashboard
- [x] Initialize Next.js 14 app in `openclaw/dashboard/`
- [x] Install dependencies (tailwind, recharts)
- [x] Build components:
  - [x] `StatCard.tsx` — single KPI display
  - [x] `EquityCurve.tsx` — Recharts line chart
  - [x] `TradeLog.tsx` — scrollable trade table
  - [x] `SessionBreakdown.tsx` — per-session/pair stats
- [x] Build hooks:
  - [x] `useBacktest.ts` — state management for trades/equity
- [x] Build API layer:
  - [x] `api.ts` — REST fetch + WebSocket connection
- [x] Build main `page.tsx` — assemble dashboard layout
- [x] Dark theme styling
- [ ] Test dashboard with real backtest data

### 1.4 Backtesting & Validation (Real Data)
- [ ] Run full 60-day backtest with real yfinance data
- [ ] Verify win rate ≥71%
- [ ] Verify avg R:R ≥1.85
- [ ] Verify max drawdown <15%
- [ ] Verify skip rate ~60-70%
- [ ] Verify sample size 240-360 trade opportunities
- [ ] Check all 4 skip rules firing correctly:
  - [ ] Wide Asian range
  - [ ] Weak breakout candle (body <60%)
  - [ ] Choppy first candle
  - [ ] No clean retest within 4 candles
- [ ] Check time stop resolving in 30 min
- [ ] Review equity curve shape (realistic volatility, not fantasy returns)

### 1.5 Documentation
- [ ] Update README with run instructions
- [ ] Document API endpoints
- [ ] Document config parameters

---

## Phase 2: Paper Trading (After Phase 1 Complete)

### 2.1 OANDA Integration
- [ ] Set up OANDA demo account
- [ ] Install oandapyV20
- [ ] Build `oanda_client.py`:
  - [ ] Connect to OANDA API
  - [ ] Fetch live M5 candles
  - [ ] Stream price updates
- [ ] Modify `mode_b.py` to accept live data
- [ ] Add SQLite logging for paper trades

### 2.2 Dashboard Updates
- [ ] Add SQLite read capability
- [ ] Add live/paper mode toggle
- [ ] Show real-time trade status

### 2.3 Paper Trading Validation
- [ ] Run 30-50 paper trades
- [ ] Compare win rate to backtest
- [ ] Verify execution timing

---

## Phase 3: Go Live (After Phase 2 Complete)

### 3.1 OANDA Live Setup
- [ ] Fund OANDA with £2,000
- [ ] Switch to live API credentials
- [ ] Set risk to 0.5% (£10/trade)

### 3.2 Deployment to Openclaw Server
- [ ] SSH into openclaw server
- [ ] Check existing stack (Docker vs bare metal)
- [ ] Set up deployment (git pull + restart)
- [ ] Deploy backend (uvicorn service)
- [ ] Deploy frontend (build + serve or Vercel)
- [ ] Configure environment variables
- [ ] Test remote access

### 3.3 Monitoring & Reporting
- [ ] Daily P&L markdown report
- [ ] Telegram/email alerts on trade completion
- [ ] Health check endpoint
- [ ] Log rotation

### 3.4 Go Live Checklist
- [ ] Start at 0.5% risk (£10)
- [ ] Monitor first 10 trades
- [ ] After 30 trades with ≥71% win rate → increase to 1% risk
- [ ] Weekly review and adjustment

---

## Notes

- **Deployment target**: Existing openclaw server (git-based deploy)
- **Win rate target**: 71%
- **Sample size**: 240-360 trade opportunities (60 days × 3 pairs × 2 sessions)
- **Data source**: yfinance cached in repo (data/*.parquet)
- **Charting**: Recharts
- **Config**: All parameters in config.py (tunable after 100+ trades)
