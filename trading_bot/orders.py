"""Order management — places, monitors, and manages limit orders."""
from datetime import datetime
from trading_bot.oanda import OANDAClient, OANDAClient as OANDA
from trading_bot.state import state, ActiveOrder, FilledTrade
from trading_bot.log_config import log
from mode_b import PAIR_CONFIG, RISK_PER_TRADE


MAX_CANDLES = 18  # 90 min ÷ 5 min


class OrderManager:
    def __init__(self, client: OANDAClient):
        self.client = client

    def place_entry(
        self,
        pair: str,
        direction: str,
        entry_price: float,
        sl_price: float,
        tp_price: float,
        session: str,
    ) -> str | None:
        pip_value = PAIR_CONFIG[pair]["pip_value"]
        pip_str = "%.5f" if pip_value < 0.001 else "%.3f"

        sl_distance_pips = abs(entry_price - sl_price) / pip_value
        try:
            acc = self.client.get_account()
            balance = acc.balance
        except Exception:
            balance = 2000.0
        risk_amount = balance * RISK_PER_TRADE
        units = int(risk_amount / (sl_distance_pips * pip_value))
        if direction == "SHORT":
            units = -units

        MARGIN_RATE = 0.025
        notional_per_unit = entry_price * pip_value
        max_units_by_margin = int(balance * MARGIN_RATE / notional_per_unit) if notional_per_unit > 0 else 0
        units = min(units, max_units_by_margin)

        if units == 0:
            log.warning(f"Balance too small for 1% risk on {pair}: £{balance}, SL distance {sl_distance_pips:.1f} pips")
            return None

        log.info(
            f"PLACING LIMIT {direction} {pair}: "
            f"entry={pip_str % entry_price} sl={pip_str % sl_price} tp={pip_str % tp_price} units={units}"
        )

        try:
            result = self.client.place_order(
                instrument=pair,
                units=units,
                order_type="LIMIT",
                price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
            )

            order = result.get("orderCreateTransaction", {})
            order_id = str(order.get("id", ""))

            if order_id:
                active = ActiveOrder(
                    oanda_order_id=order_id,
                    pair=pair,
                    session=session,
                    direction=direction,
                    entry_price=entry_price,
                    sl_price=sl_price,
                    tp_price=tp_price,
                    placed_at=datetime.utcnow(),
                )
                state.add_order(active)
                log.info(f"Limit order placed: {order_id} {pair} {direction}")
                return order_id
            else:
                log.warning(f"No order ID in response: {result}")
                return None

        except Exception as e:
            log.error(f"Failed to place order: {e}")
            return None

    def check_and_manage_orders(self, session: str = "live") -> list[FilledTrade]:
        completed = []
        try:
            open_trades = self.client.get_open_trades()
            pending_orders = self.client.get_orders()

            now = datetime.utcnow()

            for order_id, active_order in list(state.active_orders.items()):
                candles_elapsed = (now - active_order.placed_at).total_seconds() / 300

                order_in_oanda = any(
                    str(o.get("id")) == order_id for o in pending_orders
                )

                if not order_in_oanda:
                    state.remove_order(order_id)
                    log.info(f"Order {order_id} no longer pending — may have filled")
                    continue

                if candles_elapsed >= MAX_CANDLES:
                    try:
                        self.client.cancel_order(order_id)
                        state.remove_order(order_id)
                        log.info(
                            f"ORDER EXPIRED: {order_id} {active_order.pair} "
                            f"({candles_elapsed:.1f} candles elapsed)"
                        )
                    except Exception as e:
                        log.error(f"Failed to cancel order {order_id}: {e}")

            for trade in open_trades:
                trade_id = str(trade.get("id"))
                oanda_pair = trade.get("instrument")
                pair = OANDA.from_oanda_symbol(oanda_pair)
                units = int(trade.get("currentUnits", 0))
                open_time_str = trade.get("openTime", "")
                open_time_dt = datetime.fromisoformat(open_time_str.replace("Z", "+00:00")) if open_time_str else datetime.utcnow()
                candles_open = (datetime.utcnow() - open_time_dt).total_seconds() / 300

                pip_value = PAIR_CONFIG[pair]["pip_value"]
                direction = "SHORT" if units < 0 else "LONG"
                entry_price = float(trade.get("price", 0))
                sl_price = float(trade.get("stopLossOrder", {}).get("price", 0))
                tp_price = float(trade.get("takeProfitOrder", {}).get("price", 0))
                unrealized_pl = float(trade.get("unrealizedPL", 0))

                if candles_open >= MAX_CANDLES:
                    try:
                        self.client.close_trade(trade_id)
                        current_price = float(trade.get("price", 0))
                        sl_dist_pips = abs(entry_price - sl_price) / pip_value
                        pnl_at_close = unrealized_pl
                        pips_closed = round(sl_dist_pips, 1) * (-1 if direction == "SHORT" else 1)
                        try:
                            acc2 = self.client.get_account()
                            balance2 = acc2.balance
                        except Exception:
                            balance2 = 100000.0
                        pnl_pct_closed = round(pnl_at_close / balance2 * 100, 4)
                        filled_ts = FilledTrade(
                            pair=pair,
                            session=session,
                            direction=direction,
                            units=abs(units),
                            entry_time=open_time_dt,
                            entry_price=entry_price,
                            sl_price=sl_price,
                            tp_price=tp_price,
                            exit_time=datetime.utcnow(),
                            exit_price=current_price,
                            exit_reason="TIME_STOP",
                            pips=pips_closed,
                            pnl_pct=pnl_pct_closed,
                            oanda_trade_id=trade_id,
                            completed_at=datetime.utcnow(),
                        )
                        existing = next(
                            (t for t in state.filled_trades if t.oanda_trade_id == trade_id),
                            None,
                        )
                        if not existing:
                            state.add_trade(filled_ts)
                            log.info(
                                f"TIME STOP: closed trade {trade_id} {pair} "
                                f"pl={pnl_at_close:.2f} pips={pips_closed:.1f}"
                            )
                        continue
                    except Exception as e:
                        log.error(f"Failed to time stop trade {trade_id}: {e}")
                try:
                    acc = self.client.get_account()
                    balance = acc.balance
                except Exception:
                    balance = 100000.0
                pnl_pct = unrealized_pl / balance * 100 if balance > 0 else 0

                filled = FilledTrade(
                    pair=pair,
                    session=session,
                    direction=direction,
                    units=abs(units),
                    entry_time=open_time_dt,
                    entry_price=entry_price,
                    sl_price=sl_price,
                    tp_price=tp_price,
                    exit_time=None,
                    exit_price=None,
                    exit_reason="OPEN",
                    pips=round(abs(unrealized_pl) / (abs(units) * pip_value), 1),
                    pnl_pct=round(pnl_pct, 4),
                    oanda_trade_id=trade_id,
                )

                existing = next(
                    (t for t in state.filled_trades if t.oanda_trade_id == trade_id),
                    None,
                )
                if not existing:
                    state.add_trade(filled)
                    log.info(
                        f"TRADE OPENED: {trade_id} {pair} {direction} "
                        f"entry={entry_price:.5f} unrealized={unrealized_pl:.2f}"
                    )

                completed.append(filled)

        except Exception as e:
            log.error(f"Error checking orders: {e}")

        return completed

    def check_closed_trades(self, session: str = "live") -> list[FilledTrade]:
        recent_closed: list[FilledTrade] = []
        try:
            history = self.client.get_trade_history(count=50)

            for trade in history:
                trade_id = str(trade.get("id"))
                oanda_pair = trade.get("instrument", "")
                pair = OANDA.from_oanda_symbol(oanda_pair)
                pl = float(trade.get("realizedPL", 0))
                units = int(trade.get("initialUnits", 0))
                direction = "SHORT" if units < 0 else "LONG"
                entry_price = float(trade.get("price", 0))
                exit_price = float(trade.get("averageClosePrice", 0))
                sl_price = float(trade.get("stopLossOrder", {}).get("price", 0))
                tp_price = float(trade.get("takeProfitOrder", {}).get("price", 0))
                close_time = trade.get("closeTime", "")
                open_time = trade.get("openTime", "")

                pip_value = PAIR_CONFIG[OANDA.from_oanda_symbol(pair)]["pip_value"]
                pips = round(abs(entry_price - exit_price) / pip_value, 1) if entry_price and exit_price else 0

                try:
                    acc = self.client.get_account()
                    balance = acc.balance
                except Exception:
                    balance = 100000.0
                pnl_pct = pl / balance * 100 if balance > 0 else 0

                existing = next(
                    (t for t in state.filled_trades if t.oanda_trade_id == trade_id),
                    None,
                )
                if existing:
                    if close_time:
                        existing.exit_time = datetime.fromisoformat(close_time.replace("Z", "+00:00")) if close_time else None
                        existing.exit_price = exit_price
                        existing.exit_reason = "TP" if pl > 0 else ("SL" if pl < 0 else "CLOSED")
                        existing.pips = round(pips, 1)
                        existing.pnl_pct = round(pnl_pct, 4)
                    continue

                if close_time:
                    exit_reason = "TP" if pl > 0 else ("SL" if pl < 0 else "CLOSED")

                    pip_str = "%.5f" if pip_value < 0.001 else "%.3f"
                    log.info(
                        f"TRADE CLOSED: {trade_id} {pair} {direction} "
                        f"exit={pip_str % exit_price} pl={pl:.2f} reason={exit_reason}"
                    )

                    filled = FilledTrade(
                        pair=pair,
                        session=session,
                        direction=direction,
                        units=abs(units),
                        entry_time=datetime.fromisoformat(open_time.replace("Z", "+00:00")) if open_time else datetime.utcnow(),
                        entry_price=entry_price,
                        sl_price=sl_price,
                        tp_price=tp_price,
                        exit_time=datetime.fromisoformat(close_time.replace("Z", "+00:00")) if close_time else None,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        pips=round(pips, 1),
                        pnl_pct=round(pnl_pct, 4),
                        oanda_trade_id=trade_id,
                        completed_at=datetime.utcnow(),
                    )
                    state.add_trade(filled)
                    recent_closed.append(filled)

        except Exception as e:
            log.error(f"Error checking closed trades: {e}")

        return recent_closed
