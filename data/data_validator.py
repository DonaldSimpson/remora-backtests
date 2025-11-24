"""Validate OHLCV data completeness and quality."""

import logging
import pandas as pd
from datetime import datetime, timedelta
from typing import Dict, List, Tuple

logger = logging.getLogger(__name__)


class DataValidator:
    """Validate OHLCV data for backtesting."""
    
    def __init__(self):
        """Initialize data validator."""
        pass
    
    def validate_ohlcv_data(
        self,
        df: pd.DataFrame,
        expected_start: datetime,
        expected_end: datetime,
        timeframe: str = '5m'
    ) -> Dict:
        """
        Validate OHLCV data completeness and quality.
        
        Args:
            df: OHLCV DataFrame
            expected_start: Expected start date
            expected_end: Expected end date
            timeframe: Expected timeframe
            
        Returns:
            Dictionary with validation results
        """
        logger.info(f"Validating OHLCV data from {expected_start.date()} to {expected_end.date()}")
        
        results = {
            'valid': True,
            'issues': [],
            'warnings': [],
            'stats': {}
        }
        
        if df.empty:
            results['valid'] = False
            results['issues'].append("DataFrame is empty")
            return results
        
        # Check required columns
        required_columns = ['open', 'high', 'low', 'close', 'volume']
        missing_columns = [col for col in required_columns if col not in df.columns]
        if missing_columns:
            results['valid'] = False
            results['issues'].append(f"Missing columns: {missing_columns}")
        
        # Check date range
        if isinstance(df.index, pd.DatetimeIndex):
            actual_start = df.index.min()
            actual_end = df.index.max()
        elif 'timestamp' in df.columns:
            df['timestamp'] = pd.to_datetime(df['timestamp'])
            actual_start = df['timestamp'].min()
            actual_end = df['timestamp'].max()
        else:
            results['valid'] = False
            results['issues'].append("No timestamp index or column found")
            return results
        
        # Check coverage
        expected_days = (expected_end - expected_start).days
        actual_days = (actual_end - actual_start).days
        coverage = (actual_days / expected_days * 100) if expected_days > 0 else 0
        
        results['stats']['coverage'] = coverage
        results['stats']['expected_days'] = expected_days
        results['stats']['actual_days'] = actual_days
        results['stats']['actual_start'] = actual_start.isoformat()
        results['stats']['actual_end'] = actual_end.isoformat()
        
        if coverage < 80:
            results['warnings'].append(f"Low coverage: {coverage:.1f}%")
        
        # Check for gaps
        gaps = self._find_gaps(df, timeframe)
        if gaps:
            results['warnings'].append(f"Found {len(gaps)} gaps in data")
            results['stats']['gaps'] = len(gaps)
            results['stats']['gap_details'] = gaps[:10]  # First 10 gaps
        
        # Check data quality
        quality_issues = self._check_data_quality(df)
        if quality_issues:
            results['warnings'].extend(quality_issues)
        
        # Calculate statistics
        results['stats']['total_records'] = len(df)
        results['stats']['missing_values'] = df.isnull().sum().to_dict()
        results['stats']['duplicate_timestamps'] = df.index.duplicated().sum() if isinstance(df.index, pd.DatetimeIndex) else 0
        
        logger.info(f"Validation complete: {'✓' if results['valid'] else '✗'}")
        return results
    
    def _find_gaps(
        self,
        df: pd.DataFrame,
        timeframe: str
    ) -> List[Dict]:
        """Find gaps in time series data."""
        if df.empty or not isinstance(df.index, pd.DatetimeIndex):
            return []
        
        # Calculate expected interval
        interval_minutes = self._timeframe_to_minutes(timeframe)
        expected_interval = timedelta(minutes=interval_minutes)
        
        gaps = []
        sorted_index = df.index.sort_values()
        
        for i in range(len(sorted_index) - 1):
            current_time = sorted_index[i]
            next_time = sorted_index[i + 1]
            actual_interval = next_time - current_time
            
            # If gap is more than 2x expected interval, it's a gap
            if actual_interval > expected_interval * 2:
                gaps.append({
                    'start': current_time.isoformat(),
                    'end': next_time.isoformat(),
                    'duration_minutes': actual_interval.total_seconds() / 60,
                    'expected_minutes': interval_minutes
                })
        
        return gaps
    
    def _check_data_quality(self, df: pd.DataFrame) -> List[str]:
        """Check data quality issues."""
        issues = []
        
        # Check for negative values
        numeric_cols = ['open', 'high', 'low', 'close', 'volume']
        for col in numeric_cols:
            if col in df.columns:
                negative_count = (df[col] < 0).sum()
                if negative_count > 0:
                    issues.append(f"{col}: {negative_count} negative values")
        
        # Check high/low consistency
        if 'high' in df.columns and 'low' in df.columns:
            invalid_count = (df['high'] < df['low']).sum()
            if invalid_count > 0:
                issues.append(f"high < low: {invalid_count} invalid rows")
        
        # Check for zero volume
        if 'volume' in df.columns:
            zero_volume = (df['volume'] == 0).sum()
            if zero_volume > 0:
                issues.append(f"volume: {zero_volume} zero volume candles")
        
        # Check for extreme price changes (potential data errors)
        if 'close' in df.columns:
            pct_change = df['close'].pct_change()
            extreme_changes = ((pct_change.abs() > 0.5) & (pct_change.abs() < 0.99)).sum()
            if extreme_changes > 0:
                issues.append(f"close: {extreme_changes} extreme price changes (>50%)")
        
        return issues
    
    def _timeframe_to_minutes(self, timeframe: str) -> int:
        """Convert timeframe string to minutes."""
        tf_map = {
            '1m': 1,
            '5m': 5,
            '15m': 15,
            '30m': 30,
            '1h': 60,
            '4h': 240,
            '1d': 1440
        }
        return tf_map.get(timeframe, 60)
    
    def validate_multiple_datasets(
        self,
        datasets: Dict[str, pd.DataFrame],
        expected_start: datetime,
        expected_end: datetime,
        timeframe: str = '5m'
    ) -> Dict[str, Dict]:
        """
        Validate multiple OHLCV datasets.
        
        Args:
            datasets: Dictionary mapping symbol to DataFrame
            expected_start: Expected start date
            expected_end: Expected end date
            timeframe: Expected timeframe
            
        Returns:
            Dictionary mapping symbol to validation results
        """
        logger.info(f"Validating {len(datasets)} datasets")
        
        results = {}
        for symbol, df in datasets.items():
            logger.info(f"Validating {symbol}...")
            results[symbol] = self.validate_ohlcv_data(
                df,
                expected_start,
                expected_end,
                timeframe
            )
        
        return results

