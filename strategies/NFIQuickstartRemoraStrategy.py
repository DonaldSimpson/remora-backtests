"""
NFIQuickstart Remora Strategy - NFIQuickstart with Remora Filtering

This is the Remora-enhanced version of NFIQuickstartStrategy.
"""

from NFIQuickstartStrategy import NFIQuickstartStrategy
import pandas as pd
from pandas import DataFrame
from datetime import datetime
from typing import Optional
import os
import logging

logger = logging.getLogger(__name__)

REMORA_HISTORY_PATH = '/home/ubuntu/workspaces/remora/remora_service/backtesting/historical_remora/remora_history.csv'


class NFIQuickstartRemoraStrategy(NFIQuickstartStrategy):
    """Remora-enhanced version of NFIQuickstartStrategy."""
    
    def __init__(self, config: dict):
        """Initialize strategy with Remora data."""
        super().__init__(config)
        self.remora_df = None
        self._load_remora_history()
    
    def _load_remora_history(self):
        """Load historical Remora data from CSV."""
        if not os.path.exists(REMORA_HISTORY_PATH):
            logger.warning(f"Remora history file not found: {REMORA_HISTORY_PATH}")
            return
        
        try:
            self.remora_df = pd.read_csv(REMORA_HISTORY_PATH)
            if 'timestamp' in self.remora_df.columns:
                self.remora_df['timestamp'] = pd.to_datetime(self.remora_df['timestamp'])
                self.remora_df = self.remora_df.set_index('timestamp')
            logger.info(f"Loaded {len(self.remora_df)} Remora history records")
        except Exception as e:
            logger.error(f"Error loading Remora history: {e}")
            self.remora_df = None
    
    def populate_indicators(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Add Remora filtering column to dataframe."""
        dataframe = super().populate_indicators(dataframe, metadata)
        
        # Add Remora safe_to_trade column by matching timestamps
        if self.remora_df is not None and not self.remora_df.empty:
            dataframe['remora_safe'] = True  # Default to safe
            
            # Ensure dataframe index is DatetimeIndex (Freqtrade should provide this)
            if not isinstance(dataframe.index, pd.DatetimeIndex):
                # If not DatetimeIndex, skip Remora filtering (fail-open)
                logger.warning("Dataframe index is not DatetimeIndex, skipping Remora filtering")
                dataframe['remora_safe'] = True
                return dataframe
            
            # Ensure both indices are timezone-naive
            if hasattr(dataframe.index, 'tz') and dataframe.index.tz is not None:
                dataframe.index = dataframe.index.tz_localize(None)
            if hasattr(self.remora_df.index, 'tz') and self.remora_df.index.tz is not None:
                self.remora_df.index = self.remora_df.index.tz_localize(None)
            
            # Match timestamps - reindex entire dataframe index for efficiency
            # This ensures ALL timestamps are matched, not just exact matches
            try:
                # Reindex the safe_to_trade series to match ALL dataframe timestamps
                remora_safe_series = self.remora_df['safe_to_trade'].reindex(
                    dataframe.index,
                    method='nearest',
                    tolerance=pd.Timedelta(minutes=10),
                    fill_value=True  # Default to safe if no match within tolerance
                )
                # Set remora_safe for all rows based on reindexed values
                dataframe['remora_safe'] = remora_safe_series.astype(bool)
                
                # Log statistics
                unsafe_count = (dataframe['remora_safe'] == False).sum()
                safe_count = (dataframe['remora_safe'] == True).sum()
                logger.info(f"Remora filtering: {unsafe_count} unsafe, {safe_count} safe timestamps")
                
            except Exception as e:
                # Fallback if reindex fails
                logger.warning(f"reindex failed, using iteration fallback: {e}")
                # Fallback: iterate through all timestamps
                for idx in dataframe.index:
                    try:
                        if idx in self.remora_df.index:
                            # Exact match
                            dataframe.loc[idx, 'remora_safe'] = bool(self.remora_df.loc[idx, 'safe_to_trade'])
                        else:
                            # Find closest
                            time_diff = abs(self.remora_df.index - idx)
                            closest_idx = time_diff.idxmin()
                            closest_time = self.remora_df.index[time_diff.argmin()]
                            if abs((closest_time - idx).total_seconds()) <= 600:
                                dataframe.loc[idx, 'remora_safe'] = bool(self.remora_df.loc[closest_idx, 'safe_to_trade'])
                            else:
                                dataframe.loc[idx, 'remora_safe'] = True
                    except Exception as e2:
                        logger.debug(f"Error matching {idx}: {e2}")
                        dataframe.loc[idx, 'remora_safe'] = True
        else:
            dataframe['remora_safe'] = True  # Fail-open
        
        return dataframe
    
    def populate_entry_trend(self, dataframe: DataFrame, metadata: dict) -> DataFrame:
        """Populate entry signals with Remora filtering."""
        # Get base entry signals
        dataframe = super().populate_entry_trend(dataframe, metadata)
        
        # Apply Remora filter - only enter when Remora says it's safe
        if 'remora_safe' in dataframe.columns:
            dataframe.loc[dataframe['remora_safe'] == False, 'enter_long'] = 0
        
        return dataframe
