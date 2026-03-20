"""
Download and cache 60 days of M5 forex data.
Run once, or with --refresh to update.
"""
import yfinance as yf
import pandas as pd
import time
from pathlib import Path

PAIRS = ["EURUSD=X", "GBPUSD=X", "USDJPY=X", "EURJPY=X"]
DATA_DIR = Path(__file__).parent / "data"


def fetch_and_save(days=60):
    DATA_DIR.mkdir(exist_ok=True)
    
    for pair in PAIRS:
        print(f"Fetching {pair}...")
        ticker = yf.Ticker(pair)
        df = ticker.history(period=f"{days}d", interval="5m")
        
        if df.empty:
            print(f"  ERROR: No data for {pair}")
            continue
        
        df = df.tz_convert("UTC")
        
        filename = pair.replace("=X", "") + ".parquet"
        df.to_parquet(DATA_DIR / filename)
        print(f"  Saved {filename}: {len(df)} candles")
        
        time.sleep(1)


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--refresh", action="store_true", help="Re-fetch data")
    parser.add_argument("--days", type=int, default=60, help="Number of days")
    args = parser.parse_args()
    
    if args.refresh or not (DATA_DIR / "EURUSD.parquet").exists():
        fetch_and_save(args.days)
    else:
        print("Data already exists. Use --refresh to update.")
