"""
MACD Cross Strategy

A strategy based on MACD (Moving Average Convergence Divergence) indicator.
Entry: When MACD line crosses above signal line
Exit: When MACD line crosses below signal line or profit target reached
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


class MACDCrossStrategy(IStrategy):
    """
    MACD Cross Strategy
    
    Uses MACD indicator for entry/exit signals.
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
        # MACD
        macd = ta.MACD(dataframe)
        dataframe['macd'] = macd['macd']
        dataframe['macdsignal'] = macd['macdsignal']
        dataframe['macdhist'] = macd['macdhist']
        
        # RSI for confirmation
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Volume SMA for volume confirmation
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals.
        
        Entry when:
        - MACD crosses above signal line
        - MACD histogram is positive
        - RSI is not overbought (< 70)
        """
        dataframe.loc[
            (
                (dataframe['macd'] > dataframe['macdsignal']) &
                (dataframe['macd'].shift(1) <= dataframe['macdsignal'].shift(1)) &
                (dataframe['macdhist'] > 0) &
                (dataframe['rsi'] < 70) &
                (dataframe['volume'] > dataframe['volume_sma'] * 0.8)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate exit signals.
        
        Exit when:
        - MACD crosses below signal line
        - MACD histogram turns negative
        """
        dataframe.loc[
            (
                (dataframe['macd'] < dataframe['macdsignal']) &
                (dataframe['macd'].shift(1) >= dataframe['macdsignal'].shift(1))
            ) |
            (
                (dataframe['macdhist'] < 0) &
                (dataframe['macdhist'].shift(1) >= 0)
            ),
            'exit_long'
        ] = 1
        
        return dataframe

