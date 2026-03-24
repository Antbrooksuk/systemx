"""Order management — places, monitors, and manages limit orders."""
from datetime import datetime
from trading_bot.oanda import OANDAClient, OANDAClient as OANDA
from trading_bot.state import state, ActiveOrder, FilledTrade
from trading_bot.log_config import log
from mode_b import PAIR_CONFIG, RISK_PER_TRADE


MAX_CANDLES = 18  # 90 minutes = 18 x 5-min candles


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
            log.info(f"Account balance: £{balance}")
        except Exception as e:
            log.warning(f"Could not fetch account balance: {e}, using default £2000")
            balance = 2000.0
        risk_amount = balance * RISK_PER_TRADE
        units = int(risk_amount / (sl_distance_pips * pip_value))

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
            log.info(f"Sending order to OANDA: {pair} {direction} {units} units at {entry_price}")
            result = self.client.place_order(
                instrument=pair,
                units=units,
                order_type="LIMIT",
                price=entry_price,
                sl_price=sl_price,
                tp_price=tp_price,
            )

            log.info(f"Full OANDA response: {result}")
            
            order = result.get("orderCreateTransaction", {})
            order_id = str(order.get("id", ""))
            order_status = order.get("status", "UNKNOWN")
            
            if "orderRejectTransaction" in result:
                reject = result.get("orderRejectTransaction", {})
                reject_reason = reject.get("rejectReason", "UNKNOWN")
                log.error(f"Order REJECTED: {reject_reason}, details={reject}")
                return None
            
            log.info(f"Order response: id={order_id}, status={order_status}, full={result}")
            
            # Only add to active orders if PENDING or FILLED
            if order_status in ("PENDING", "FILLED"):
                try:
                    verified_order = self.client.get_order(order_id)
                    if verified_order:
                            log.info(f"Verified order {order_id} exists in OANDA: {verified_order.get('state')}, price={verified_order.get('price')}")
                        else:
                            log.warning(f"Order {order_id} not found in OANDA after placement!")
                    except Exception as e:
                        log.warning(f"Could not verify order {order_id}: {e}")
                    
                # Add to active orders if PENDING or FILLED
                if order_status in ("PENDING", "FILLED") and order_id:
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
                    log.info(f"Limit order tracked: {order_id} {pair} {direction}")
                    return order_id
                
                # Handle UNKNOWN status - log and wait for next cycle
                if order_status == "UNKNOWN":
                    log.warning(f"Order {order_id} status UNKNOWN - will check again next cycle")
                    return None

        except Exception as e:
            log.error(f"Failed to place order: {e}")
            return None

    def check_and_manage_orders(self, session: str = "live") -> list[FilledTrade]:
        completed = []
        try:
            open_trades = self.client.get_open_trades()
            pending_orders = self.client.get_orders()
            
            open_trade_ids = {str(t.get("id")) for t in open_trades}
            pending_order_ids = {str(o.get("id")) for o in pending_orders}
            
            log.info(f"check_and_manage_orders: {len(pending_order_ids)} pending orders, {len(open_trade_ids)} open trades, {len(state.active_orders)} tracked orders")

            now = datetime.utcnow()

            for order_id, active_order in list(state.active_orders.items()):
                candles_elapsed = (now - active_order.placed_at).total_seconds() / 300

                order_in_pending = order_id in pending_order_ids
                order_in_trades = order_id in open_trade_ids
                
                log.debug(f"Order {order_id} ({active_order.pair}): pending={order_in_pending}, open={order_in_trades}")

                if order_in_trades:
                    log.info(f"Order {order_id} is now an OPEN TRADE - creating FilledTrade record")
                    trade = next((t for t in open_trades if str(t.get("id")) == order_id), None)
                    if trade:
                        units = int(trade.get("currentUnits", 0))
                        direction = "SHORT" if units < 0 else "LONG"
                        entry_price = float(trade.get("price", 0))
                        open_time_str = trade.get("openTime", "")
                        open_time_dt = datetime.fromisoformat(open_time_str.replace("Z", "+00:00")) if open_time_str else datetime.utcnow()
                        
                        filled = FilledTrade(
                            pair=active_order.pair,
                            session=active_order.session,
                            direction=direction,
                            units=abs(units),
                            entry_time=open_time_dt,
                            entry_price=entry_price,
                            sl_price=active_order.sl_price,
                            tp_price=active_order.tp_price,
                            exit_time=None,
                            exit_price=None,
                            exit_reason="OPEN",
                            pips=0,
                            pnl_pct=0,
                            oanda_trade_id=order_id,
                        )
                        existing = next(
                            (t for t in state.filled_trades if t.oanda_trade_id == order_id),
                            None,
                        )
                        if not existing:
                            state.add_trade(filled)
                            log.info(f"Created FilledTrade for filled order {order_id} {active_order.pair} {direction}")
                    
                    state.remove_order(order_id)
                    continue

                if not order_in_pending:
                    log.warning(f"Order {order_id} disappeared from pending - checking if cancelled by OANDA")
                    try:
                        all_orders = self.client.get_all_orders()
                        cancelled = [o for o in all_orders if str(o.get("id")) == order_id]
                        if cancelled:
                            order_state = cancelled[0].get("state", "unknown")
                            cancel_time = cancelled[0].get("cancelledTime", "N/A")
                            log.error(f"Order {order_id} state={order_state}, cancelled at={cancel_time}")
                        else:
                            log.warning(f"Order {order_id} not found in OANDA at all - may have expired or been filled then closed")
                    except Exception as e:
                        log.error(f"Could not check order status: {e}")
                    state.remove_order(order_id)
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
            history = self.client.get_trade_history(count=100)
            log.info(f"check_closed_trades: fetched {len(history)} trades from OANDA")
            
            if not history:
                log.info("No closed trades in OANDA history")
                return []

            for trade in history:
                trade_id = str(trade.get("id"))
                oanda_pair = trade.get("instrument", "")
                pair = OANDA.from_oanda_symbol(oanda_pair)
                pl = float(trade.get("realizedPL", 0))
                units = int(trade.get("initialUnits", 0))
                direction = "SHORT" if units < 0 else "LONG"
                entry_price = float(trade.get("price", 0))
                exit_price = float(trade.get("averageClosePrice", 0))
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
