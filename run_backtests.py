#!/usr/bin/env python3
"""Run all backtest combinations."""

import sys
import os
from pathlib import Path
from datetime import datetime
import logging

# Add backtesting directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backtest_runner import BacktestRunner
from metrics_extractor import MetricsExtractor

# Set up logging to both file and console
log_file = os.path.join(os.path.dirname(__file__), 'results', f'backtest_progress_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log')
os.makedirs(os.path.join(os.path.dirname(__file__), 'results'), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(log_file),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


def main():
    """Run all backtest combinations."""
    runner = BacktestRunner()
    
    baseline_strategies = [
        "NFIQuickstartStrategy",
        "MACDCrossStrategy",
        "RSIEMAStrategy",
        "BollingerBreakoutStrategy"
    ]
    
    remora_strategies = [
        "NFIQuickstartRemoraStrategy",
        "MACDCrossRemoraStrategy",
        "RSIEMARemoraStrategy",
        "BollingerBreakoutRemoraStrategy"
    ]
    
    # Full 6-year period for maximum statistical power
    periods = [
        "20200101-20251231",  # Full period: 2020-2025 (6 years - IRREFUTABLE)
        # Also test individual periods for detailed analysis
        "20200101-20211231",  # 2020-2021 Bull
        "20220101-20221231",  # 2022 Bear
        "20230101-20241231",  # 2023-2024 Sideways/Choppy
        "20240101-20251231"   # 2024-2025 Mixed
    ]
    
    pair = "BTC/USDT"
    timeframe = "5m"
    
    all_comparisons = []
    
    for i, baseline_strat in enumerate(baseline_strategies):
        remora_strat = remora_strategies[i]
        
        for period in periods:
            logger.info(f"Running: {baseline_strat} vs {remora_strat} for {period}")
            
            try:
                comparison = runner.run_comparison(
                    baseline_strategy=baseline_strat,
                    remora_strategy=remora_strat,
                    timerange=period,
                    pair=pair,
                    timeframe=timeframe
                )
                all_comparisons.append(comparison)
                logger.info(f"✓ Completed: {baseline_strat} vs {remora_strat} for {period}")
            except Exception as e:
                logger.error(f"✗ Error: {e}")
                continue
    
    logger.info(f"Completed {len(all_comparisons)} comparisons")
    
    # Generate summary
    extractor = MetricsExtractor(runner.results_dir)
    
    # Save aggregated results
    logger.info("Generating summary report...")
    
    # Create summary
    summary = {
        'total_comparisons': len(all_comparisons),
        'comparisons': all_comparisons
    }
    
    summary_path = os.path.join(runner.results_dir, 'summary.json')
    import json
    with open(summary_path, 'w') as f:
        json.dump(summary, f, indent=2, default=str)
    
    logger.info(f"Summary saved to {summary_path}")
    logger.info("Backtest suite complete!")


if __name__ == "__main__":
    main()

