# Security & Privacy Notes

## What's Included

✅ **Safe to share:**
- Public market data fetching scripts (OHLCV, VIX, DXY, etc.)
- Generic trading strategies (standard technical analysis)
- Backtest results and analysis
- Documentation

⚠️ **References Remora internals:**
- `build_remora_history.py` - imports from `app.engine.*`
- `historical_remora/remora_history_builder.py` - imports RiskCalculator
- These scripts require access to Remora service to run

## What's NOT Included

❌ **Not exposed:**
- Remora source code (RiskCalculator, RegimeDetector implementations)
- API keys or credentials
- User data
- Proprietary algorithms

## Impact

The repository shows **how** Remora is used, but not **how it works**. Someone would need:
1. Access to the actual Remora service code
2. The ability to run the Remora service locally
3. Historical data to generate remora_history.csv

Without these, they cannot recreate Remora's risk calculations.

## Recommendation

This repository is safe to publish as-is. It demonstrates Remora's effectiveness through backtesting without exposing the core intellectual property.
