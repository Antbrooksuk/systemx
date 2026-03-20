# SYSTEM-X

Forex scalping bot using Mode X strategy. Real-time execution on OANDA practice account.

## Structure

```
systemx/         Strategy code (mode_b.py, backtest.py, etc.)
dashboard/       Next.js monitoring dashboard
trading_bot/     Live trading bot (FastAPI on port 8001)
docs/            Strategy documentation
```

## Setup

### VPS (Hetzner)

```bash
# Clone
git clone https://github.com/Antbrooksuk/systemx.git /opt/systemx
cd /opt/systemx

# Python env
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Configure
cp .env.example .env
nano .env  # add your OANDA_API_KEY and OANDA_ACCOUNT_ID

# Logging
mkdir -p /var/log/systemx
chmod 755 /var/log/systemx

# Install systemd service
cp trading_bot/systemd/systemx-bot.service /etc/systemd/system/
systemctl daemon-reload
systemctl enable systemx-bot
systemctl start systemx-bot

# Check status
curl http://127.0.0.1:8001/health
```

### Dashboard (local)

```bash
cd dashboard
npm install
npm run dev
# Open http://localhost:3000
```

### Updating

```bash
git pull origin master
source venv/bin/activate
pip install -r requirements.txt
systemctl restart systemx-bot
```

## Bot API

| Endpoint | Method | Returns |
|---|---|---|
| `http://127.0.0.1:8001/health` | GET | Bot alive, websocket status |
| `http://127.0.0.1:8001/status` | GET | Session, pairs, uptime |
| `http://127.0.0.1:8001/trades` | GET | All filled trades |
| `http://127.0.0.1:8001/orders` | GET | Open orders |
| `http://127.0.0.1:8001/equity` | GET | Account equity + P&L |

## Strategy

- Mode X-Plus: 64.4% WR, 2R, 2-pip SL, 4-candle time stop
- London: 08:00-10:00 UTC (EURUSD, GBPUSD)
- New York: 14:30-16:30 UTC (EURUSD, GBPUSD, USDJPY)
- Spread modeled: EURUSD 0.6pip, GBPUSD 1.2pip, USDJPY 0.7pip
