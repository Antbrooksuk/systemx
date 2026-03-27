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
from trading_bot.session import get_current_session, session_seconds_remaining, candle_countdown, get_session_start_dt, get_session_end_dt
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


SESSION_REPORT_FILE = Path(__file__).parent / "session_reports.txt"

def write_session_report(session_name: str):
    """Write permanent session report to file"""
    try:
        session_trades = [t for t in state.filled_trades if t.session == session_name]
        
        wins = [t for t in session_trades if t.pnl_pct > 0]
        losses = [t for t in session_trades if t.pnl_pct < 0]
        skips = [t for t in session_trades if t.direction == "SKIP"]
        
        total_pnl = sum(t.pnl_pct for t in session_trades)
        
        with open(SESSION_REPORT_FILE, "a") as f:
            f.write(f"\n{'='*60}\n")
            f.write(f"SESSION REPORT - {session_name} - {datetime.utcnow().isoformat()}\n")
            f.write(f"{'='*60}\n")
            
            f.write(f"Trades: {len(session_trades)} (wins: {len(wins)}, losses: {len(losses)}, skips: {len(skips)})\n")
            f.write(f"P&L: {total_pnl:.2f}%\n\n")
            
            for t in session_trades:
                f.write(f"  - {t.pair} {t.direction} {t.exit_reason} pnl={t.pnl_pct:.2f}%\n")
            
            f.write(f"\nBot Uptime: {int((datetime.utcnow() - state.started_at).total_seconds())}s\n")
    except Exception as e:
        log.error(f"Failed to write session report: {e}")


def poll_loop():
    last_session = None
    while running:
        try:
            current_session = get_current_session()
            session_name = current_session.name if current_session else "live"
            order_manager.check_and_manage_orders(session=session_name)
            order_manager.check_closed_trades(session=session_name)

            if current_session:
                check_session_signals(current_session)
                
            # Check if session ended
            if last_session and current_session is None:
                write_session_report(last_session.name)
                
            last_session = current_session

        except Exception as e:
            log.error(f"Poll error: {e}")

        time.sleep(30)


def check_session_signals(session):
    from trading_bot.state import FilledTrade
    
    log.info(f"=== SESSION CHECK: {session.name} ===")
    
    if getattr(state, "_last_checked_session", None) != session.name:
        state.checked_pairs = set()
        state._last_checked_session = session.name
        state.clear_session_trades()
        log.info(f"=== NEW SESSION START: {session.name} ===")
    
    now = datetime.utcnow()
    session_start_dt = pd.Timestamp(get_session_start_dt(session, now)).tz_localize("UTC")
    
    for pair in session.pairs:
        log.info(f"--- Checking {pair} ---")
        try:
            df = client.get_candles_df(pair, count=200, granularity="M5")
            if df.empty:
                log.warning(f"{pair}: No candle data")
                continue

            df = df.sort_index()
            
            session_candles = df[df.index >= session_start_dt].copy()
            
            pd_candles = df[(df.index < session_start_dt)].copy()
            if len(pd_candles) < 10:
                log.info(f"{pair}: SKIP - insufficient previous day data")
                continue

            if session_candles.empty:
                log.info(f"{pair}: SKIP - no session candles yet")
                continue

            session_end_dt = get_session_end_dt(session, now)
            session_end_ts = pd.Timestamp(session_end_dt).tz_localize("UTC")
            window_open_candles = session_candles[(session_candles.index >= session_start_dt) & (session_candles.index < session_end_ts)]
            
            now_ts = pd.Timestamp(now).tz_localize("UTC")
            minutes_since_open = (now_ts - session_start_dt).total_seconds() / 60
            log.info(f"{pair}: minutes_since_open={minutes_since_open:.1f}, window_end={session_end_ts}")
            if minutes_since_open >= 90:
                log.info(f"{pair}: SKIP - 90-min window expired")
                continue

            if window_open_candles.empty:
                log.info(f"{pair}: SKIP - no window candles")
                continue

            signal = run_signal(pd_candles, window_open_candles, pair)
            
            log.info(f"{pair}: Signal={signal['signal']}, reason={signal.get('reason', 'N/A')}")

            if signal["signal"] == "SKIP":
                log.info(f"{pair}: SKIPPED - {signal.get('reason', 'no signal')}")
                already_recorded = any(
                    t.pair == pair and t.exit_reason == "SKIP"
                    for t in state.filled_trades
                )
                if not already_recorded:
                    state.add_trade(FilledTrade(
                        pair=pair,
                        session=session.name,
                        direction="SKIP",
                        units=0,
                        entry_time=datetime.utcnow(),
                        entry_price=0,
                        sl_price=0,
                        tp_price=0,
                        exit_time=datetime.utcnow(),
                        exit_price=0,
                        exit_reason=signal.get('reason', 'SKIP'),
                        pips=0,
                        pnl_pct=0,
                        oanda_trade_id=f"skip_{pair}_{session.name}",
                    ))

            if signal["signal"] in ("LONG", "SHORT"):
                state.current_signal = signal
                log.info(f"{pair}: {signal['signal']} at {signal.get('entry_formatted', 'N/A')} (SL:{signal.get('sl_formatted', 'N/A')} TP:{signal.get('tp_formatted', 'N/A')})")

                has_existing = any(
                    o.pair == pair
                    for o in list(state.active_orders.values())
                )
                if has_existing:
                    log.info(f"{pair}: SKIP - already has open order in state")
                    state.current_signal = None
                    continue

                try:
                    open_trades = client.get_open_trades()
                    pending_orders = client.get_orders()
                    has_open = any(
                        OANDAClient.from_oanda_symbol(t.get("instrument", "")) == pair
                        for t in open_trades
                    )
                    has_pending_oanda = any(
                        OANDAClient.from_oanda_symbol(o.get("instrument", "")) == pair
                        for o in pending_orders
                    )
                    log.info(f"{pair}: OANDA check - has_open={has_open}, has_pending={has_pending_oanda}")
                except Exception as e:
                    log.warning(f"Could not check open trades for idempotency: {e}")
                    has_open = False
                    has_pending_oanda = False

                if has_pending_oanda:
                    log.info(f"{pair}: SKIP - pending order exists in OANDA")
                    state.current_signal = None
                    continue
                    
                if has_open:
                    log.info(f"{pair}: SKIP - open trade exists in OANDA")
                    state.mark_pair_traded(session.name, pair)
                    state.current_signal = None
                    continue
                    
                if state.has_pair_traded(session.name, pair):
                    log.info(f"{pair}: SKIP - already traded in session {session.name}")
                    state.current_signal = None
                    continue

                log.info(f"=== ORDER PLACED: {pair} {signal['direction']} entry={signal['entry']} SL={signal['sl']} TP={signal['tp']} ===")
                order_id = order_manager.place_entry(
                    pair=pair,
                    direction=signal["direction"],
                    entry_price=signal["entry"],
                    sl_price=signal["sl"],
                    tp_price=signal["tp"],
                    session=session.name,
                )
                if order_id:
                    log.info(f"=== ORDER SUCCESS: {order_id} {pair} {signal['direction']} ===")
                    state.mark_pair_traded(session.name, pair)
                    state.current_signal = None
                else:
                    log.error(f"=== ORDER FAILED: {pair} ===")

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
            "unrealized_pl": account.unrealized_pl,
            "currency": account.currency,
        }
        STARTING_BALANCE = 2000.0
        total_pnl_pct = round((account.balance - STARTING_BALANCE) / STARTING_BALANCE * 100, 2)
    except Exception:
        account_info = None
        total_pnl_pct = 0.0

    # Get session trade summary
    session_summary = {}
    for trade in state.filled_trades:
        if trade.session not in session_summary:
            session_summary[trade.session] = {"trades": 0, "skips": 0, "wins": 0, "losses": 0, "pnl": 0.0}
        if trade.direction == "SKIP":
            session_summary[trade.session]["skips"] += 1
        else:
            session_summary[trade.session]["trades"] += 1
            if trade.pnl_pct > 0:
                session_summary[trade.session]["wins"] += 1
            else:
                session_summary[trade.session]["losses"] += 1
            session_summary[trade.session]["pnl"] += trade.pnl_pct

    return {
        "session": session_info,
        "active_orders": len(state.active_orders),
        "filled_trades": len(state.filled_trades),
        "total_pnl_pct": total_pnl_pct,
        "uptime_seconds": int((datetime.utcnow() - state.started_at).total_seconds()),
        "account": account_info,
        "current_signal": state.current_signal,
        "session_traded_pairs": list(state.session_traded_pairs),
        "session_summary": session_summary,
    }


@app.get("/report")
def full_report():
    """Full detailed report of all trades, skips, and decisions"""
    
    # Get OANDA state
    try:
        oanda_orders = client.get_orders()
        oanda_trades = client.get_open_trades()
    except:
        oanda_orders = []
        oanda_trades = []
    
    # Build detailed trade list
    trades_detail = []
    for t in state.filled_trades:
        trades_detail.append({
            "pair": t.pair,
            "session": t.session,
            "direction": t.direction,
            "entry_price": t.entry_price,
            "exit_price": t.exit_price,
            "exit_reason": t.exit_reason,
            "pips": t.pips,
            "pnl_pct": t.pnl_pct,
            "entry_time": t.entry_time.isoformat() if t.entry_time else None,
            "exit_time": t.exit_time.isoformat() if t.exit_time else None,
        })
    
    # Recent activity log
    recent_logs = []
    try:
        log_path = Path(__file__).parent / "logs" / "bot.log"
        if log_path.exists():
            with open(log_path) as f:
                lines = f.readlines()
                recent_logs = [l.strip() for l in lines[-100:]]
    except:
        pass
    
    return {
        "bot_uptime_seconds": int((datetime.utcnow() - state.started_at).total_seconds()),
        "current_session": get_current_session().name if get_current_session() else None,
        "session_traded_pairs": list(state.session_traded_pairs),
        "active_orders_in_state": len(state.active_orders),
        "pending_orders_in_oanda": len(oanda_orders),
        "open_trades_in_oanda": len(oanda_trades),
        "trades_history": trades_detail,
        "recent_logs": recent_logs,
    }


@app.get("/session-reports")
def get_session_reports():
    """Get permanent session reports as text"""
    try:
        if SESSION_REPORT_FILE.exists():
            with open(SESSION_REPORT_FILE, "r") as f:
                content = f.read()
        else:
            content = "No session reports yet."
    except Exception as e:
        content = f"Error reading reports: {e}"
    
    return {"reports": content}


@app.get("/trades")
def trades():
    return {"trades": state.get_trades()}


@app.get("/orders")
def orders():
    return {"orders": state.get_orders()}


@app.get("/oanda-trades")
def oanda_trades():
    try:
        closed = client.get_trade_history(count=100)
        open_trades = client.get_open_trades()
        pending = client.get_orders()
        
        return {
            "open_trades": [
                {
                    "id": t.get("id"),
                    "instrument": t.get("instrument"),
                    "pair": OANDAClient.from_oanda_symbol(t.get("instrument", "")),
                    "units": t.get("currentUnits"),
                    "direction": "SHORT" if int(t.get("currentUnits", 0)) < 0 else "LONG",
                    "price": t.get("price"),
                    "unrealizedPL": t.get("unrealizedPL"),
                    "stopLoss": t.get("stopLossOrder", {}).get("price") if t.get("stopLossOrder") else None,
                    "takeProfit": t.get("takeProfitOrder", {}).get("price") if t.get("takeProfitOrder") else None,
                    "openTime": t.get("openTime"),
                }
                for t in open_trades
            ],
            "pending_orders": [
                {
                    "id": o.get("id"),
                    "instrument": o.get("instrument"),
                    "pair": OANDAClient.from_oanda_symbol(o.get("instrument", "")),
                    "units": o.get("units"),
                    "direction": "SHORT" if int(o.get("units", 0)) < 0 else "LONG",
                    "price": o.get("price"),
                    "state": o.get("state"),
                    "type": o.get("type"),
                    "stopLoss": o.get("stopLossOnFill", {}).get("price") if o.get("stopLossOnFill") else None,
                    "takeProfit": o.get("takeProfitOnFill", {}).get("price") if o.get("takeProfitOnFill") else None,
                    "createTime": o.get("createTime"),
                }
                for o in pending
            ],
            "closed_trades": [
                {
                    "id": t.get("id"),
                    "instrument": t.get("instrument"),
                    "pair": OANDAClient.from_oanda_symbol(t.get("instrument", "")),
                    "units": t.get("initialUnits"),
                    "direction": "SHORT" if int(t.get("initialUnits", 0)) < 0 else "LONG",
                    "price": t.get("price"),
                    "averageClosePrice": t.get("averageClosePrice"),
                    "realizedPL": t.get("realizedPL"),
                    "stopLoss": t.get("stopLossOrder", {}).get("price") if t.get("stopLossOrder") else None,
                    "takeProfit": t.get("takeProfitOrder", {}).get("price") if t.get("takeProfitOrder") else None,
                    "openTime": t.get("openTime"),
                    "closeTime": t.get("closeTime"),
                }
                for t in closed
            ],
        }
    except Exception as e:
        return {"error": str(e)}


@app.get("/oanda-debug")
def oanda_debug():
    try:
        account = client.get_account()
        open_trades = client.get_open_trades()
        pending_orders = client.get_orders()
        
        return {
            "status": "connected",
            "account_id": client.account_id,
            "account": {
                "balance": account.balance,
                "currency": account.currency,
                "unrealized_pl": account.unrealized_pl,
                " NAV": account.equity,
            },
            "open_trades_count": len(open_trades),
            "pending_orders_count": len(pending_orders),
            "open_trades": open_trades,
            "pending_orders": pending_orders,
        }
    except Exception as e:
        return {"status": "error", "error": str(e)}


@app.get("/logs")
def get_logs(level: str | None = None, limit: int = 50):
    from trading_bot.log_config import get_recent_logs
    logs = get_recent_logs(level, limit)
    return {"logs": logs, "count": len(logs)}





@app.get("/live-trades")
def live_trades():
    try:
        open_trades = client.get_open_trades()
        return {
            "trades": [
                {
                    "id": t.get("id"),
                    "oanda_trade_id": t.get("id"),
                    "pair": OANDAClient.from_oanda_symbol(t.get("instrument", "")),
                    "direction": "SHORT" if int(t.get("currentUnits", 0)) < 0 else "LONG",
                    "units": abs(int(t.get("currentUnits", 0))),
                    "price": float(t.get("price", 0)),
                    "current_price": float(t.get("price", 0)),
                    "unrealized_pl": float(t.get("unrealizedPL", 0)),
                    "open_time": t.get("openTime", ""),
                }
                for t in open_trades
            ]
        }
    except Exception as e:
        return {"trades": [], "error": str(e)}


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
