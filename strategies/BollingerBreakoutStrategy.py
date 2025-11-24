"""
Bollinger Breakout Strategy

A strategy based on Bollinger Bands for breakout trading.
Entry: When price breaks above upper Bollinger Band
Exit: When price returns to middle band or profit target reached
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


class BollingerBreakoutStrategy(IStrategy):
    """
    Bollinger Breakout Strategy
    
    Uses Bollinger Bands to identify breakouts.
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
        # Bollinger Bands
        bollinger = ta.BBANDS(dataframe, timeperiod=20, nbdevup=2.0, nbdevdn=2.0)
        dataframe['bb_upper'] = bollinger['upperband']
        dataframe['bb_middle'] = bollinger['middleband']
        dataframe['bb_lower'] = bollinger['lowerband']
        
        # RSI for confirmation
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # Volume SMA
        dataframe['volume_sma'] = ta.SMA(dataframe['volume'], timeperiod=20)
        
        # Price position within bands
        dataframe['bb_percent'] = (
            (dataframe['close'] - dataframe['bb_lower']) /
            (dataframe['bb_upper'] - dataframe['bb_lower'])
        )
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals.
        
        Entry when:
        - Price breaks above upper Bollinger Band
        - RSI is strong but not overbought (50-75)
        - Volume is above average
        """
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['bb_upper']) &
                (dataframe['close'].shift(1) <= dataframe['bb_upper'].shift(1)) &
                (dataframe['rsi'] > 50) &
                (dataframe['rsi'] < 75) &
                (dataframe['volume'] > dataframe['volume_sma'] * 0.9) &
                (dataframe['bb_percent'] > 1.0)  # Above upper band
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate exit signals.
        
        Exit when:
        - Price returns to middle band
        - RSI becomes overbought (> 80)
        """
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['bb_middle']) &
                (dataframe['close'].shift(1) >= dataframe['bb_middle'].shift(1))
            ) |
            (dataframe['rsi'] > 80),
            'exit_long'
        ] = 1
        
        return dataframe

