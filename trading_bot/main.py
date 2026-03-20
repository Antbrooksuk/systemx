"""SYSTEM-X Trading Bot — FastAPI server (port 8001)."""
import sys
import threading
import time
from datetime import datetime
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent / "systemx"))

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import pandas as pd

from trading_bot.oanda import OANDAClient
from trading_bot.orders import OrderManager
from trading_bot.session import get_current_session, session_seconds_remaining, candle_countdown
from trading_bot.state import state, BotState
from trading_bot.log_config import log

sys.path.insert(0, str(Path(__file__).parent))
from strategy import run_signal

app = FastAPI(title="SYSTEM-X Trading Bot")
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

client = OANDAClient()
order_manager = OrderManager(client)
running = True
poll_thread: threading.Thread | None = None


def poll_loop():
    while running:
        try:
            order_manager.check_and_manage_orders()
            order_manager.check_closed_trades()

            current_session = get_current_session()
            if current_session:
                check_session_signals(current_session)

        except Exception as e:
            log.error(f"Poll error: {e}")

        time.sleep(30)


def check_session_signals(session):
    for pair in session.pairs:
        try:
            df = client.get_candles_df(pair, count=50)
            if df.empty:
                continue

            pd_candles = df.iloc[:-5].copy() if len(df) > 5 else df.copy().iloc[:0]
            session_candles = df.copy()

            signal = run_signal(pd_candles, session_candles, pair)

            if signal["signal"] in ("LONG", "SHORT"):
                state.current_signal = signal

                has_existing = any(
                    o.pair == pair
                    for o in list(state.active_orders.values())
                )
                if has_existing:
                    log.info(f"Signal {pair} {signal['signal']} — already has open order")
                    continue

                order_id = order_manager.place_entry(
                    pair=pair,
                    direction=signal["direction"],
                    entry_price=signal["entry"],
                    sl_price=signal["sl"],
                    tp_price=signal["tp"],
                    session=session.name,
                )
                if order_id:
                    state.current_signal = None

        except Exception as e:
            log.error(f"Signal check error for {pair}: {e}")


@app.on_event("startup")
def startup():
    global poll_thread, running
    log.info("SYSTEM-X Bot starting up...")
    running = True
    poll_thread = threading.Thread(target=poll_loop, daemon=True)
    poll_thread.start()
    log.info("Poll thread started")


@app.on_event("shutdown")
def shutdown():
    global running
    running = False
    log.info("SYSTEM-X Bot shutting down...")


@app.get("/health")
def health():
    return {
        "status": "ok",
        "uptime_seconds": (datetime.utcnow() - state.started_at).total_seconds(),
        "websocket_connected": state.websocket_connected,
        "last_candle_time": state.last_candle_time.isoformat() if state.last_candle_time else None,
        "started_at": state.started_at.isoformat(),
    }


@app.get("/status")
def status():
    current_session = get_current_session()
    session_info = None
    if current_session:
        session_info = {
            "name": current_session.name,
            "pairs": current_session.pairs,
            "seconds_remaining": session_seconds_remaining(current_session, datetime.utcnow()),
            "candle_countdown": candle_countdown(datetime.utcnow()),
        }

    try:
        account = client.get_account()
        account_info = {
            "balance": account.balance,
            "equity": account.equity,
            "currency": account.currency,
        }
    except Exception:
        account_info = None

    return {
        "session": session_info,
        "active_orders": len(state.active_orders),
        "filled_trades": len(state.filled_trades),
        "total_pnl_pct": round(state.total_pnl_pct, 2),
        "uptime_seconds": int((datetime.utcnow() - state.started_at).total_seconds()),
        "account": account_info,
        "current_signal": state.current_signal,
    }


@app.get("/trades")
def trades():
    return {"trades": state.get_trades()}


@app.get("/orders")
def orders():
    return {"orders": state.get_orders()}


@app.get("/candles")
def candles(pair: str = "EURUSD", count: int = 20):
    try:
        df = client.get_candles_df(pair, count=count)
        if df.empty:
            return {"pair": pair, "candles": []}
        candles_data = []
        for idx, row in df.iterrows():
            candles_data.append({
                "time": idx.isoformat(),
                "open": row["Open"],
                "high": row["High"],
                "low": row["Low"],
                "close": row["Close"],
                "volume": int(row.get("Volume", 0)),
            })
        return {"pair": pair, "candles": candles_data}
    except Exception as e:
        return {"pair": pair, "error": str(e), "candles": []}


@app.get("/signal")
def signal(pair: str = "EURUSD"):
    try:
        df = client.get_candles_df(pair, count=50)
        if df.empty:
            return {"pair": pair, "signal": "NO_DATA"}

        pd_candles = df.iloc[:-5].copy() if len(df) > 5 else df.copy().iloc[:0]
        session_candles = df.copy()

        sig = run_signal(pd_candles, session_candles, pair)
        return {"pair": pair, **sig}
    except Exception as e:
        return {"pair": pair, "signal": "ERROR", "error": str(e)}


@app.get("/equity")
def equity():
    try:
        account = client.get_account()
        return {
            "balance": account.balance,
            "equity": account.equity,
            "unrealized_pl": account.unrealized_pl,
            "currency": account.currency,
            "total_pnl_pct": round(state.total_pnl_pct, 2),
        }
    except Exception as e:
        return {"error": str(e)}


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)
