#!/usr/bin/env python3
"""
Analyze backtest results and generate summary statistics.

Extracts key metrics and calculates improvements from Remora filtering.
"""

import json
import re
from pathlib import Path
from typing import Dict, List, Optional
import pandas as pd

def parse_freqtrade_output(output: str) -> Dict:
    """Parse Freqtrade backtest output to extract metrics."""
    metrics = {}
    
    if not output:
        return metrics
    
    # Parse table format - look for the BACKTESTING REPORT table
    # The table has columns: Pair | Trades | Avg Profit % | Tot Profit USDT | Tot Profit % | Duration | Win Draw Loss | Win%
    # Find the TOTAL row and parse it
    lines = output.split('\n')
    for line in lines:
        if 'TOTAL' in line and '│' in line and any(c.isdigit() for c in line):
            # Extract numbers from the line
            numbers = re.findall(r'[\d.-]+', line)
            
            if len(numbers) >= 7:
                try:
                    metrics['total_trades'] = int(numbers[0])
                    metrics['avg_profit_pct'] = float(numbers[1])
                    metrics['profit_usdt'] = float(numbers[2])
                    metrics['profit_pct'] = float(numbers[3])
                    # Skip duration (numbers[4], 5, 6 if time format like 3:08:00)
                    # Win Draw Loss pattern: | 666 | 0 1662 |
                    # Look for the pattern in the line itself
                    win_loss_match = re.search(r'\|\s+(\d+)\s+\|\s+(\d+)\s+(\d+)\s+\|', line)
                    if win_loss_match:
                        metrics['wins'] = int(win_loss_match.group(1))
                        metrics['losses'] = int(win_loss_match.group(3))
                        total = metrics['wins'] + metrics['losses']
                        if total > 0:
                            metrics['win_rate'] = (metrics['wins'] / total) * 100
                    # Win% is usually the last number
                    if len(numbers) >= 8:
                        metrics['win_rate'] = float(numbers[-1])
                except (ValueError, IndexError) as e:
                    pass
            break
    else:
        # Fallback: try to extract individual values
        # Trades
        trades_match = re.search(r'\|\s+TOTAL\s+\|\s+(\d+)', output)
        if trades_match:
            metrics['total_trades'] = int(trades_match.group(1))
        
        # Profit percentage
        profit_match = re.search(r'Total profit\s+([\d.-]+)\s+USDT\s+\(([\d.-]+)%\)', output)
        if profit_match:
            metrics['profit_usdt'] = float(profit_match.group(1))
            metrics['profit_pct'] = float(profit_match.group(2))
        else:
            profit_match = re.search(r'Total profit\s+([\d.-]+)%', output)
            if profit_match:
                metrics['profit_pct'] = float(profit_match.group(1))
        
        # Win rate
        winrate_match = re.search(r'Win rate\s+([\d.]+)%', output, re.IGNORECASE)
        if winrate_match:
            metrics['win_rate'] = float(winrate_match.group(1))
    
    # Extract profit factor from summary section
    pf_match = re.search(r'Profit factor\s+([\d.]+)', output, re.IGNORECASE)
    if pf_match:
        metrics['profit_factor'] = float(pf_match.group(1))
    
    # Extract Sharpe ratio
    sharpe_match = re.search(r'Sharpe Ratio\s+([\d.-]+)', output, re.IGNORECASE)
    if sharpe_match:
        metrics['sharpe_ratio'] = float(sharpe_match.group(1))
    
    # Extract Sortino ratio
    sortino_match = re.search(r'Sortino Ratio\s+([\d.-]+)', output, re.IGNORECASE)
    if sortino_match:
        metrics['sortino_ratio'] = float(sortino_match.group(1))
    
    # Extract max drawdown - look in the summary section
    # Pattern: "Max Drawdown 123.45 USDT (12.34%)" or "Absolute drawdown 123.45 USDT (12.34%)"
    dd_match = re.search(r'(?:Max|Absolute) drawdown\s+([\d.-]+)\s+USDT\s+\(([\d.-]+)%\)', output, re.IGNORECASE)
    if dd_match:
        metrics['max_drawdown_usdt'] = abs(float(dd_match.group(1)))
        metrics['max_drawdown_pct'] = abs(float(dd_match.group(2)))
    else:
        dd_match = re.search(r'(?:Max|Absolute) drawdown\s+([\d.-]+)%', output, re.IGNORECASE)
        if dd_match:
            metrics['max_drawdown_pct'] = abs(float(dd_match.group(1)))
    
    # Extract exposure
    exposure_match = re.search(r'Exposure\s+([\d.]+)%', output, re.IGNORECASE)
    if exposure_match:
        metrics['exposure_pct'] = float(exposure_match.group(1))
    
    return metrics


def analyze_comparisons(comparisons: List[Dict]) -> Dict:
    """Analyze all comparisons and calculate aggregate statistics."""
    
    results = []
    
    for comp in comparisons:
        baseline = comp.get('baseline', {})
        remora = comp.get('remora', {})
        
        if not baseline.get('success') or not remora.get('success'):
            continue
        
        # Parse outputs
        baseline_metrics = parse_freqtrade_output(baseline.get('raw_output', ''))
        remora_metrics = parse_freqtrade_output(remora.get('raw_output', ''))
        
        if not baseline_metrics or not remora_metrics:
            continue
        
        # Calculate improvements
        profit_improvement = 0
        if baseline_metrics.get('profit_pct') and remora_metrics.get('profit_pct'):
            profit_improvement = remora_metrics['profit_pct'] - baseline_metrics['profit_pct']
        
        drawdown_reduction = 0
        if baseline_metrics.get('max_drawdown_pct') and remora_metrics.get('max_drawdown_pct'):
            drawdown_reduction = baseline_metrics['max_drawdown_pct'] - remora_metrics['max_drawdown_pct']
        
        trades_reduction = 0
        if baseline_metrics.get('total_trades') and remora_metrics.get('total_trades'):
            trades_reduction = baseline_metrics['total_trades'] - remora_metrics['total_trades']
            trades_reduction_pct = (trades_reduction / baseline_metrics['total_trades']) * 100 if baseline_metrics['total_trades'] > 0 else 0
        else:
            trades_reduction_pct = 0
        
        result = {
            'strategy': baseline.get('strategy', 'unknown'),
            'period': baseline.get('timerange', 'unknown'),
            'baseline': baseline_metrics,
            'remora': remora_metrics,
            'improvements': {
                'profit_pct': profit_improvement,
                'drawdown_reduction_pct': drawdown_reduction,
                'trades_reduction': trades_reduction,
                'trades_reduction_pct': trades_reduction_pct,
                'win_rate_improvement': remora_metrics.get('win_rate', 0) - baseline_metrics.get('win_rate', 0),
                'profit_factor_improvement': remora_metrics.get('profit_factor', 0) - baseline_metrics.get('profit_factor', 0),
            }
        }
        
        results.append(result)
    
    return results


def generate_summary(results: List[Dict]) -> Dict:
    """Generate aggregate summary statistics."""
    
    if not results:
        return {}
    
    df = pd.DataFrame(results)
    
    # Calculate averages
    avg_profit_improvement = df['improvements'].apply(lambda x: x.get('profit_pct', 0)).mean()
    avg_drawdown_reduction = df['improvements'].apply(lambda x: x.get('drawdown_reduction_pct', 0)).mean()
    avg_trades_reduction_pct = df['improvements'].apply(lambda x: x.get('trades_reduction_pct', 0)).mean()
    avg_win_rate_improvement = df['improvements'].apply(lambda x: x.get('win_rate_improvement', 0)).mean()
    
    # Calculate median (more robust to outliers)
    median_profit_improvement = df['improvements'].apply(lambda x: x.get('profit_pct', 0)).median()
    median_drawdown_reduction = df['improvements'].apply(lambda x: x.get('drawdown_reduction_pct', 0)).median()
    
    # Count positive improvements
    positive_profit = (df['improvements'].apply(lambda x: x.get('profit_pct', 0)) > 0).sum()
    positive_drawdown = (df['improvements'].apply(lambda x: x.get('drawdown_reduction_pct', 0)) > 0).sum()
    
    summary = {
        'total_comparisons': len(results),
        'average_improvements': {
            'profit_pct': avg_profit_improvement,
            'drawdown_reduction_pct': avg_drawdown_reduction,
            'trades_reduction_pct': avg_trades_reduction_pct,
            'win_rate_improvement': avg_win_rate_improvement,
        },
        'median_improvements': {
            'profit_pct': median_profit_improvement,
            'drawdown_reduction_pct': median_drawdown_reduction,
        },
        'positive_improvements': {
            'profit_improved': positive_profit,
            'drawdown_reduced': positive_drawdown,
            'profit_improved_pct': (positive_profit / len(results)) * 100,
            'drawdown_reduced_pct': (positive_drawdown / len(results)) * 100,
        },
        'detailed_results': results
    }
    
    return summary


def main():
    """Main analysis function."""
    print("📊 Analyzing Backtest Results")
    print("=" * 60)
    print("")
    
    # Load summary
    summary_path = Path('results/summary.json')
    if not summary_path.exists():
        print("❌ Summary file not found!")
        return
    
    with open(summary_path) as f:
        data = json.load(f)
    
    comparisons = data.get('comparisons', [])
    print(f"Loaded {len(comparisons)} comparisons")
    print("")
    
    # Analyze
    print("Analyzing results...")
    results = analyze_comparisons(comparisons)
    print(f"Successfully analyzed {len(results)} comparisons")
    print("")
    
    # Generate summary
    print("Generating summary statistics...")
    summary = generate_summary(results)
    
    # Save detailed analysis
    analysis_path = Path('results/detailed_analysis.json')
    with open(analysis_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    print(f"✅ Detailed analysis saved to {analysis_path}")
    print("")
    
    # Print summary
    print("=" * 60)
    print("📊 SUMMARY STATISTICS")
    print("=" * 60)
    print("")
    
    avg = summary['average_improvements']
    median = summary['median_improvements']
    positive = summary['positive_improvements']
    
    print(f"Total Comparisons: {summary['total_comparisons']}")
    print("")
    print("💰 PROFIT IMPROVEMENTS:")
    print(f"   Average: {avg['profit_pct']:+.2f}%")
    print(f"   Median:  {median['profit_pct']:+.2f}%")
    print(f"   Improved in: {positive['profit_improved']}/{summary['total_comparisons']} cases ({positive['profit_improved_pct']:.1f}%)")
    print("")
    print("📉 DRAWDOWN REDUCTIONS:")
    print(f"   Average reduction: {avg['drawdown_reduction_pct']:+.2f}%")
    print(f"   Median reduction:  {median['drawdown_reduction_pct']:+.2f}%")
    print(f"   Reduced in: {positive['drawdown_reduced']}/{summary['total_comparisons']} cases ({positive['drawdown_reduced_pct']:.1f}%)")
    print("")
    print("📊 TRADE FILTERING:")
    print(f"   Average trades reduced: {avg['trades_reduction_pct']:.1f}%")
    print("")
    print("🎯 WIN RATE:")
    print(f"   Average improvement: {avg['win_rate_improvement']:+.2f}%")
    print("")
    
    # Calculate money saved
    if avg['profit_pct'] > 0:
        print("=" * 60)
        print("💵 MONEY SAVED ANALYSIS")
        print("=" * 60)
        print("")
        print(f"✅ Remora improves profit by an average of {avg['profit_pct']:.2f}%")
        print(f"✅ Remora reduces drawdown by an average of {avg['drawdown_reduction_pct']:.2f}%")
        print("")
        print("On a $10,000 account:")
        print(f"   - Profit improvement: ${avg['profit_pct'] * 100:.2f} more profit")
        print(f"   - Drawdown reduction: ${avg['drawdown_reduction_pct'] * 100:.2f} less loss")
        print("")
        print("On a $100,000 account:")
        print(f"   - Profit improvement: ${avg['profit_pct'] * 1000:.2f} more profit")
        print(f"   - Drawdown reduction: ${avg['drawdown_reduction_pct'] * 1000:.2f} less loss")
        print("")
    
    print("=" * 60)
    print("✅ Analysis complete!")
    print("=" * 60)


if __name__ == "__main__":
    main()

