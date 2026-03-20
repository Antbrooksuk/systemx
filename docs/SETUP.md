# SYSTEM-X Trading Setup

## Overview

SYSTEM-X is a forex scalping bot that trades a momentum-pullback pattern during two high-liquidity daily sessions. It runs on a Hetzner VPS and is monitored via a local Next.js dashboard.

- **Broker:** OANDA (practice account)
- **Account:** £100,000 GBP
- **Pairs:** EURUSD, GBPUSD, USDJPY, EURJPY (EURJPY in backtest bench, pending live)
- **Sessions:** London 08:00–10:00 UTC, NY 14:30–16:30 UTC
- **Strategy:** Mode X — impulse candle + pullback candle + limit entry + SL/TP + 4-candle time stop
- **Framework:** Python/FastAPI bot, Next.js dashboard

---

## Architecture

```
[OANDA API]
     |
     v
[Hetzner VPS: port 8001]
  trading_bot/main.py (FastAPI)
  ├── oanda.py         Raw httpx REST client
  ├── orders.py        Order placement + SL/TP management
  ├── state.py         In-memory trade/order state
  ├── session.py       Session timing (London/NY)
  ├── strategy.py      run_signal() → mode_b.py
  └── log_config.py    Logging to /opt/systemx/logs/bot.log
          |
          v (polls every 5s)
[Dashboard: http://localhost:3000]
  /           Backtest tab
  /live       Live trading tab
```

---

## Bot (trading_bot/)

### Poll loop (every 30s)

1. `check_and_manage_orders()` — sync pending orders, expire after 4 M5 candles (20min)
2. `check_closed_trades()` — fetch closed trade history, log exits
3. If in session window → `check_session_signals()` — run strategy for session pairs

### Session timing

| Session | Time (UTC) | Pairs |
|---|---|---|
| London | 08:00–10:00 | EURUSD, GBPUSD |
| NY | 14:30–16:30 | EURUSD, GBPUSD, USDJPY, EURJPY |

### Order flow

1. Strategy generates signal (entry, SL, TP, direction)
2. `place_entry()` → OANDA LIMIT order with SL/TP attached
3. Order expires after 4 M5 candles if not filled
4. Filled trade → tracked in `state.filled_trades`
5. Closed trade (TP/SL) → logged with P&L

### OANDA symbol mapping

| Internal | OANDA API |
|---|---|
| EURUSD | EUR_USD |
| GBPUSD | GBP_USD |
| USDJPY | USD_JPY |
| EURJPY | EUR_JPY |

### Spread assumptions

| Pair | Spread |
|---|---|
| EURUSD | 0.6 pip |
| GBPUSD | 1.2 pip |
| USDJPY | 0.7 pip |
| EURJPY | 1.0 pip |

---

## Strategy (systemx/mode_b.py)

### Entry rules

- C1: impulse candle, body ≥ 70% of range, direction toward PDH/PDL extreme
- C2: pullback candle immediately after C1, body 20–50%, does NOT fully retrace C1
- Entry: LIMIT at C2 extreme (C2.low for longs, C2.high for shorts)
- SL: entry ± 3 pips (X-Base) or ± 2 pips (X-Plus, X-Elite)
- TP: entry + 2R (X-Base/X-Plus) or + 1.75R (X-Elite)

### Time stop

- Trade not filled within 4 M5 candles after C2 → cancelled, no trade
- Trade filled but TP/SL not hit by close of 4th candle after entry → exit at candle close

### Mode variants

| Mode | SL | TP | Filters |
|---|---|---|---|
| X-Base | 3 pip | 2R | Standard |
| X-Plus | 2 pip | 2R | Tighter pullback (≥34%) |
| X-Elite | 2 pip | 1.75R | Tightest filters, highest skip rate |

### Backtest results (Jan 2025 – Mar 2026, spread + slippage modeled, 3 pairs)

| Strategy | WR | Final £ | Max DD | Trades | Skip % |
|---|---|---|---|---|---|
| X-Base | 61.6% | £10,644 | 6.2% | 477 | 66% |
| X-Plus | 64.4% | £4,892 | 4.9% | 298 | 78% |
| X-Elite | 64.7% | £3,652 | 5.1% | 255 | 81% |

X-Base wins on total P&L due to higher trade volume. All modes are profitable.
EURJPY added to backtest bench — pending re-run with new data download.

---

## Dashboard (dashboard/)

### Backtest tab (`/`)

- Strategy dropdown (X-Base, X-Plus, X-Elite)
- Capital selector (£1K–£10K)
- Risk selector (0.5%–2%)
- Run Backtest / Stream buttons
- Equity curve, trade log, session breakdown

### Live tab (`/live`)

- Session clock (name, pairs, countdown)
- Account panel (balance, equity, unrealized P&L)
- Current signal display (entry/SL/TP/RR)
- Active orders table
- Open trades table
- Polls bot every 5 seconds

---

## VPS Setup

### Server

- **Provider:** Hetzner
- **IP:** 204.168.130.153
- **OS:** Ubuntu
- **User:** openclaw
- **Bot port:** 8001

### Install

```bash
git clone https://github.com/Antbrooksuk/systemx.git /opt/systemx
cd /opt/systemx
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
nano .env  # OANDA_API_KEY, OANDA_ACCOUNT_ID, OANDA_ENV=demo

mkdir -p logs

sudo cp trading_bot/systemd/systemx-bot.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable systemx-bot
sudo systemctl start systemx-bot
```

### Updating

```bash
cd /opt/systemx && git pull && sudo systemctl restart systemx-bot
```

### Logs

```
/opt/systemx/logs/bot.log
```

---

## Bot API Endpoints

| Endpoint | Description |
|---|---|
| `GET /health` | Bot alive, uptime, started_at |
| `GET /status` | Session info, account (balance/equity/unrealized_pl), active orders, filled trades, total P&L % |
| `GET /trades` | All filled trades |
| `GET /orders` | Pending orders |
| `GET /candles?pair=EURUSD&count=20` | Live M5 candles |
| `GET /signal?pair=EURUSD` | Current strategy signal |
| `GET /equity` | Account equity + P&L |

All endpoints return JSON.

---

## Current Status

- Bot deployed and running on VPS via systemd ✅
- `/candles` and `/signal` returning live OANDA data ✅
- Dashboard Live tab connecting to VPS bot ✅
- Practice trading active — paper only, no real money ✅
- Systemd auto-restart configured ✅
- LIVE indicator shows bot is running

---

## Next Steps

1. **Monitor NY session** — bot will auto-trade from 14:30 UTC today
2. **Install systemd** on VPS if not already done
3. **Watch the Live tab** during a session to verify order placement
4. **Add trade alerts** — Slack/Discord notifications on fills and closes
5. **Go live** — switch `OANDA_ENV=demo` → `live` when paper trading is validated
