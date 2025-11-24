"""
RSI + EMA Strategy

A trend-following strategy using RSI and EMA indicators.
Entry: When price is above EMA and RSI indicates oversold recovery
Exit: When price crosses below EMA or RSI becomes overbought
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


class RSIEMAStrategy(IStrategy):
    """
    RSI + EMA Strategy
    
    Combines RSI momentum indicator with EMA trend filter.
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
        # EMA for trend
        dataframe['ema_fast'] = ta.EMA(dataframe, timeperiod=12)
        dataframe['ema_slow'] = ta.EMA(dataframe, timeperiod=26)
        
        # RSI for momentum
        dataframe['rsi'] = ta.RSI(dataframe, timeperiod=14)
        
        # ATR for volatility
        dataframe['atr'] = ta.ATR(dataframe, timeperiod=14)
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate entry signals.
        
        Entry when:
        - Price is above fast EMA (uptrend)
        - Fast EMA is above slow EMA (trend confirmation)
        - RSI crosses above 50 (momentum turning positive)
        - RSI was below 45 (oversold recovery)
        """
        dataframe.loc[
            (
                (dataframe['close'] > dataframe['ema_fast']) &
                (dataframe['ema_fast'] > dataframe['ema_slow']) &
                (dataframe['rsi'] > 50) &
                (dataframe['rsi'].shift(1) <= 50) &
                (dataframe['rsi'].shift(2) < 45) &
                (dataframe['volume'] > 0)
            ),
            'enter_long'
        ] = 1
        
        return dataframe
    
    def populate_exit_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """
        Populate exit signals.
        
        Exit when:
        - Price crosses below fast EMA
        - RSI becomes overbought (> 75)
        """
        dataframe.loc[
            (
                (dataframe['close'] < dataframe['ema_fast']) &
                (dataframe['close'].shift(1) >= dataframe['ema_fast'].shift(1))
            ) |
            (dataframe['rsi'] > 75),
            'exit_long'
        ] = 1
        
        return dataframe

