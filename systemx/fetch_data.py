"""
Download historical M5 forex data from OANDA.
Run with --years N to fetch N years of data (default: 3).
Ex: python fetch_data.py --years 3 --pairs EURUSD GBPUSD GBPUSD USDJPY EURJPY
"""
import os
import sys
import time
from datetime import datetime, timedelta
from pathlib import Path
from dotenv import load_dotenv

load_dotenv(Path(__file__).parent / ".env.local")
load_dotenv(Path(__file__).parent.parent / ".env")
sys.path.insert(0, str(Path(__file__).parent.parent))
from trading_bot.oanda import OANDAClient

DATA_DIR = Path(__file__).parent / "data"
DEFAULT_YEARS = 3
CANDLES_PER_REQUEST = 5000


def fetch_oanda_candles(client: OANDAClient, instrument: str, from_dt: datetime, to_dt: datetime) -> list[dict]:
    candles = []

    while True:
        params = {
            "granularity": "M5",
            "count": CANDLES_PER_REQUEST,
            "to": to_dt.strftime("%Y-%m-%dT%H:%M:%SZ"),
        }

        price = client._get(f"/v3/instruments/{instrument}/candles", params=params)

        batch = price.get("candles", [])
        if not batch:
            break

        oldest = datetime.fromisoformat(batch[0]["time"].replace("Z", ""))
        if oldest <= from_dt:
            batch = [c for c in batch if datetime.fromisoformat(c["time"].replace("Z", "")) >= from_dt]
            candles.extend(batch)
            break

        candles.extend(batch)

        if price.get("complete", False) or len(batch) < CANDLES_PER_REQUEST:
            break

        oldest = datetime.fromisoformat(batch[0]["time"].replace("Z", ""))
        to_dt = oldest - timedelta(minutes=5)

        time.sleep(0.25)

    return candles


def save_parquet(candles: list[dict], output_path: Path):
    import pandas as pd

    rows = []
    for c in candles:
        mid = c.get("mid", {})
        rows.append({
            "Open": float(mid["o"]),
            "High": float(mid["h"]),
            "Low": float(mid["l"]),
            "Close": float(mid["c"]),
            "Volume": int(c.get("volume", 0)),
        })

    df = pd.DataFrame(rows, index=pd.to_datetime([c["time"] for c in candles], utc=True))
    df = df.sort_index()
    df = df[~df.index.duplicated(keep='first')]
    df.to_parquet(output_path)
    if len(df) > 0:
        print(f"  Saved {output_path.name}: {len(df)} candles, {df.index[0].date()} to {df.index[-1].date()}")
    else:
        print(f"  Saved {output_path.name}: 0 candles — no data in range")


def main():
    import argparse

    parser = argparse.ArgumentParser(description="Download OANDA M5 historical data")
    parser.add_argument("--years", type=int, default=DEFAULT_YEARS, help=f"Years of data to fetch (default: {DEFAULT_YEARS})")
    parser.add_argument("--pairs", nargs="+", default=["EURUSD", "GBPUSD", "USDJPY", "EURJPY"], help="Pairs to fetch")
    parser.add_argument("--dry-run", action="store_true", help="Show what would be fetched without fetching")
    parser.add_argument("--refresh", action="store_true", help="Delete existing files before fetching")
    args = parser.parse_args()

    DATA_DIR.mkdir(exist_ok=True)

    client = OANDAClient()
    to_dt = datetime.utcnow()
    from_dt = to_dt - timedelta(days=args.years * 365 + 30)
    from_dt = from_dt.replace(tzinfo=None)
    to_dt = to_dt.replace(tzinfo=None)

    print(f"Fetching {args.years} years of M5 data from {from_dt.date()} to {to_dt.date()}")
    print(f"Pairs: {', '.join(args.pairs)}")
    print()

    for pair in args.pairs:
        oanda_symbol = OANDAClient.to_oanda_symbol(pair)
        output_path = DATA_DIR / f"{pair}_oanda.parquet"

        existing = 0
        if output_path.exists():
            if not args.refresh:
                import pandas as pd
                df = pd.read_parquet(output_path)
                existing = len(df)
                print(f"  {pair}: {existing} candles already cached ({df.index[0].date()} to {df.index[-1].date()}) — skipped (use --refresh to re-fetch)")
                continue
            else:
                output_path.unlink()
                print(f"  {pair}: deleted existing file, re-fetching...")

        if args.dry_run:
            print(f"  Would fetch: {from_dt.date()} → {to_dt.date()} (~{(args.years * 365 * 288) // 1000}K candles)")
            continue

        print(f"Fetching {pair} ({oanda_symbol})...")
        try:
            candles = fetch_oanda_candles(client, oanda_symbol, from_dt, to_dt)
        except Exception as e:
            print(f"  FAILED: {e}")
            time.sleep(1)
            continue

        if candles:
            save_parquet(candles, output_path)
        else:
            print(f"  No candles returned for {pair}")

        time.sleep(1)


if __name__ == "__main__":
    main()
