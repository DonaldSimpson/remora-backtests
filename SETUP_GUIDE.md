# Setup Guide - Remora Backtesting for Freqtrade

This guide will walk you through setting up and running the Remora backtesting framework to validate Remora's impact on **Freqtrade strategies**.

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
   
   **Note:** This framework uses Freqtrade's native backtesting engine to ensure realistic results.

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

You need two types of data for Freqtrade backtesting:

#### A. OHLCV Data (Price Data for Freqtrade)

```bash
python fetch_data_robust.py --pair BTC/USDT --timeframe 5m --start 2020-01-01 --end 2025-12-31
```

This will download BTC/USDT 5-minute candles (compatible with Freqtrade) and save them as Parquet files.

#### B. External Market Data (for Remora Risk Calculation)

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

**Important:** Ensure your Freqtrade strategies are in the correct location (`user_data/strategies/`).

### 6. Run Backtests

Run all backtests comparing baseline Freqtrade strategies vs Remora-enhanced Freqtrade strategies:

```bash
python run_backtests.py
```

Or use the shell script:

```bash
./run_backtests.sh
```

This will:
- Run baseline Freqtrade strategies for all periods
- Run Remora-enhanced Freqtrade strategies for all periods
- Use Freqtrade's native backtesting engine
- Save results in `results/` directory

### 7. Analyze Results

```bash
python analyze_results.py
```

This generates summary reports and comparison files showing the impact of Remora on Freqtrade strategies.

## Understanding the Results

### What Gets Tested

The framework tests:
- **Baseline Freqtrade strategies** - Standard Freqtrade implementations without Remora
- **Remora-enhanced Freqtrade strategies** - Same strategies with Remora risk filtering

### Key Metrics

Results show:
- Profit improvement (baseline vs Remora-enhanced)
- Drawdown reduction
- Number of trades filtered (high-risk periods avoided)
- Risk-adjusted returns (Sharpe, Sortino)
- Performance across different market regimes

### Detailed Analysis

For comprehensive analysis and financial impact calculations, see:
- **Blog Post:** [Advanced Risk Management for Freqtrade](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/)
- **Risk engine (self-host):** [DonaldSimpson/remora](https://github.com/DonaldSimpson/remora)

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
- Ensure Freqtrade can access the data directory

### Remora History Issues

- Run `build_remora_history.py` first
- Ensure external data is fetched
- Check that `remora_history.csv` contains data for your test periods

## Data Requirements

Minimum data needed for Freqtrade backtesting:
- OHLCV: BTC/USDT 5m candles (2020-01-01 to 2025-12-31)
- External data: VIX, DXY, Fear & Greed, Funding Rates, etc.
- Remora history: Generated from above data

## Expected Runtime

- Data fetching: 10-30 minutes (depending on API limits)
- Remora history build: 5-15 minutes
- Backtests: 30-60 minutes (20 test cases using Freqtrade)
- Analysis: 1-2 minutes

## Next Steps

Once setup is complete:

1. **Review Results** - Check `results/` directory for detailed metrics
2. **Read the Blog Post** - [Advanced Risk Management for Freqtrade](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/)
3. **See the integration repo** - [remora-freqtrade](https://github.com/DonaldSimpson/remora-freqtrade) for integration examples
4. **Test Your Own Strategies** - Use this framework to test your own Freqtrade strategies with and without Remora

## Integration with Your Freqtrade Strategies

To integrate Remora with your own Freqtrade strategies:

1. See the [integration examples](https://github.com/DonaldSimpson/remora-freqtrade) in remora-freqtrade
2. Check the [blog post](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/) for detailed, color-coded examples
3. Review the [remora-freqtrade repository](https://github.com/DonaldSimpson/remora-freqtrade) for onboarding guides

**Key Integration Points:**
- Add Remora check in `confirm_trade_entry()` method
- Use `remora_allows()` to check if current market conditions are safe
- Remora returns `False` during high-risk periods, blocking the trade
- Fail-open behaviour: if Remora is unavailable, trades proceed normally

## Support

For issues or questions:
- Open an issue on GitHub
- Check the [METHODOLOGY.md](METHODOLOGY.md) for technical details
- See [DonaldSimpson/remora](https://github.com/DonaldSimpson/remora) for documentation
- See [Freqtrade documentation](https://www.freqtrade.io) for Freqtrade-specific help

---

**Built for Freqtrade** | [Remora](https://github.com/DonaldSimpson/remora) | [Blog Post](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/) | [Freqtrade](https://www.freqtrade.io)
