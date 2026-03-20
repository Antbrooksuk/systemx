"""In-memory trade state and REST API models."""
from dataclasses import dataclass, field
from datetime import datetime
from typing import Optional
from enum import Enum
import threading


class OrderStatus(Enum):
    PENDING = "PENDING"
    FILLED = "FILLED"
    CANCELLED = "CANCELLED"
    EXPIRED = "EXPIRED"


@dataclass
class ActiveOrder:
    oanda_order_id: str
    pair: str
    session: str
    direction: str
    entry_price: float
    sl_price: float
    tp_price: float
    placed_at: datetime
    candles_placed: int = 0


@dataclass
class FilledTrade:
    pair: str
    session: str
    direction: str
    entry_time: datetime
    entry_price: float
    sl_price: float
    tp_price: float
    exit_time: Optional[datetime]
    exit_price: Optional[float]
    exit_reason: str
    pips: float
    pnl_pct: float
    oanda_trade_id: str
    completed_at: Optional[datetime] = None


@dataclass
class BotState:
    active_orders: dict[str, ActiveOrder] = field(default_factory=dict)
    filled_trades: list[FilledTrade] = field(default_factory=list)
    started_at: datetime = field(default_factory=datetime.utcnow)
    websocket_connected: bool = False
    last_candle_time: Optional[datetime] = None
    current_signal: Optional[dict] = None
    total_pnl_pct: float = 0.0
    lock: threading.Lock = field(default_factory=threading.Lock)

    def add_order(self, order: ActiveOrder):
        with self.lock:
            self.active_orders[order.oanda_order_id] = order

    def remove_order(self, order_id: str) -> Optional[ActiveOrder]:
        with self.lock:
            return self.active_orders.pop(order_id, None)

    def add_trade(self, trade: FilledTrade):
        with self.lock:
            self.filled_trades.append(trade)
            self.total_pnl_pct += trade.pnl_pct

    def get_trades(self) -> list[dict]:
        with self.lock:
            return [
                {
                    "pair": t.pair,
                    "session": t.session,
                    "direction": t.direction,
                    "entry_time": t.entry_time.isoformat() if t.entry_time else None,
                    "entry": t.entry_price,
                    "sl": t.sl_price,
                    "tp": t.tp_price,
                    "exit_time": t.exit_time.isoformat() if t.exit_time else None,
                    "exit_price": t.exit_price,
                    "exit_reason": t.exit_reason,
                    "pips": t.pips,
                    "pnl_pct": t.pnl_pct,
                    "oanda_trade_id": t.oanda_trade_id,
                }
                for t in self.filled_trades
            ]

    def get_orders(self) -> list[dict]:
        with self.lock:
            return [
                {
                    "oanda_order_id": o.oanda_order_id,
                    "pair": o.pair,
                    "session": o.session,
                    "direction": o.direction,
                    "entry": o.entry_price,
                    "sl": o.sl_price,
                    "tp": o.tp_price,
                    "placed_at": o.placed_at.isoformat(),
                    "candles_placed": o.candles_placed,
                }
                for o in self.active_orders.values()
            ]

    def get_status(self) -> dict:
        with self.lock:
            session = "outside"
            # Simple heuristic — caller should check session.py
            return {
                "active_orders": len(self.active_orders),
                "filled_trades": len(self.filled_trades),
                "total_pnl_pct": round(self.total_pnl_pct, 2),
                "uptime_seconds": int((datetime.utcnow() - self.started_at).total_seconds()),
                "websocket_connected": self.websocket_connected,
                "last_candle_time": self.last_candle_time.isoformat() if self.last_candle_time else None,
            }


state = BotState()
