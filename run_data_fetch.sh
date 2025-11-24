#!/bin/bash
# Script to fetch all data for backtesting

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "============================================================"
echo "Remora Backtesting - Data Fetching"
echo "============================================================"
echo ""
echo "This will fetch:"
echo "  - OHLCV data: 2020-2025 (6 years)"
echo "  - External market data (VIX, DXY, Fear & Greed, etc.)"
echo "  - Build Remora history"
echo ""
echo "Estimated time: 4-9 hours"
echo ""

# Activate virtual environment if it exists
if [ -d "../../venv" ]; then
    echo "Activating virtual environment..."
    source ../../venv/bin/activate
fi

# Check dependencies
echo "Checking dependencies..."
python3 -c "import pandas, numpy, requests, yfinance, ccxt" 2>/dev/null || {
    echo "⚠ Some dependencies missing. Installing..."
    pip install -q pandas numpy requests yfinance ccxt
}

# Run data fetch
echo ""
echo "Starting data fetch..."
echo "This will take several hours. You can monitor progress in the logs."
echo ""

python3 fetch_all_data.py

echo ""
echo "============================================================"
echo "Data fetching complete!"
echo "============================================================"
echo ""
echo "Next step: Run backtests with ./run_backtests.sh"

