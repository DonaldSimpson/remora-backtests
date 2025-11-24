#!/bin/bash
# Master script to run all backtests

set -e  # Exit on error

# Configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RESULTS_DIR="${SCRIPT_DIR}/results"
LOG_FILE="${RESULTS_DIR}/backtest_log_$(date +%Y%m%d_%H%M%S).log"

# Create results directory
mkdir -p "${RESULTS_DIR}"

# Logging function
log() {
    echo "[$(date +'%Y-%m-%d %H:%M:%S')] $1" | tee -a "${LOG_FILE}"
}

log "Starting backtest suite"
log "Results directory: ${RESULTS_DIR}"

# Define strategies
BASELINE_STRATEGIES=(
    "NFIQuickstartStrategy"
    "MACDCrossStrategy"
    "RSIEMAStrategy"
    "BollingerBreakoutStrategy"
)

REMORA_STRATEGIES=(
    "NFIQuickstartRemoraStrategy"
    "MACDCrossRemoraStrategy"
    "RSIEMARemoraStrategy"
    "BollingerBreakoutRemoraStrategy"
)

# Define time periods
PERIODS=(
    "20200101-20211231"  # 2020-2021 Bull
    "20220101-20221231"  # 2022 Bear
    "20230101-20241231"  # 2023-2024 Sideways/Choppy
    "20240101-20251231"  # 2024-2025 Mixed
)

# Trading pair
PAIR="BTC/USDT"
TIMEFRAME="5m"

# Python script to run backtests
PYTHON_SCRIPT="${SCRIPT_DIR}/run_backtests.py"

# Check if Python script exists, if not create it
if [ ! -f "${PYTHON_SCRIPT}" ]; then
    log "Creating Python backtest runner script..."
    cat > "${PYTHON_SCRIPT}" << 'PYTHON_EOF'
#!/usr/bin/env python3
"""Run all backtest combinations."""

import sys
import os
from pathlib import Path

# Add backtesting directory to path
sys.path.insert(0, str(Path(__file__).parent))

from backtest_runner import BacktestRunner
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
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
    
    periods = [
        "20200101-20211231",
        "20220101-20221231",
        "20230101-20241231",
        "20240101-20251231"
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
    from metrics_extractor import MetricsExtractor
    extractor = MetricsExtractor(runner.results_dir)
    
    # Aggregate all results
    logger.info("Generating summary report...")
    # Summary generation would go here
    
    logger.info("Backtest suite complete!")

if __name__ == "__main__":
    main()
PYTHON_EOF
    chmod +x "${PYTHON_SCRIPT}"
fi

# Run Python script
log "Executing Python backtest runner..."
python3 "${PYTHON_SCRIPT}" 2>&1 | tee -a "${LOG_FILE}"

log "Backtest suite complete!"
log "Results saved to: ${RESULTS_DIR}"
log "Log file: ${LOG_FILE}"

