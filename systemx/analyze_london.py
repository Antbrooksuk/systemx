"""
London performance analysis script
Extracts London-specific metrics from backtest results
"""
import json
from pathlib import Path
from typing import Dict, List
import statistics

RESULTS_DIR = Path(__file__).parent / "results" / "london_analysis"

def load_results() -> Dict:
    """Load all backtest results."""
    results = {}
    for f in RESULTS_DIR.glob("bt_*.json"):
        # Extract year and SL value from filename
        parts = f.stem.split('_')
        year = int(parts[1])
        sl_value = int(parts[2].replace('sl', ''))
        
        with open(f, 'r') as file:
            data = json.load(file)
            key = (year, sl_value)
            results[key] = data
    
    return results

def analyze_london(trades: List[Dict]) -> Dict:
    """Analyze London-specific metrics from trades."""
    london_trades = [t for t in trades if t['session'] == 'london' and t['signal'] != 'SKIP']
    
    if not london_trades:
        return None
    
    wins = [t for t in london_trades if t.get('pnl_pct', 0) > 0]
    losses = [t for t in london_trades if t.get('pnl_pct', 0) < 0]
    
    # By pair
    eurusd = [t for t in london_trades if t['pair'] == 'EURUSD']
    gbpusd = [t for t in london_trades if t['pair'] == 'GBPUSD']
    
    eurusd_wins = sum(1 for t in eurusd if t.get('pnl_pct', 0) > 0)
    gbpusd_wins = sum(1 for t in gbpusd if t.get('pnl_pct', 0) > 0)
    
    # Exit reasons
    exit_reasons = {}
    for t in london_trades:
        reason = t.get('exit_reason', 'UNKNOWN')
        exit_reasons[reason] = exit_reasons.get(reason, 0) + 1
    
    # Calculate metrics
    total_trades = len(london_trades)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    avg_win_pips = statistics.mean([t.get('pips', 0) for t in wins]) if wins else 0
    avg_loss_pips = statistics.mean([abs(t.get('pips', 0)) for t in losses]) if losses else 0
    
    # Expectancy calculation
    if wins and losses:
        avg_win_pct = statistics.mean([t.get('pnl_pct', 0) for t in wins])
        avg_loss_pct = statistics.mean([abs(t.get('pnl_pct', 0)) for t in losses])
        wr = len(wins) / total_trades
        expectancy_pct = (wr * avg_win_pct) - ((1 - wr) * avg_loss_pct)
        rr_ratio = avg_win_pips / avg_loss_pips
    else:
        avg_win_pct = 0
        avg_loss_pct = 0
        expectancy_pct = 0
        rr_ratio = 0
    
    # Breakdown by pair
    eurusd_wr = (eurusd_wins / len(eurusd) * 100) if eurusd else 0
    gbpusd_wr = (gbpusd_wins / len(gbpusd) * 100) if gbpusd else 0
    
    return {
        'total_trades': total_trades,
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(win_rate, 1),
        'avg_win_pips': round(avg_win_pips, 1),
        'avg_loss_pips': round(avg_loss_pips, 1),
        'rr_ratio': round(rr_ratio, 2),
        'expectancy_pct': round(expectancy_pct, 4),
        'exit_reasons': exit_reasons,
        'eurusd': {
            'total': len(eurusd),
            'wins': eurusd_wins,
            'wr': round(eurusd_wr, 1)
        },
        'gbpusd': {
            'total': len(gbpusd),
            'wins': gbpusd_wins,
            'wr': round(gbpusd_wr, 1)
        }
    }

def analyze_ny(trades: List[Dict]) -> Dict:
    """Analyze NY-specific metrics for comparison."""
    ny_trades = [t for t in trades if t['session'] == 'ny' and t['signal'] != 'SKIP']
    
    if not ny_trades:
        return None
    
    wins = [t for t in ny_trades if t.get('pnl_pct', 0) > 0]
    losses = [t for t in ny_trades if t.get('pnl_pct', 0) < 0]
    
    total_trades = len(ny_trades)
    win_rate = (len(wins) / total_trades * 100) if total_trades > 0 else 0
    
    avg_win_pips = statistics.mean([t.get('pips', 0) for t in wins]) if wins else 0
    avg_loss_pips = statistics.mean([abs(t.get('pips', 0)) for t in losses]) if losses else 0
    
    if wins and losses:
        avg_win_pct = statistics.mean([t.get('pnl_pct', 0) for t in wins])
        avg_loss_pct = statistics.mean([abs(t.get('pnl_pct', 0)) for t in losses])
        wr = len(wins) / total_trades
        expectancy_pct = (wr * avg_win_pct) - ((1 - wr) * avg_loss_pct)
        rr_ratio = avg_win_pips / avg_loss_pips
    else:
        avg_win_pct = 0
        avg_loss_pct = 0
        expectancy_pct = 0
        rr_ratio = 0
    
    return {
        'total_trades': total_trades,
        'wins': len(wins),
        'losses': len(losses),
        'win_rate': round(win_rate, 1),
        'avg_win_pips': round(avg_win_pips, 1),
        'avg_loss_pips': round(avg_loss_pips, 1),
        'rr_ratio': round(rr_ratio, 2),
        'expectancy_pct': round(expectancy_pct, 4)
    }

def generate_report(results: Dict):
    """Generate comprehensive London performance report."""
    print("=" * 80)
    print("LONDON PERFORMANCE ANALYSIS REPORT")
    print("=" * 80)
    print()
    
    # Summary table: SL=40 vs SL=3 by year
    print("LONDON WIN RATE BY YEAR AND SL VALUE")
    print("-" * 80)
    print(f"{'Year':<8} {'SL=40':<15} {'SL=3':<15} {'Difference':<15} {'Winner'}")
    print("-" * 80)
    
    years = sorted(set(k[0] for k in results.keys()))
    for year in years:
        sl40 = results.get((year, 40), {}).get('trades', [])
        sl3 = results.get((year, 3), {}).get('trades', [])
        
        london_40 = analyze_london(sl40)
        london_3 = analyze_london(sl3)
        
        if london_40 and london_3:
            diff = london_3['win_rate'] - london_40['win_rate']
            winner = 'SL=3' if diff > 0 else 'SL=40'
            
            print(f"{year:<8} {london_40['win_rate']:>5.1f}% ({london_40['total_trades']:>3} trades)  "
                  f"{london_3['win_rate']:>5.1f}% ({london_3['total_trades']:>3} trades)  "
                  f"{diff:+>5.1f}%       {winner}")
    print()
    
    # Detailed London breakdown
    print("LONDON DETAILED METRICS")
    print("-" * 80)
    
    print("\nSL=40 PIPS:")
    print("-" * 40)
    for year in years:
        data = results.get((year, 40), {}).get('trades', [])
        london = analyze_london(data)
        if london:
            print(f"{year}: {london['win_rate']}% WR, {london['wins']}W/{london['losses']}L, "
                  f"{london['total_trades']} trades")
            print(f"      EUR/USD: {london['eurusd']['wr']}% WR, "
                  f"GBP/USD: {london['gbpusd']['wr']}% WR")
            print(f"      Expectancy: {london['expectancy_pct']}% per trade")
            print(f"      Exits: {london['exit_reasons']}")
            print()
    
    print("SL=3 PIPS:")
    print("-" * 40)
    for year in years:
        data = results.get((year, 3), {}).get('trades', [])
        london = analyze_london(data)
        if london:
            print(f"{year}: {london['win_rate']}% WR, {london['wins']}W/{london['losses']}L, "
                  f"{london['total_trades']} trades")
            print(f"      EUR/USD: {london['eurusd']['wr']}% WR, "
                  f"GBP/USD: {london['gbpusd']['wr']}% WR")
            print(f"      Expectancy: {london['expectancy_pct']}% per trade")
            print(f"      Exits: {london['exit_reasons']}")
            print()
    
    # London vs NY comparison
    print("LONDON VS NY COMPARISON")
    print("-" * 80)
    print(f"{'Year':<8} {'SL':<6} {'London WR':<12} {'NY WR':<12} {'Diff':<8} {'London Expectancy':<18} {'NY Expectancy'}")
    print("-" * 80)
    
    for year in years:
        for sl_value in [40, 3]:
            data = results.get((year, sl_value), {}).get('trades', [])
            london = analyze_london(data)
            ny = analyze_ny(data)
            
            if london and ny:
                diff = london['win_rate'] - ny['win_rate']
                print(f"{year:<8} {sl_value:<6} {london['win_rate']:>5.1f}%       "
                      f"{ny['win_rate']:>5.1f}%       {diff:>+4.1f}%   "
                      f"{london['expectancy_pct']:>8.4f}%       {ny['expectancy_pct']:>8.4f}%")
    print()
    
    # Aggregate statistics
    print("AGGREGATE STATISTICS (ALL YEARS)")
    print("-" * 80)
    
    for sl_value in [40, 3]:
        all_trades = []
        for year in years:
            data = results.get((year, sl_value), {}).get('trades', [])
            all_trades.extend(data)
        
        london = analyze_london(all_trades)
        ny = analyze_ny(all_trades)
        
        print(f"\nSL={sl_value} PIPS:")
        if london:
            print(f"  London: {london['win_rate']}% WR ({london['total_trades']} trades)")
            print(f"          EUR/USD: {london['eurusd']['wr']}% WR, GBP/USD: {london['gbpusd']['wr']}% WR")
            print(f"          Expectancy: {london['expectancy_pct']}% per trade")
            print(f"          R:R Ratio: {london['rr_ratio']}")
            print(f"          Exits: {london['exit_reasons']}")
        if ny:
            print(f"  NY: {ny['win_rate']}% WR ({ny['total_trades']} trades)")
            print(f"      Expectancy: {ny['expectancy_pct']}% per trade")
            print(f"      R:R Ratio: {ny['rr_ratio']}")
    
    print()
    print("=" * 80)
    print("KEY FINDINGS")
    print("=" * 80)
    
    # Generate key findings
    findings = []
    
    for year in years:
        sl40 = results.get((year, 40), {}).get('trades', [])
        sl3 = results.get((year, 3), {}).get('trades', [])
        
        london_40 = analyze_london(sl40)
        london_3 = analyze_london(sl3)
        
        if london_40 and london_3:
            if london_40['win_rate'] < 50 and london_3['win_rate'] < 50:
                findings.append(f"Year {year}: Both SL values below 50% WR threshold")
            elif london_40['win_rate'] >= 50 and london_3['win_rate'] >= 50:
                findings.append(f"Year {year}: Both SL values meet 50% WR threshold")
            else:
                better_sl = 'SL=40' if london_40['win_rate'] > london_3['win_rate'] else 'SL=3'
                findings.append(f"Year {year}: {better_sl} performs better")
    
    if findings:
        for i, finding in enumerate(findings, 1):
            print(f"{i}. {finding}")
    
    print()
    print("=" * 80)

def main():
    results = load_results()
    if not results:
        print("No backtest results found. Run run_london_tests.py first.")
        return
    
    generate_report(results)
    
    # Save report to file
    report_path = RESULTS_DIR / "LONDON_ANALYSIS_REPORT.txt"
    import sys
    original_stdout = sys.stdout
    
    with open(report_path, 'w') as f:
        sys.stdout = f
        generate_report(results)
        sys.stdout = original_stdout
    
    print(f"Report saved to: {report_path}")

if __name__ == "__main__":
    main()
