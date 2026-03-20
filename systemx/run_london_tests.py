"""
Batch backtest runner for London performance analysis
Tests SL_OFFSET_PIPS = 40 vs 3 across years 2023-2026
"""
import json
from pathlib import Path
from backtest import run_backtest

YEARS = [2023, 2024, 2025, 2026]
SL_VALUES = [40, 3]
RESULTS_DIR = Path(__file__).parent / "results" / "london_analysis"

def main():
    RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    print("=" * 60)
    print("LONDON PERFORMANCE ANALYSIS - BATCH BACKTEST RUNNER")
    print("=" * 60)
    print(f"Years: {YEARS}")
    print(f"SL values: {SL_VALUES}")
    print(f"Results directory: {RESULTS_DIR}")
    print()
    
    total_tests = len(YEARS) * len(SL_VALUES)
    test_num = 0
    
    for year in YEARS:
        for sl_value in SL_VALUES:
            test_num += 1
            filename = f"bt_{year}_sl{sl_value}.json"
            filepath = RESULTS_DIR / filename
            
            print(f"[{test_num}/{total_tests}] Testing year {year}, SL={sl_value} pips")
            print(f"  Result file: {filename}")
            
            # Run backtest with SL override
            print(f"  Running backtest with sl_override={sl_value}...")
            result = run_backtest(year=year, strategy="base", starting_capital=2000.0, risk_pct=0.01, sl_override=sl_value)
            
            # Add metadata about SL override
            result["sl_override_pips"] = sl_value
            
            # Save results
            with open(filepath, 'w') as f:
                json.dump(result, f, indent=2, default=str)
            
            # Print summary
            trades = result["trades_taken"]
            wins = result["wins"]
            losses = result["losses"]
            win_rate = result["win_rate"]
            roi = result["roi"]
            max_dd = result["max_drawdown"]
            
            print(f"  Results: {trades} trades, {wins}W/{losses}L, {win_rate}% WR")
            print(f"  ROI: {roi}%, Max DD: {max_dd}%")
            print(f"  Saved to: {filepath}")
            print()
    
    print("=" * 60)
    print("BATCH BACKTEST COMPLETE")
    print(f"Total tests run: {test_num}")
    print(f"Results saved to: {RESULTS_DIR}")
    print("=" * 60)

if __name__ == "__main__":
    main()
