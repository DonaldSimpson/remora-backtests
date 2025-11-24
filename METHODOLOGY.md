# Backtesting Methodology for Remora Risk Engine

This document explains exactly how to reproduce the backtests used to validate the Remora Risk Engine. It is designed to be transparent, deterministic, and independently verifiable.

## 1. Purpose

The goals of this study are:

1. To measure whether using the Remora Risk Engine improves trading outcomes
2. To quantify reductions in drawdown, losses, and exposure during high-risk market conditions
3. To demonstrate that these improvements are strategy-agnostic and reproducible
4. To allow any trader to validate the results using this repository

## 2. Test Design

### Comparison Method

The tests compare:
- **Baseline:** Strategy without filters
- **Remora-Enhanced:** Same strategy with Remora blocking entries during high-risk periods

### Strategies Tested

1. **NFI Quickstart** - Simple moving average crossover
2. **MACD Cross** - MACD line crossover strategy
3. **RSI + EMA** - RSI and EMA trend following
4. **Bollinger Breakout** - Bollinger Band breakout

### Market Periods

| Period | Regime | Reason |
|--------|--------|---------|
| 2020–2021 | Bull | Tests over trend markets |
| 2022 | Bear | Measures drawdown protection |
| 2023–2024 | Sideways/choppy | Hardest environment for algos |
| 2024–2025 | Mixed | Realistic recent conditions |

## 3. Historical Data Reconstruction

Remora uses many real-time signals (VIX, DXY, sentiment, liquidations, etc.) which are not natively available historically. To allow reproducible backtests, we reconstruct historical Remora data using historical versions of each input.

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
2. Fetch historical OHLCV data for trading pairs
3. Use existing `RiskCalculator` and `RegimeDetector` classes to compute historical risk scores
4. Output `remora_history.csv` with all required fields

This ensures historical Remora values match current real-time behavior.

## 4. Freqtrade Integration

Remora filtering is added by modifying `confirm_trade_entry()`:

```python
def confirm_trade_entry(self, pair, order_type, amount, rate, time_in_force, **kwargs):
    return remora_allows(timestamp=time)
```

Where `remora_allows()` checks the historical Remora data:

```python
def remora_allows(timestamp):
    return remora_df.loc[timestamp]["safe_to_trade"]
```

No modifications are made to exit logic.

## 5. Backtest Execution

For each strategy and each market period:

1. Run baseline backtest:
   ```bash
   freqtrade backtesting --strategy BASELINE_STRAT --timerange {period}
   ```

2. Run Remora-enhanced backtest:
   ```bash
   freqtrade backtesting --strategy REMORA_STRAT --timerange {period}
   ```

All settings (pairlist, timeframe, stake) are identical between tests.

The master script `run_backtests.sh` executes all combinations automatically.

## 6. Metrics Collected

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
- Max-loss trades avoided

## 7. Visual Reports

The following plots are automatically generated:

1. Equity curve: Baseline vs Remora
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
- All strategies used
- All commands
- Scripts to run backtests
- Scripts to generate charts
- Full methodology (this document)

Anyone can run `./run_backtests.sh` to recreate the complete study.

## 9. Limitations

- Some sentiment sources do not offer full historical coverage (mitigated by proxy signals)
- Corruption or gaps in exchange historical data may slightly alter results
- Strategies with extremely low trade frequency may show high variance
- Remora currently filters entries only — exits remain strategy-dependent

These limitations are documented to ensure transparency.

## 10. Validation

Results are validated by:
- Cross-checking metrics
- Verifying calculations
- Ensuring statistical significance
- Documenting any anomalies

## Conclusion

This methodology offers a fully transparent, repeatable, and technically rigorous evaluation of Remora. Traders may reproduce all tests independently to validate claims about reduced drawdowns, improved stability, improved risk-adjusted returns, smarter exposure control, and strategy-agnostic performance enhancement.

