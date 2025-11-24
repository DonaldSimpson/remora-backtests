"""
Remora Strategy Wrapper

Wraps any Freqtrade strategy to add Remora risk filtering.
Loads historical Remora data and blocks entries when safe_to_trade is False.
"""

import logging
import pandas as pd
from datetime import datetime
from typing import Optional
import os

logger = logging.getLogger(__name__)


class RemoraStrategyWrapper:
    """
    Wrapper class to add Remora filtering to any strategy.
    
    This class can be used to wrap existing strategies and add
    Remora risk filtering via confirm_trade_entry().
    """
    
    def __init__(self, base_strategy, remora_history_path: str):
        """
        Initialize wrapper.
        
        Args:
            base_strategy: Base strategy class to wrap
            remora_history_path: Path to remora_history.csv file
        """
        self.base_strategy = base_strategy
        self.remora_history_path = remora_history_path
        self.remora_df = None
        self._load_remora_history()
    
    def _load_remora_history(self):
        """Load historical Remora data from CSV."""
        if not os.path.exists(self.remora_history_path):
            logger.warning(f"Remora history file not found: {self.remora_history_path}")
            logger.warning("Trades will not be filtered by Remora")
            return
        
        try:
            self.remora_df = pd.read_csv(self.remora_history_path)
            if 'timestamp' in self.remora_df.columns:
                self.remora_df['timestamp'] = pd.to_datetime(self.remora_df['timestamp'])
                self.remora_df = self.remora_df.set_index('timestamp')
            
            logger.info(f"Loaded {len(self.remora_df)} Remora history records")
        except Exception as e:
            logger.error(f"Error loading Remora history: {e}")
            self.remora_df = None
    
    def confirm_trade_entry(
        self,
        pair: str,
        order_type: str,
        amount: float,
        rate: float,
        time_in_force: str,
        current_time: Optional[datetime] = None,
        entry_tag: Optional[str] = None,
        side: str = 'long',
        **kwargs
    ) -> bool:
        """
        Confirm trade entry using Remora risk data.
        
        This method is called by Freqtrade before entering a trade.
        Returns False if Remora indicates it's not safe to trade.
        
        Args:
            pair: Trading pair
            order_type: Order type
            amount: Trade amount
            rate: Entry rate
            time_in_force: Time in force
            current_time: Current timestamp (defaults to now)
            entry_tag: Entry tag
            side: Trade side ('long' or 'short')
            **kwargs: Additional arguments
            
        Returns:
            True if safe to trade, False otherwise
        """
        if self.remora_df is None or self.remora_df.empty:
            # If no Remora data, allow trade (fail-open behavior)
            logger.debug("No Remora data available, allowing trade")
            return True
        
        if current_time is None:
            current_time = datetime.now()
        
        try:
            # Find closest timestamp in Remora data
            time_diff = abs(self.remora_df.index - current_time)
            closest_idx = time_diff.idxmin()
            closest_time = self.remora_df.index[closest_idx]
            
            # Only use if within 1 hour (for 5m data)
            if abs((closest_time - current_time).total_seconds()) > 3600:
                logger.debug(f"No Remora data within 1 hour of {current_time}, allowing trade")
                return True
            
            # Get safe_to_trade value
            safe_to_trade = self.remora_df.loc[closest_idx, 'safe_to_trade']
            
            if pd.isna(safe_to_trade):
                logger.debug(f"safe_to_trade is NaN for {current_time}, allowing trade")
                return True
            
            # Convert to boolean if needed
            if isinstance(safe_to_trade, (int, float)):
                safe_to_trade = bool(safe_to_trade)
            
            if not safe_to_trade:
                risk_score = self.remora_df.loc[closest_idx, 'risk_score']
                regime = self.remora_df.loc[closest_idx, 'regime']
                logger.info(
                    f"Remora blocked trade entry for {pair} at {current_time}: "
                    f"risk_score={risk_score:.2f}, regime={regime}"
                )
            
            return bool(safe_to_trade)
            
        except Exception as e:
            logger.warning(f"Error checking Remora data: {e}, allowing trade")
            return True  # Fail-open behavior


def create_remora_strategy(base_strategy_class, remora_history_path: str):
    """
    Create a Remora-enhanced strategy class from a base strategy.
    
    This function creates a new strategy class that inherits from the base
    strategy and adds Remora filtering.
    
    Args:
        base_strategy_class: Base strategy class
        remora_history_path: Path to remora_history.csv
        
    Returns:
        New strategy class with Remora filtering
    """
    class RemoraEnhancedStrategy(base_strategy_class):
        """Remora-enhanced version of the base strategy."""
        
        def __init__(self, config: dict):
            """Initialize strategy with Remora wrapper."""
            super().__init__(config)
            self.remora_wrapper = RemoraStrategyWrapper(self, remora_history_path)
        
        def confirm_trade_entry(
            self,
            pair: str,
            order_type: str,
            amount: float,
            rate: float,
            time_in_force: str,
            current_time: Optional[datetime] = None,
            entry_tag: Optional[str] = None,
            side: str = 'long',
            **kwargs
        ) -> bool:
            """
            Confirm trade entry with Remora filtering.
            
            First checks base strategy, then applies Remora filter.
            """
            # Check base strategy first (if it has confirm_trade_entry)
            if hasattr(super(), 'confirm_trade_entry'):
                base_result = super().confirm_trade_entry(
                    pair, order_type, amount, rate, time_in_force,
                    current_time, entry_tag, side, **kwargs
                )
                if not base_result:
                    return False
            
            # Apply Remora filter
            return self.remora_wrapper.confirm_trade_entry(
                pair, order_type, amount, rate, time_in_force,
                current_time, entry_tag, side, **kwargs
            )
    
    # Set class name to match Freqtrade's expected pattern: BaseStrategyNameRemoraStrategy
    # e.g., NFIQuickstartStrategy -> NFIQuickstartRemoraStrategy
    base_name = base_strategy_class.__name__
    if base_name.endswith('Strategy'):
        new_name = base_name.replace('Strategy', 'RemoraStrategy')
    else:
        new_name = f"{base_name}RemoraStrategy"
    
    RemoraEnhancedStrategy.__name__ = new_name
    RemoraEnhancedStrategy.__qualname__ = new_name
    
    # Set module to the calling module (not RemoraStrategyWrapper)
    # This is important for Freqtrade's strategy discovery
    import inspect
    frame = inspect.currentframe().f_back
    if frame:
        calling_module = frame.f_globals.get('__name__', '')
        if calling_module:
            RemoraEnhancedStrategy.__module__ = calling_module
    
    return RemoraEnhancedStrategy

