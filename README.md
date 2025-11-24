# Remora Backtesting Framework

This directory contains the complete backtesting framework for validating Remora Risk Engine performance.

## Overview

The backtesting framework allows you to:
- Reconstruct historical Remora risk data
- Run backtests comparing baseline strategies vs Remora-enhanced strategies
- Generate comprehensive metrics and visualizations
- Reproduce all results independently

## Quick Start

### 1. Prepare Historical Data

First, you need historical OHLCV data and external market data:

```bash
# Fetch OHLCV data
python data/ohlcv_fetcher.py --pair BTC/USDT --timeframe 5m --start 2020-01-01 --end 2025-12-31

# Fetch external data (VIX, DXY, Fear & Greed, etc.)
python historical_remora/historical_data_fetcher.py --start 2020-01-01 --end 2025-12-31

# Build Remora history
python historical_remora/remora_history_builder.py
```

### 2. Run Backtests

```bash
# Run all backtests
./run_backtests.sh

# Or run Python script directly
python run_backtests.py
```

### 3. View Results

Results are saved in `results/` directory:
- JSON files with detailed metrics
- Comparison files showing baseline vs Remora
- Summary reports

## Directory Structure

```
backtesting/
├── historical_remora/     # Historical data reconstruction
│   ├── historical_data_fetcher.py
│   ├── remora_history_builder.py
│   └── data_verification.py
├── data/                  # OHLCV data management
│   ├── ohlcv_fetcher.py
│   └── data_validator.py
├── strategies/            # Trading strategies
│   ├── NFIQuickstartStrategy.py
│   ├── MACDCrossStrategy.py
│   ├── RSIEMAStrategy.py
│   ├── BollingerBreakoutStrategy.py
│   └── RemoraStrategyWrapper.py
├── visualizations/        # Chart generation
│   ├── equity_curves.py
│   ├── drawdown_comparison.py
│   └── risk_metrics.py
├── results/              # Backtest results
│   └── graphs/           # Generated charts
├── backtest_runner.py    # Backtest execution
├── metrics_extractor.py  # Metrics extraction
└── run_backtests.sh      # Master script
```

## Strategies Included

1. **NFI Quickstart** - Simple moving average crossover
2. **MACD Cross** - MACD line crossover strategy
3. **RSI + EMA** - RSI and EMA trend following
4. **Bollinger Breakout** - Bollinger Band breakout

Each strategy has a baseline version and a Remora-enhanced version.

## Time Periods

Backtests cover multiple market regimes:
- **2020-2021**: Bull market
- **2022**: Bear market
- **2023-2024**: Sideways/choppy market
- **2024-2025**: Mixed conditions

## Metrics Collected

### Trading Metrics
- Total profit %
- Total number of trades
- Win rate %
- Profit factor
- Sharpe ratio
- Sortino ratio
- Maximum drawdown
- Exposure time
- Average trade duration

### Remora-Specific Metrics
- % of trades filtered out
- Average risk_score of losing trades
- Average risk_score of winning trades
- Distribution of returns by risk_class
- Distribution of returns by regime
- % of losing trades occurring during Remora high-risk periods

## Reproducing Results

All data and code needed to reproduce results is included:
1. Historical data fetching scripts
2. Remora history builder
3. All strategies
4. Backtest execution scripts
5. Visualization scripts

See [METHODOLOGY.md](METHODOLOGY.md) for detailed methodology.

## Results

See [RESULTS.md](RESULTS.md) for summary of backtest results.

## Troubleshooting

### Common Issues

**No historical data available:**
- Run data fetching scripts first
- Check data directory permissions

**Backtests fail:**
- Ensure Freqtrade is installed and configured
- Check that strategies are in the correct location
- Verify OHLCV data is available for the time period

**Missing Remora history:**
- Run `remora_history_builder.py` first
- Ensure external data is fetched

## Support

For issues or questions, please open an issue in the repository.

