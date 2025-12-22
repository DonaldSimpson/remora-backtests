# Remora Backtesting Framework for Freqtrade

**Reproducible backtesting framework for validating Remora's impact on Freqtrade strategies**

[![Remora Website](https://img.shields.io/badge/Remora-remora--ai.com-8b6bff)](https://remora-ai.com)
[![Blog Post](https://img.shields.io/badge/Blog-Advanced%20Risk%20Management-8b6bff)](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/)
[![Freqtrade](https://img.shields.io/badge/Built%20for-Freqtrade-8b6bff)](https://www.freqtrade.io)

[<img src="images/remora-social-card.jpg" alt="Remora Risk Engine - Stop Bad Trades Before They Happen" width="600">](https://remora-ai.com)

### BUILT FOR:

[<img src="images/freqtrade.png" alt="Freqtrade" width="200">](https://www.freqtrade.io)

## What is Remora?

Remora is a **market awareness layer specifically built for Freqtrade strategies**. It answers the question: "Should I be trading at all right now?" - not "Is this a good entry signal?"

Remora adds a thin, transparent, fail-safe risk layer that blocks trades during high-risk market conditions, helping Freqtrade users reduce drawdowns and improve risk-adjusted performance.

**Key Features:**
- ✅ Simple API call - not a plugin
- ✅ Fully transparent - returns reasoning, not just boolean
- ✅ Fail-safe design - fail-open by default
- ✅ Easy to remove - just delete a few lines
- ✅ Multiple data sources with redundancy/failover

## About This Repository

This repository enables **independent verification** of Remora's impact on Freqtrade strategies through comprehensive backtesting. All results are reproducible, and the complete methodology is documented.

### What This Framework Does

- Reconstructs historical Remora risk data (6 years of data)
- Runs backtests comparing baseline Freqtrade strategies vs Remora-enhanced strategies
- Tests across multiple market regimes (bull, bear, sideways, mixed)
- Generates comprehensive metrics and visualisations
- Provides complete reproducibility for independent validation

### Proven Results

**See the detailed analysis:** [Advanced Risk Management for Freqtrade](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/)

**Summary of Backtest Results (6 years, 4 strategies, 20 tests):**
- **+1.54%** profit improvement
- **+1.55%** drawdown reduction
- **4.3%** of trades filtered (high-risk periods avoided)
- Improved risk-adjusted returns across all market regimes

All results are Freqtrade-specific and validated using real Freqtrade strategies.

## Quick Start

### 1. Install Dependencies

```bash
# Install Freqtrade (required)
# See: https://www.freqtrade.io/en/stable/installation/

# Install Python packages
pip install -r requirements.txt
```

### 2. Prepare Historical Data

```bash
# Fetch OHLCV data for Freqtrade backtesting
python fetch_data_robust.py --pair BTC/USDT --timeframe 5m --start 2020-01-01 --end 2025-12-31

# Fetch external market data (VIX, DXY, Fear & Greed, etc.)
python historical_remora/historical_data_fetcher.py --start 2020-01-01 --end 2025-12-31

# Build Remora history
python build_remora_history.py
```

### 3. Run Backtests

```bash
# Run all backtests (baseline vs Remora-enhanced Freqtrade strategies)
./run_backtests.sh

# Or run Python script directly
python run_backtests.py
```

### 4. View Results

Results are saved in `results/` directory:
- JSON files with detailed metrics
- Comparison files showing baseline vs Remora
- Summary reports
- Visualisations (equity curves, drawdown comparisons, etc.)

## Freqtrade Strategies Tested

All strategies are standard Freqtrade strategies with Remora integration:

1. **NFI Quickstart** - Simple moving average crossover
2. **MACD Cross** - MACD line crossover strategy
3. **RSI + EMA** - RSI and EMA trend following
4. **Bollinger Breakout** - Bollinger Band breakout

Each strategy has:
- **Baseline version** - Standard Freqtrade strategy
- **Remora-enhanced version** - Same strategy with Remora risk filtering

### How Remora Integrates with Freqtrade

Remora filtering is added via `confirm_trade_entry()` method:

```python
def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, **kwargs):
    # REMORA: Check if current market conditions are safe to trade
    if not remora_allows(timestamp=current_time):
        return False  # Block trade during high-risk periods
    
    # Your existing strategy logic continues unchanged
    return True
```

See the [integration examples](https://remora-ai.com) and [blog post](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/) for detailed, color-coded examples.

## Test Periods

Backtests cover multiple market regimes to validate Remora across different conditions:

- **2020-2021**: Bull market
- **2022**: Bear market (critical for drawdown protection)
- **2023-2024**: Sideways/choppy market (hardest environment for algos)
- **2024-2025**: Mixed conditions
- **2020-2025**: Full 6-year period (maximum statistical power)

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
- % of trades filtered out (high-risk periods avoided)
- Average risk_score of losing trades
- Average risk_score of winning trades
- Distribution of returns by risk_class
- Distribution of returns by regime
- % of losing trades occurring during Remora high-risk periods

## Reproducibility

Everything required to reproduce the tests is included:

1. ✅ Historical data fetching scripts
2. ✅ Remora history builder
3. ✅ All Freqtrade strategies (baseline and Remora-enhanced)
4. ✅ Backtest execution scripts
5. ✅ Visualisation scripts
6. ✅ Complete methodology documentation

See [METHODOLOGY.md](METHODOLOGY.md) for detailed methodology.

## Resources

### Website & Documentation
- **Main Website:** [remora-ai.com](https://remora-ai.com)
- **Blog Post (Detailed Analysis):** [Advanced Risk Management for Freqtrade](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/)
- **API Documentation:** [remora-ai.com/api-docs.php](https://remora-ai.com/api-docs.php)
- **Live Status:** [remora-ai.com/status.php](https://remora-ai.com/status.php)

### Freqtrade Resources
- **Freqtrade:** [freqtrade.io](https://www.freqtrade.io)
- **Freqtrade Integration Examples:** [remora-freqtrade repository](https://github.com/DonaldSimpson/remora-freqtrade)

### Related Repositories
- **remora-freqtrade:** Freqtrade integration examples and onboarding guides
- **remora-backtests:** This repository - reproducible backtesting framework

## Key Messaging

### What Remora Does
- ✅ Lets you know if current market conditions are safe to trade in
- ✅ Blocks trades during high-risk periods (volatility spikes, regime changes, etc.)
- ✅ Provides full transparency (returns reasoning, not just boolean)
- ✅ Uses multiple data sources with redundancy and failover

### What Remora Does NOT Do
- ❌ Does not replace your Freqtrade strategy logic
- ❌ Does not optimise entry/exit signals
- ❌ Does not require complex configuration
- ❌ Does not lock you in (easy to remove)

### Why Freqtrade Users Should Care
- **Reduced Drawdowns:** Avoid trading during high-risk market conditions
- **Improved Risk-Adjusted Performance:** Better Sharpe and Sortino ratios
- **Transparency:** See exactly why trades were blocked
- **Fail-Safe:** If Remora is unavailable, trades proceed normally (fail-open)
- **Easy Integration:** Simple API call, not a plugin

## Setup Guide

For detailed setup instructions, see [SETUP_GUIDE.md](SETUP_GUIDE.md).

## Troubleshooting

### Common Issues

**No historical data available:**
- Run data fetching scripts first
- Check data directory permissions

**Backtests fail:**
- Ensure Freqtrade is installed and configured
- Check that strategies are in the correct location (`user_data/strategies/`)
- Verify OHLCV data is available for the time period

**Missing Remora history:**
- Run `build_remora_history.py` first
- Ensure external data is fetched

## Support

For issues or questions:
- Open an issue in this repository
- Check the [METHODOLOGY.md](METHODOLOGY.md) for technical details
- Visit [remora-ai.com](https://remora-ai.com) for documentation

## License

See LICENSE file for details.

---

**Built for Freqtrade** | [Remora Website](https://remora-ai.com) | [Blog Post](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/) | [Freqtrade](https://www.freqtrade.io)
