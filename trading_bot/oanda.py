"""OANDA v20 REST API client."""
import os
from pathlib import Path
from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
import pandas as pd
import httpx
from dotenv import load_dotenv

cwd = Path.cwd()
for env_file in [".env", ".env.local"]:
    env_path = cwd / env_file
    if env_path.exists():
        load_dotenv(dotenv_path=env_path)
        break

OANDA_API_KEY = os.getenv("OANDA_API_KEY", "")
OANDA_ACCOUNT_ID = os.getenv("OANDA_ACCOUNT_ID", "")
OANDA_ENV = os.getenv("OANDA_ENV", "demo")

if not OANDA_API_KEY:
    raise ValueError(f"OANDA_API_KEY not found in environment variables. Checked: {cwd}/.env and {cwd}/.env.local")
if not OANDA_ACCOUNT_ID:
    raise ValueError("OANDA_ACCOUNT_ID not found in environment variables")

BASE_URL = (
    "https://api-fxpractice.oanda.com" if OANDA_ENV == "demo"
    else "https://api-fxtrade.oanda.com"
)

HEADERS = {
    "Authorization": f"Bearer {OANDA_API_KEY}",
    "Content-Type": "application/json",
}


@dataclass
class Candle:
    time: datetime
    open: float
    high: float
    low: float
    close: float
    volume: int


@dataclass
class AccountInfo:
    balance: float
    equity: float
    unrealized_pl: float
    currency: str


class OANDAClient:
    def __init__(self):
        self.base_url = BASE_URL
        self.headers = HEADERS
        self.account_id = OANDA_ACCOUNT_ID

    @staticmethod
    def to_oanda_symbol(pair: str) -> str:
        mapping = {"EURUSD": "EUR_USD", "GBPUSD": "GBP_USD", "USDJPY": "USD_JPY", "EURJPY": "EUR_JPY"}
        return mapping.get(pair, pair.replace("USD", "_USD"))

    @staticmethod
    def from_oanda_symbol(oanda_symbol: str) -> str:
        mapping = {"EUR_USD": "EURUSD", "GBP_USD": "GBPUSD", "USD_JPY": "USDJPY"}
        return mapping.get(oanda_symbol, oanda_symbol.replace("_", ""))

    def _get(self, path: str, params: Optional[dict] = None) -> dict:
        with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30) as client:
            resp = client.get(path, params=params)
            resp.raise_for_status()
            return resp.json()

    def _post(self, path: str, data: Optional[dict] = None) -> dict:
        with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30) as client:
            resp = client.post(path, json=data)
            if resp.status_code >= 400:
                try:
                    error_body = resp.json()
                except:
                    error_body = resp.text
                raise httpx.HTTPStatusError(
                    f"OANDA API error {resp.status_code}: {error_body}",
                    request=resp.request,
                    response=resp,
                )
            return resp.json()

    def _put(self, path: str, data: dict) -> dict:
        with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30) as client:
            resp = client.put(path, json=data)
            resp.raise_for_status()
            return resp.json()

    def _patch(self, path: str, data: dict) -> dict:
        with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30) as client:
            resp = client.patch(path, json=data)
            resp.raise_for_status()
            return resp.json()

    def _delete(self, path: str) -> dict:
        with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30) as client:
            resp = client.delete(path)
            resp.raise_for_status()
            return resp.json()

    def get_candles(self, instrument: str, count: int = 20, granularity: str = "M5") -> list[Candle]:
        oanda_symbol = self.to_oanda_symbol(instrument)
        data = self._get(
            f"/v3/instruments/{oanda_symbol}/candles",
            params={"granularity": granularity, "count": count},
        )
        candles = []
        for c in data.get("candles", []):
            mid = c.get("mid", {})
            candles.append(Candle(
                time=datetime.fromisoformat(c["time"].replace("Z", "+00:00")),
                open=float(mid["o"]),
                high=float(mid["h"]),
                low=float(mid["l"]),
                close=float(mid["c"]),
                volume=int(c.get("volume", 0)),
            ))
        return candles

    def get_candles_df(self, instrument: str, count: int = 20, granularity: str = "M5") -> pd.DataFrame:
        candles = self.get_candles(instrument, count, granularity)
        if not candles:
            return pd.DataFrame()
        df = pd.DataFrame([{
            "Open": c.open,
            "High": c.high,
            "Low": c.low,
            "Close": c.close,
            "Volume": c.volume,
        } for c in candles], index=pd.DatetimeIndex([c.time for c in candles]))
        return df

    def get_account(self) -> AccountInfo:
        data = self._get(f"/v3/accounts/{self.account_id}")
        a = data["account"]
        return AccountInfo(
            balance=float(a["balance"]),
            equity=float(a.get("NAV", a.get("equity", "0"))),
            unrealized_pl=float(a["unrealizedPL"]),
            currency=a["currency"],
        )

    def get_orders(self, state_filter: str = "PENDING") -> list[dict]:
        data = self._get(
            f"/v3/accounts/{self.account_id}/orders",
            params={"state": state_filter},
        )
        return data.get("orders", [])

    def get_all_orders(self) -> list[dict]:
        data = self._get(
            f"/v3/accounts/{self.account_id}/orders",
            params={"count": 100},
        )
        return data.get("orders", [])

    def get_order(self, order_id: str) -> dict | None:
        data = self._get(f"/v3/accounts/{self.account_id}/orders/{order_id}")
        return data.get("order")

    def get_open_trades(self) -> list[dict]:
        data = self._get(f"/v3/accounts/{self.account_id}/openTrades")
        return data.get("trades", [])

    def place_order(
        self,
        instrument: str,
        units: int,
        order_type: str,
        price: Optional[float] = None,
        sl_price: Optional[float] = None,
        tp_price: Optional[float] = None,
        trade_id: Optional[str] = None,
    ) -> dict:
        units_str = str(units) if units > 0 else str(units)
        side = "SELL" if units < 0 else "BUY"

        order: dict = {
            "order": {
                "type": order_type,
                "instrument": self.to_oanda_symbol(instrument),
                "units": units_str,
                "side": side,
                "timeInForce": "GTD",
                "gtdTime": (datetime.utcnow() + timedelta(hours=2)).strftime("%Y-%m-%dT%H:%M:%SZ"),
            }
        }

        if price is not None:
            if order_type == "LIMIT":
                order["order"]["price"] = f"{price:.5f}"
            elif order_type == "STOP":
                order["order"]["price"] = f"{price:.5f}"

        if sl_price is not None:
            order["order"]["stopLossOnFill"] = {
                "price": f"{sl_price:.5f}",
                "timeInForce": "GTC"
            }

        if tp_price is not None:
            order["order"]["takeProfitOnFill"] = {
                "price": f"{tp_price:.5f}",
                "timeInForce": "GTC"
            }

        if trade_id:
            order["order"]["tradeID"] = trade_id
            path = f"/v3/accounts/{self.account_id}/orders"
        else:
            path = f"/v3/accounts/{self.account_id}/orders"

        return self._post(path, order)

    def cancel_order(self, order_id: str) -> dict:
        return self._put(f"/v3/accounts/{self.account_id}/orders/{order_id}/cancel", {})

    def close_trade(self, trade_id: str, units: Optional[int] = None) -> dict:
        data = {}
        if units is not None:
            data["units"] = str(units)
        return self._close_trade(trade_id, data)

    def _close_trade(self, trade_id: str, data: dict) -> dict:
        path = f"/v3/accounts/{self.account_id}/trades/{trade_id}/close"
        with httpx.Client(base_url=self.base_url, headers=self.headers, timeout=30) as client:
            resp = client.put(path, json=data)
            resp.raise_for_status()
            return resp.json()

    def get_trade_history(self, count: int = 100) -> list[dict]:
        data = self._get(
            f"/v3/accounts/{self.account_id}/trades",
            params={"count": count, "state": "CLOSED"},
        )
        return data.get("trades", [])

    def get_recent_trades(self, count: int = 50) -> list[dict]:
        data = self._get(
            f"/v3/accounts/{self.account_id}/trades",
            params={"count": count},
        )
        return data.get("trades", [])

    def get_transaction(self, transaction_id: int) -> dict:
        return self._get(f"/v3/accounts/{self.account_id}/transactions/{transaction_id}")

    def get_transactions_since(self, transaction_id: int) -> list[dict]:
        data = self._get(
            f"/v3/accounts/{self.account_id}/transactions",
            params={"from": transaction_id, "type": "ORDER_CANCEL"},
        )
        return data.get("transactions", [])
