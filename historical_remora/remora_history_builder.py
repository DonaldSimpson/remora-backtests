"""Build historical Remora risk data from OHLCV and external data."""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, Optional
import sys
import os

# Add parent directory to path to import remora_service modules
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

from app.engine.risk_calculator import RiskCalculator

logger = logging.getLogger(__name__)


class RemoraHistoryBuilder:
    """Build historical Remora risk scores from OHLCV and external data."""
    
    def __init__(self):
        """Initialize history builder."""
        self.risk_calculator = RiskCalculator()
    
    def build_historical_remora(
        self,
        ohlcv_df: pd.DataFrame,
        external_df: pd.DataFrame,
        pair: str = "BTC/USD"
    ) -> pd.DataFrame:
        """
        Build historical Remora risk data.
        
        Args:
            ohlcv_df: DataFrame with OHLCV data (columns: timestamp, open, high, low, close, volume)
            external_df: DataFrame with external data (vix, dxy, fear_greed, etc.)
            pair: Trading pair name
            
        Returns:
            DataFrame with historical Remora data including risk_score, safe_to_trade, etc.
        """
        logger.info(f"Building historical Remora data for {pair}")
        logger.info(f"OHLCV data: {len(ohlcv_df)} records")
        logger.info(f"External data: {len(external_df)} records")
        
        # Ensure timestamps are datetime
        if 'timestamp' in ohlcv_df.columns:
            ohlcv_df['timestamp'] = pd.to_datetime(ohlcv_df['timestamp'])
            ohlcv_df = ohlcv_df.set_index('timestamp')
        
        if 'timestamp' in external_df.columns:
            external_df['timestamp'] = pd.to_datetime(external_df['timestamp'])
            external_df = external_df.set_index('timestamp')
        
        # Resample OHLCV to 5-minute intervals if needed
        if len(ohlcv_df) > 0:
            # Check current frequency
            sample_diff = (ohlcv_df.index[1] - ohlcv_df.index[0]).total_seconds() / 60
            if sample_diff > 5:
                # Resample to 5-minute
                ohlcv_df = ohlcv_df.resample('5T').agg({
                    'open': 'first',
                    'high': 'max',
                    'low': 'min',
                    'close': 'last',
                    'volume': 'sum'
                }).dropna()
        
        # Create result DataFrame
        results = []
        
        # Process in chunks to avoid memory issues
        chunk_size = 1000
        total_chunks = (len(ohlcv_df) // chunk_size) + 1
        
        for chunk_idx in range(total_chunks):
            start_idx = chunk_idx * chunk_size
            end_idx = min((chunk_idx + 1) * chunk_size, len(ohlcv_df))
            
            if start_idx >= len(ohlcv_df):
                break
            
            chunk_df = ohlcv_df.iloc[start_idx:end_idx].copy()
            
            logger.info(f"Processing chunk {chunk_idx + 1}/{total_chunks} ({len(chunk_df)} records)")
            
            for idx_in_chunk, (timestamp, row) in enumerate(chunk_df.iterrows()):
                try:
                    # Get external data for this timestamp
                    external_data = self._get_external_data_for_timestamp(
                        timestamp,
                        external_df
                    )
                    
                    # Calculate absolute index in full dataframe
                    absolute_idx = start_idx + idx_in_chunk
                    
                    # Prepare OHLCV data for risk calculation
                    # Need at least 50 candles for indicators
                    # Use last 200 candles for context (or all available if less than 200)
                    lookback_start = max(0, absolute_idx - 200)
                    lookback_end = absolute_idx + 1
                    available_df = ohlcv_df.iloc[lookback_start:lookback_end]
                    
                    if len(available_df) < 50:
                        # Not enough data, skip
                        continue
                    
                    # Calculate risk
                    risk_result = self.risk_calculator.calculate_risk(
                        dataframe_5m=available_df,
                        dataframe_1h=None,  # Could be added if available
                        dataframe_1d=None,  # Could be added if available
                        external_metrics=external_data
                    )
                    
                    # Add timestamp and pair
                    result_row = {
                        'timestamp': timestamp,
                        'pair': pair,
                        **risk_result
                    }
                    
                    results.append(result_row)
                    
                except Exception as e:
                    logger.warning(f"Error processing {timestamp}: {e}")
                    continue
            
            # Progress update
            if (chunk_idx + 1) % 10 == 0:
                logger.info(f"Processed {chunk_idx + 1}/{total_chunks} chunks")
        
        if not results:
            logger.warning("No results generated")
            return pd.DataFrame()
        
        result_df = pd.DataFrame(results)
        result_df = result_df.set_index('timestamp')
        
        logger.info(f"Generated {len(result_df)} historical Remora records")
        return result_df
    
    def _get_external_data_for_timestamp(
        self,
        timestamp: pd.Timestamp,
        external_df: pd.DataFrame
    ) -> Optional[Dict]:
        """
        Get external data for a specific timestamp.
        
        Args:
            timestamp: Target timestamp
            external_df: DataFrame with external data
            
        Returns:
            Dictionary with external metrics or None
        """
        if external_df.empty:
            return None
        
        # Find closest timestamp in external data (within 1 day)
        # Convert to Series to use idxmin() (TimedeltaIndex doesn't have idxmin)
        time_diff = pd.Series(abs(external_df.index - timestamp), index=external_df.index)
        closest_idx = time_diff.idxmin()
        closest_time = closest_idx  # idxmin() already returns the index value
        
        # Only use if within 1 day
        if abs((closest_time - timestamp).total_seconds()) > 86400:
            return None
        
        row = external_df.loc[closest_idx]
        
        # Build external metrics dictionary
        external_metrics = {}
        
        if 'fear_greed' in row and pd.notna(row['fear_greed']):
            external_metrics['fear_greed_index'] = float(row['fear_greed'])
        
        if 'vix' in row and pd.notna(row['vix']):
            external_metrics['vix'] = float(row['vix'])
        
        if 'dxy' in row and pd.notna(row['dxy']):
            external_metrics['dxy'] = float(row['dxy'])
        
        if 'btc_dominance' in row and pd.notna(row['btc_dominance']):
            external_metrics['btc_dominance'] = float(row['btc_dominance'])
        
        if 'funding_rate' in row and pd.notna(row['funding_rate']):
            external_metrics['funding_rate'] = float(row['funding_rate'])
        
        return external_metrics if external_metrics else None
    
    def save_to_csv(self, remora_df: pd.DataFrame, output_path: str):
        """
        Save Remora history to CSV.
        
        Args:
            remora_df: DataFrame with Remora history
            output_path: Path to save CSV file
        """
        logger.info(f"Saving Remora history to {output_path}")
        
        # Reset index to include timestamp as column
        output_df = remora_df.reset_index()
        
        # Flatten nested dictionaries in columns
        for col in output_df.columns:
            if isinstance(output_df[col].iloc[0], dict):
                # Expand dictionary columns
                expanded = pd.json_normalize(output_df[col])
                expanded.columns = [f"{col}.{subcol}" for subcol in expanded.columns]
                output_df = pd.concat([output_df.drop(columns=[col]), expanded], axis=1)
        
        output_df.to_csv(output_path, index=False)
        logger.info(f"Saved {len(output_df)} records to {output_path}")

