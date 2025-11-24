# Setup Guide - Remora Backtesting

This guide will walk you through setting up and running the Remora backtesting framework.

## Prerequisites

1. **Python 3.8+**
   ```bash
   python3 --version
   ```

2. **Freqtrade** - Required for running backtests
   ```bash
   # Install Freqtrade
   # See: https://www.freqtrade.io/en/stable/installation/
   ```

3. **Required Python packages**
   ```bash
   pip install -r requirements.txt
   ```

## Step-by-Step Setup

### 1. Clone and Navigate

```bash
git clone https://github.com/DonaldSimpson/remora-backtests.git
cd remora-backtests
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Fetch Historical Data

You need two types of data:

#### A. OHLCV Data (Price Data)

```bash
python data/ohlcv_fetcher.py --pair BTC/USDT --timeframe 5m --start 2020-01-01 --end 2025-12-31
```

This will download BTC/USDT 5-minute candles and save them as Parquet files.

#### B. External Market Data

```bash
python historical_remora/historical_data_fetcher.py --start 2020-01-01 --end 2025-12-31
```

This fetches:
- VIX (Volatility Index)
- DXY (Dollar Index)
- Fear & Greed Index
- BTC Dominance
- Funding Rates
- Open Interest
- Liquidations

### 4. Build Remora History

Once you have the data, build the historical Remora risk scores:

```bash
python build_remora_history.py
```

This will:
- Combine OHLCV and external data
- Calculate historical risk scores using the RiskCalculator
- Generate `historical_remora/remora_history.csv`

**Note**: This requires access to the Remora RiskCalculator. You may need to adjust the import paths in `remora_history_builder.py` to match your setup.

### 5. Configure Freqtrade

Create a minimal Freqtrade config (or use the provided `user_data/config.json`):

```json
{
  "stake_currency": "USDT",
  "stake_amount": 100,
  "timeframe": "5m",
  "exchange": {
    "name": "binance",
    "ccxt_config": {}
  },
  "max_open_trades": 1,
  "minimal_roi": {
    "0": 10
  },
  "stoploss": -0.10,
  "trailing_stop": false,
  "trailing_stop_positive": 0.0
}
```

### 6. Run Backtests

Run all backtests:

```bash
python run_backtests.py
```

Or use the shell script:

```bash
./run_backtests.sh
```

This will:
- Run baseline strategies for all periods
- Run Remora-enhanced strategies for all periods
- Save results in `results/` directory

### 7. Analyze Results

```bash
python analyze_results.py
```

This generates summary reports and comparison files.

## Troubleshooting

### Import Errors

If you get import errors for `app` modules, you may need to:
1. Adjust the Python path in scripts
2. Install the Remora service as a package
3. Copy necessary modules to the backtesting directory

### Missing Data

If backtests fail due to missing data:
1. Check that OHLCV data files exist
2. Verify `remora_history.csv` was generated
3. Ensure data covers the required time periods

### Freqtrade Issues

- Ensure Freqtrade is properly installed
- Check that strategies are in the correct location (`user_data/strategies/`)
- Verify config.json is valid

## Data Requirements

Minimum data needed:
- OHLCV: BTC/USDT 5m candles (2020-01-01 to 2025-12-31)
- External data: VIX, DXY, Fear & Greed, Funding Rates, etc.
- Remora history: Generated from above data

## Expected Runtime

- Data fetching: 10-30 minutes (depending on API limits)
- Remora history build: 5-15 minutes
- Backtests: 30-60 minutes (20 test cases)
- Analysis: 1-2 minutes

## Next Steps

Once setup is complete:
1. Review results in `results/` directory
2. Check `EXECUTIVE_SUMMARY.md` for key findings
3. See `COMPREHENSIVE_PROOF_REPORT.md` for detailed analysis
4. Visit the live results page: https://remora-ai.com/evidence-backtesting.php

## Support

For issues or questions:
- Open an issue on GitHub
- Check the [METHODOLOGY.md](METHODOLOGY.md) for technical details
