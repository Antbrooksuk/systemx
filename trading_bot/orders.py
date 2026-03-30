"""Order management — places, monitors, and manages limit orders."""
from datetime import datetime, timezone, timedelta
import httpx
from trading_bot.oanda import OANDAClient, OANDAClient as OANDA
from trading_bot.state import state, ActiveOrder, FilledTrade
from trading_bot.log_config import log
from mode_b import PAIR_CONFIG, RISK_PER_TRADE


MAX_CANDLES = 18


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


class OrderManager:
    def __init__(self, client: OANDAClient):
        self.client = client
        self._balance_cache: float = 2000.0
        self._balance_ts: float = 0.0

    def _get_balance(self) -> float:
        now = _utc_now().timestamp()
        if now - self._balance_ts < 30 and self._balance_cache > 0:
            return self._balance_cache
        try:
            acc = self.client.get_account()
            self._balance_cache = acc.balance
            self._balance_ts = now
            return acc.balance
        except Exception as e:
            log.warning(f"Could not fetch balance, using cached £{self._balance_cache:.0f}: {e}")
            return self._balance_cache

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
        balance = self._get_balance()
        risk_amount = balance * RISK_PER_TRADE
        gbp_per_pip_per_unit = PAIR_CONFIG[pair]["gbp_per_pip"] / 1000.0
        units = int(risk_amount / (sl_distance_pips * gbp_per_pip_per_unit))

        if units == 0:
            log.warning(f"Balance too small for 1% risk on {pair}: £{balance}, SL distance {sl_distance_pips:.1f} pips")
            return None

        # Proactive margin cap — check available margin before sending to OANDA
        try:
            acc = self.client.get_account()
            margin_available = acc.margin_available
            MARGIN_RATE = 0.033
            notional_per_unit = entry_price * pip_value
            if notional_per_unit > 0:
                max_units_by_margin = int(margin_available * MARGIN_RATE / notional_per_unit)
                if max_units_by_margin < units:
                    log.warning(f"Margin cap: risk wants {units} units, margin allows {max_units_by_margin}")
                    units = max_units_by_margin
        except Exception as e:
            log.warning(f"Could not check margin for proactive cap: {e}")

        if units == 0:
            log.error(f"Units reduced to 0 by margin cap on {pair}")
            return None

        if direction == "SHORT":
            units = -units

        spread_value = PAIR_CONFIG[pair]["spread_pips"] * pip_value
        sl_slippage_value = 0.3 * pip_value

        if direction == "LONG":
            order_sl = sl_price - spread_value - sl_slippage_value
            order_tp = tp_price + spread_value
        else:
            order_sl = sl_price + spread_value + sl_slippage_value
            order_tp = tp_price - spread_value

        log.info(
            f"PLACING LIMIT {direction} {pair}: "
            f"entry={pip_str % entry_price} sl={pip_str % order_sl} tp={pip_str % order_tp} units={abs(units)}"
        )

        max_attempts = 5
        for attempt in range(max_attempts):
            try:
                result = self.client.place_order(
                    instrument=pair,
                    units=units,
                    order_type="LIMIT",
                    price=entry_price,
                    sl_price=order_sl,
                    tp_price=order_tp,
                )

                order = result.get("orderCreateTransaction", {})
                cancel = result.get("orderCancelTransaction", {})
                order_id = str(order.get("id", ""))

                if cancel.get("id") and order_id:
                    cancel_reason = cancel.get("reason", "")
                    log.warning(f"Order {order_id} cancelled by OANDA: {cancel_reason}")
                    if "MARGIN" in cancel_reason.upper() or "INSUFFICIENT" in cancel_reason.upper():
                        units = int(units / 2)
                        if abs(units) < 1000:
                            log.error(f"Failed to place {pair} order: margin insufficient even at {abs(units)} units")
                            return None
                        log.warning(f"Margin rejected, retrying {pair} with {abs(units)} units (attempt {attempt + 2})")
                        continue
                    return None

                if order_id:
                    order_status = order.get("status", "UNKNOWN")

                    if order_status == "FILLED":
                        units_val = int(order.get("units", 0))
                        filled_trade = FilledTrade(
                            pair=pair,
                            session=session,
                            direction=direction,
                            units=abs(units_val),
                            entry_time=_utc_now(),
                            entry_price=float(order.get("price", entry_price)),
                            sl_price=order_sl,
                            tp_price=order_tp,
                            exit_time=None,
                            exit_price=None,
                            exit_reason="OPEN",
                            pips=0,
                            pnl_pct=0,
                            oanda_trade_id=order_id,
                        )
                        state.add_trade(filled_trade)
                        state.mark_pair_traded(session, pair)
                        log.info(f"Order FILLED immediately: {order_id} {pair} {direction}")
                        return order_id

                    active = ActiveOrder(
                        oanda_order_id=order_id,
                        pair=pair,
                        session=session,
                        direction=direction,
                        entry_price=entry_price,
                        sl_price=order_sl,
                        tp_price=order_tp,
                        placed_at=_utc_now(),
                    )
                    state.add_order(active)
                    if attempt > 0:
                        actual_risk_pct = (abs(units) * sl_distance_pips * gbp_per_pip_per_unit) / balance * 100
                        log.warning(f"Order placed after {attempt + 1} attempts with reduced size: {abs(units)} units ({actual_risk_pct:.2f}% risk)")
                    else:
                        log.info(f"Limit order placed: {order_id} {pair} {direction}")
                    return order_id
                else:
                    log.warning(f"No order ID in response: {result}")
                    return None

            except httpx.HTTPStatusError as e:
                error_str = str(e)
                if "insufficient" in error_str.lower() or "margin" in error_str.lower():
                    units = int(units / 2)
                    if abs(units) < 1000:
                        log.error(f"Failed to place {pair} order: margin insufficient even at {abs(units)} units")
                        return None
                    log.warning(f"Margin rejected, retrying {pair} with {abs(units)} units (attempt {attempt + 2})")
                    continue
                else:
                    log.error(f"Failed to place order: {e}")
                    return None
            except Exception as e:
                log.error(f"Failed to place order: {e}")
                return None

        return None

    def check_and_manage_orders(self, session: str = "live") -> list[FilledTrade]:
        completed = []
        try:
            open_trades = self.client.get_open_trades()
            pending_orders = self.client.get_orders()

            open_trade_ids = {str(t.get("id")) for t in open_trades}
            pending_order_ids = {str(o.get("id")) for o in pending_orders}

            log.info(f"=== ORDER CHECK: {len(pending_order_ids)} pending, {len(open_trade_ids)} open, {len(state.active_orders)} tracked ===")

            now = _utc_now()

            for order_id, active_order in list(state.active_orders.items()):
                candles_elapsed = (now - active_order.placed_at).total_seconds() / 300

                order_in_pending = order_id in pending_order_ids
                order_in_trades = order_id in open_trade_ids

                # Order filled — it transitioned from pending to open trade
                if order_in_trades and not order_in_pending:
                    trade = next((t for t in open_trades if str(t.get("id")) == order_id), None)
                    if trade:
                        units = int(trade.get("currentUnits", 0))
                        direction = "SHORT" if units < 0 else "LONG"
                        entry_price = float(trade.get("price", 0))
                        open_time_str = trade.get("openTime", "")
                        open_time_dt = datetime.fromisoformat(open_time_str.replace("Z", "+00:00")) if open_time_str else _utc_now()

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
                            state.mark_pair_traded(active_order.session, active_order.pair)
                            log.info(f"Order FILLED: {order_id} {active_order.pair} {direction} @ {entry_price}")

                    state.remove_order(order_id)
                    continue

                # Order still pending — check expiry
                if order_in_pending:
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
                    continue

                # Order not in pending and not in open trades
                if not order_in_pending and not order_in_trades:
                    if (now - active_order.placed_at).total_seconds() < 60:
                        log.info(f"Order {order_id} ({active_order.pair}) still propagating ({(now - active_order.placed_at).total_seconds():.0f}s)")
                        continue

                    log.warning(f"Order {order_id} ({active_order.pair}) disappeared — checking OANDA state")
                    try:
                        all_orders = self.client.get_all_orders()
                        oanda_order = next((o for o in all_orders if str(o.get("id")) == order_id), None)
                        if oanda_order:
                            order_state = oanda_order.get("state", "unknown")
                            log.warning(f"Order {order_id} state={order_state}")
                        else:
                            log.warning(f"Order {order_id} not found in OANDA at all")
                    except Exception as e:
                        log.error(f"Could not check order status: {e}")

                    # Don't mark pair as traded — allow retry
                    state.remove_order(order_id)
                    log.warning(f"Order {order_id} ({active_order.pair}) removed from tracking (not marked as traded)")
                    continue

            # Time-stop open trades
            for trade in open_trades:
                trade_id = str(trade.get("id"))
                oanda_pair = trade.get("instrument")
                pair = OANDA.from_oanda_symbol(oanda_pair)
                units = int(trade.get("currentUnits", 0))

                open_time_str = trade.get("openTime", "")
                if open_time_str:
                    open_time_dt = datetime.fromisoformat(open_time_str.replace("Z", "+00:00"))
                    candles_open = (now - open_time_dt).total_seconds() / 300
                else:
                    candles_open = 0

                if candles_open < MAX_CANDLES:
                    continue

                pip_value = PAIR_CONFIG[pair]["pip_value"]
                direction = "SHORT" if units < 0 else "LONG"
                entry_price = float(trade.get("price", 0))
                sl_price = float(trade.get("stopLossOrder", {}).get("price", 0))
                tp_price = float(trade.get("takeProfitOrder", {}).get("price", 0))
                unrealized_pl = float(trade.get("unrealizedPL", 0))

                try:
                    self.client.close_trade(trade_id)
                    current_price = float(trade.get("price", 0))
                    pnl_at_close = unrealized_pl
                    balance = self._get_balance()
                    pnl_pct_closed = round(pnl_at_close / balance * 100, 4) if balance > 0 else 0
                    pips_closed = round(pnl_at_close / (abs(units) * pip_value), 1) if abs(units) * pip_value > 0 else 0

                    filled_ts = FilledTrade(
                        pair=pair,
                        session=session,
                        direction=direction,
                        units=abs(units),
                        entry_time=open_time_dt,
                        entry_price=entry_price,
                        sl_price=sl_price,
                        tp_price=tp_price,
                        exit_time=_utc_now(),
                        exit_price=current_price,
                        exit_reason="TIME_STOP",
                        pips=pips_closed,
                        pnl_pct=pnl_pct_closed,
                        oanda_trade_id=trade_id,
                        completed_at=_utc_now(),
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
                except Exception as e:
                    log.error(f"Failed to time stop trade {trade_id}: {e}")

        except Exception as e:
            log.error(f"Error checking orders: {e}")

        return completed

    def check_closed_trades(self, session: str = "live") -> list[FilledTrade]:
        recent_closed: list[FilledTrade] = []
        try:
            history = self.client.get_trade_history(count=50)
            balance = self._get_balance()

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

                pip_value = PAIR_CONFIG[pair]["pip_value"]
                if direction == "SHORT":
                    pips = round((entry_price - exit_price) / pip_value, 1) if entry_price and exit_price else 0
                else:
                    pips = round((exit_price - entry_price) / pip_value, 1) if entry_price and exit_price else 0

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
                        entry_time=datetime.fromisoformat(open_time.replace("Z", "+00:00")) if open_time else _utc_now(),
                        entry_price=entry_price,
                        sl_price=sl_price,
                        tp_price=tp_price,
                        exit_time=datetime.fromisoformat(close_time.replace("Z", "+00:00")) if close_time else None,
                        exit_price=exit_price,
                        exit_reason=exit_reason,
                        pips=round(pips, 1),
                        pnl_pct=round(pnl_pct, 4),
                        oanda_trade_id=trade_id,
                        completed_at=_utc_now(),
                    )
                    state.add_trade(filled)
                    recent_closed.append(filled)

        except Exception as e:
            log.error(f"Error checking closed trades: {e}")

        return recent_closed
