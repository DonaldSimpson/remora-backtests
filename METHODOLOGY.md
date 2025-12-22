# Backtesting Methodology for Remora Risk Engine with Freqtrade

This document explains exactly how to reproduce the backtests used to validate the Remora Risk Engine's impact on **Freqtrade strategies**. It is designed to be transparent, deterministic, and independently verifiable.

## 1. Purpose

The goals of this study are:

1. To measure whether using the Remora Risk Engine improves **Freqtrade strategy** outcomes
2. To quantify reductions in drawdown, losses, and exposure during high-risk market conditions for Freqtrade users
3. To demonstrate that these improvements are strategy-agnostic and reproducible across different Freqtrade strategies
4. To allow any Freqtrade user to validate the results using this repository

## 2. Test Design

### Comparison Method

The tests compare:
- **Baseline:** Freqtrade strategy without filters (standard Freqtrade behaviour)
- **Remora-Enhanced:** Same Freqtrade strategy with Remora blocking entries during high-risk periods

All tests use **Freqtrade's native backtesting engine** to ensure realistic results.

### Freqtrade Strategies Tested

1. **NFI Quickstart** - Simple moving average crossover (Freqtrade example strategy)
2. **MACD Cross** - MACD line crossover strategy
3. **RSI + EMA** - RSI and EMA trend following
4. **Bollinger Breakout** - Bollinger Band breakout

Each strategy is tested in two forms:
- Standard Freqtrade implementation (baseline)
- Freqtrade implementation with Remora integration (enhanced)

### Market Periods

| Period | Regime | Reason |
|--------|--------|---------|
| 2020–2021 | Bull | Tests over trend markets |
| 2022 | Bear | Measures drawdown protection (critical for Freqtrade users) |
| 2023–2024 | Sideways/choppy | Hardest environment for algos |
| 2024–2025 | Mixed | Realistic recent conditions |
| 2020–2025 | Full period | Maximum statistical power (6 years) |

## 3. Historical Data Reconstruction

Remora uses many real-time signals (VIX, DXY, sentiment, liquidations, etc.) which are not natively available historically. To allow reproducible backtests with Freqtrade, we reconstruct historical Remora data using historical versions of each input.

### Data Sources

| Signal | Source | Availability | Method |
|--------|--------|--------------|--------|
| VIX | Yahoo Finance | Full | yfinance |
| DXY | Yahoo Finance | Full | yfinance |
| BTC dominance | CoinGecko | Full | Public API |
| BTC price | CoinGecko / CCXT | Full | API |
| Funding rate | Binance Futures | Multi-year | Exchange API |
| Open interest | Binance / Coinalyze | Partial | API scrape |
| Liquidations | Coinglass | Partial | API |
| Fear & Greed Index | alternative.me | Full | Historical endpoint |
| CryptoPanic sentiment | No full history | Reconstructed | Proxy signals |
| CryptoCompare news | Limited | Partial | API |

### Reconstruction Process

1. Fetch historical external data for all sources
2. Fetch historical OHLCV data for trading pairs (compatible with Freqtrade)
3. Use existing `RiskCalculator` and `RegimeDetector` classes to compute historical risk scores
4. Output `remora_history.csv` with all required fields

This ensures historical Remora values match current real-time behaviour, allowing accurate Freqtrade backtesting.

## 4. Freqtrade Integration

Remora filtering is added to Freqtrade strategies by modifying the `confirm_trade_entry()` method, which is called by Freqtrade before entering any trade.

### Integration Pattern

```python
def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, **kwargs):
    # REMORA: Check if current market conditions are safe to trade
    current_time = kwargs.get('current_time', datetime.now())
    
    if not remora_allows(timestamp=current_time):
        # Block trade during high-risk periods
        return False
    
    # Your existing Freqtrade strategy logic continues unchanged
    # (populate_entry_trend, populate_exit_trend, etc.)
    return True
```

Where `remora_allows()` checks the historical Remora data:

```python
def remora_allows(timestamp):
    # Look up Remora data for this timestamp
    remora_record = remora_df.loc[timestamp]
    return remora_record["safe_to_trade"]
```

### Key Points

- **No modifications to exit logic** - Remora only filters entries, exits remain strategy-dependent
- **Fail-open behaviour** - If Remora data is unavailable, trades proceed normally
- **Transparent** - Remora returns reasoning (risk_score, regime) not just boolean
- **Easy to remove** - Just delete the Remora check lines

See the [Remora website](https://remora-ai.com) and [blog post](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/) for detailed, color-coded integration examples.

## 5. Backtest Execution

For each Freqtrade strategy and each market period:

1. Run baseline backtest using Freqtrade:
   ```bash
   freqtrade backtesting --strategy BASELINE_STRAT --timerange {period}
   ```

2. Run Remora-enhanced backtest using Freqtrade:
   ```bash
   freqtrade backtesting --strategy REMORA_STRAT --timerange {period}
   ```

All settings are identical between tests:
- Same pairlist (BTC/USDT)
- Same timeframe (5m)
- Same stake amount
- Same Freqtrade configuration

The master script `run_backtests.sh` executes all combinations automatically using Freqtrade's backtesting engine.

## 6. Metrics Collected

### Trading Metrics (Freqtrade Standard)

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
- Max-loss trades avoided

## 7. Visual Reports

The following plots are automatically generated:

1. Equity curve: Baseline vs Remora (Freqtrade strategies)
2. Drawdown curves comparison
3. Trade scatter: Profit vs Risk Score
4. Histogram: Win/Loss distribution before vs after
5. Trade count reduction bar chart
6. Sharpe and Sortino comparison
7. Monthly returns bar chart
8. Regime heatmap (PnL by market regime)

## 8. Reproducibility

Everything required to reproduce the tests is included:

- Historical Remora dataset (or code to rebuild it)
- All Freqtrade strategies used (baseline and Remora-enhanced)
- All commands for Freqtrade backtesting
- Scripts to run backtests
- Scripts to generate charts
- Full methodology (this document)

Anyone can run `./run_backtests.sh` to recreate the complete study using Freqtrade.

## 9. Limitations

- Some sentiment sources do not offer full historical coverage (mitigated by proxy signals)
- Corruption or gaps in exchange historical data may slightly alter results
- Freqtrade strategies with extremely low trade frequency may show high variance
- Remora currently filters entries only — exits remain Freqtrade strategy-dependent
- Results are specific to Freqtrade backtesting engine (though methodology applies broadly)

These limitations are documented to ensure transparency.

## 10. Validation

Results are validated by:
- Cross-checking metrics
- Verifying calculations
- Ensuring statistical significance
- Documenting any anomalies
- Using Freqtrade's native backtesting engine for accuracy

## 11. Results Summary

**See the detailed analysis:** [Advanced Risk Management for Freqtrade](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/)

**Key Findings (6 years, 4 Freqtrade strategies, 20 tests):**
- **+1.54%** profit improvement
- **+1.55%** drawdown reduction
- **4.3%** of trades filtered (high-risk periods avoided)
- Improved risk-adjusted returns across all market regimes

All results are Freqtrade-specific and validated using real Freqtrade strategies.

## Conclusion

This methodology offers a fully transparent, repeatable, and technically rigorous evaluation of Remora's impact on Freqtrade strategies. Freqtrade users may reproduce all tests independently to validate claims about reduced drawdowns, improved stability, improved risk-adjusted returns, smarter exposure control, and strategy-agnostic performance enhancement.

The results demonstrate that Remora provides meaningful value to Freqtrade users by blocking trades during high-risk market conditions, leading to improved risk-adjusted performance across multiple strategies and market regimes.

---

**Resources:**
- [Remora Website](https://remora-ai.com)
- [Blog Post (Detailed Analysis)](https://www.donaldsimpson.co.uk/2025/12/22/advanced-risk-management-for-freqtrade-strategies/)
- [Freqtrade Documentation](https://www.freqtrade.io)
- [Freqtrade Integration Examples](https://github.com/DonaldSimpson/remora-freqtrade)
