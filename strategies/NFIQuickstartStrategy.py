"""
NFI Quickstart Strategy - Simple Moving Average Crossover

A basic strategy that uses two moving averages to generate buy/sell signals.
Entry: When fast MA crosses above slow MA
Exit: When fast MA crosses below slow MA or profit target reached
"""

# pragma pylint: disable=missing-docstring, invalid-name, pointless-string-statement
# flake8: noqa: F401
# isort: skip_file

import numpy as np
import pandas as pd
from pandas import DataFrame
from typing import Optional
import talib.abstract as ta
from freqtrade.strategy import IStrategy


class NFIQuickstartStrategy(IStrategy):
    """
    NFI Quickstart Strategy - Simple MA Crossover
    
    This is a basic strategy for backtesting purposes.
    """
    
    INTERFACE_VERSION = 3
    timeframe = '5m'
    can_short: bool = False
    
    # ROI table
    minimal_roi = {
        "0": 0.10,   # 10% profit target
        "60": 0.05,  # 5% after 60 minutes
        "120": 0.02  # 2% after 120 minutes
    }
    
    stoploss = -0.10  # 10% stop loss
    trailing_stop = False
    
    process_only_new_candles = False
    use_exit_signal = True
    exit_profit_only = False
    ignore_roi_if_entry_signal = False
    startup_candle_count: int = 200
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Add indicators to the dataframe.
        
        Args:
            dataframe: DataFrame with OHLCV data
            metadata: Pair metadata
            
        Returns:
            DataFrame with indicators added
        """
        # Fast moving average (20 periods)
        dataframe['sma_fast'] = ta.SMA(dataframe, timeperiod=20)
        
        # Slow moving average (50 periods)
        dataframe['sma_slow'] = ta.SMA(dataframe, timeperiod=50)
        
        # RSI for additional confirmation
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals.
        
        Entry when:
        - Fast MA crosses above slow MA
        - RSI is not overbought (< 70)
        """
        dataframe.loc[
            (
                (dataframe['sma_fast'] > dataframe['sma_slow']) &
                (dataframe['sma_fast'].shift(1) <= dataframe['sma_slow'].shift(1)) &
                (dataframe['rsi'] < 70) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate exit signals.
        
        Exit when:
        - Fast MA crosses below slow MA
        - RSI is overbought (> 80)
        """
        dataframe.loc[
            (
                (dataframe['sma_fast'] < dataframe['sma_slow']) &
                (dataframe['sma_fast'].shift(1) >= dataframe['sma_slow'].shift(1))
            ) |
            (dataframe['rsi'] > 80),
            'exit_long'
        ] = 1
        
        return dataframe

