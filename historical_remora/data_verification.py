"""Verify and check existing data in ClickHouse for backtesting."""

import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '../../..'))

try:
    from app.data.clickhouse_client import ClickHouseClient
    CLICKHOUSE_AVAILABLE = True
except ImportError:
    CLICKHOUSE_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("ClickHouse client not available")

logger = logging.getLogger(__name__)


class DataVerifier:
    """Verify existing data in ClickHouse and identify gaps."""
    
    def __init__(self):
        """Initialize data verifier."""
        self.clickhouse_client = None
        if CLICKHOUSE_AVAILABLE:
            try:
                self.clickhouse_client = ClickHouseClient()
                if not self.clickhouse_client.enabled:
                    self.clickhouse_client = None
            except Exception as e:
                logger.warning(f"Could not initialize ClickHouse client: {e}")
                self.clickhouse_client = None
    
    def check_historical_risk_data(
        self,
        pair: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Check what historical risk data exists in ClickHouse.
        
        Args:
            pair: Trading pair to check
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with data availability information
        """
        if not self.clickhouse_client:
            return {
                'available': False,
                'reason': 'ClickHouse not available',
                'records': 0,
                'date_range': None,
                'coverage': 0.0
            }
        
        try:
            risk_data = self.clickhouse_client.get_historical_risk(
                pair,
                start_date,
                end_date
            )
            
            if not risk_data:
                return {
                    'available': False,
                    'reason': 'No data found',
                    'records': 0,
                    'date_range': None,
                    'coverage': 0.0
                }
            
            # Analyze data
            timestamps = [r.get('timestamp') for r in risk_data if 'timestamp' in r]
            if timestamps:
                min_date = min(timestamps)
                max_date = max(timestamps)
                total_days = (end_date - start_date).days
                data_days = (max_date - min_date).days if max_date and min_date else 0
                coverage = (data_days / total_days * 100) if total_days > 0 else 0.0
            else:
                min_date = None
                max_date = None
                coverage = 0.0
            
            return {
                'available': True,
                'records': len(risk_data),
                'date_range': {
                    'start': min_date.isoformat() if min_date else None,
                    'end': max_date.isoformat() if max_date else None
                },
                'coverage': coverage,
                'gaps': self._identify_gaps(timestamps, start_date, end_date)
            }
            
        except Exception as e:
            logger.error(f"Error checking historical risk data: {e}")
            return {
                'available': False,
                'reason': str(e),
                'records': 0,
                'date_range': None,
                'coverage': 0.0
            }
    
    def check_external_data(
        self,
        source: str,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Check what external data exists in ClickHouse.
        
        Args:
            source: Data source name (fear_greed, vix_dxy, etc.)
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with data availability information
        """
        if not self.clickhouse_client:
            return {
                'available': False,
                'reason': 'ClickHouse not available',
                'records': 0
            }
        
        try:
            external_data = self.clickhouse_client.get_historical_external_data(
                source,
                start_date,
                end_date
            )
            
            return {
                'available': len(external_data) > 0,
                'records': len(external_data),
                'source': source
            }
            
        except Exception as e:
            logger.error(f"Error checking external data for {source}: {e}")
            return {
                'available': False,
                'reason': str(e),
                'records': 0,
                'source': source
            }
    
    def check_all_data_sources(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> Dict:
        """
        Check all data sources and return comprehensive report.
        
        Args:
            start_date: Start date
            end_date: End date
            
        Returns:
            Dictionary with availability for all sources
        """
        logger.info(f"Checking data availability from {start_date.date()} to {end_date.date()}")
        
        report = {
            'date_range': {
                'start': start_date.isoformat(),
                'end': end_date.isoformat()
            },
            'risk_engine_data': {},
            'external_data': {},
            'recommendations': []
        }
        
        # Check risk engine data for common pairs
        pairs = ['BTC/USD', 'ETH/USD', 'SOL/USD']
        for pair in pairs:
            report['risk_engine_data'][pair] = self.check_historical_risk_data(
                pair,
                start_date,
                end_date
            )
        
        # Check external data sources
        sources = [
            'fear_greed',
            'vix_dxy',
            'sentiment',
            'funding_rates',
            'open_interest',
            'liquidations',
            'cryptopanic',
            'cryptocompare_news'
        ]
        
        for source in sources:
            report['external_data'][source] = self.check_external_data(
                source,
                start_date,
                end_date
            )
        
        # Generate recommendations
        report['recommendations'] = self._generate_recommendations(report)
        
        return report
    
    def _identify_gaps(
        self,
        timestamps: List[datetime],
        start_date: datetime,
        end_date: datetime
    ) -> List[Dict]:
        """Identify gaps in timestamp data."""
        if not timestamps:
            return [{
                'start': start_date.isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - start_date).days
            }]
        
        sorted_timestamps = sorted(timestamps)
        gaps = []
        
        # Check gap at start
        if sorted_timestamps[0] > start_date:
            gaps.append({
                'start': start_date.isoformat(),
                'end': sorted_timestamps[0].isoformat(),
                'days': (sorted_timestamps[0] - start_date).days
            })
        
        # Check gaps between timestamps
        for i in range(len(sorted_timestamps) - 1):
            gap_start = sorted_timestamps[i]
            gap_end = sorted_timestamps[i + 1]
            gap_days = (gap_end - gap_start).days
            
            # Consider gap if more than 1 day
            if gap_days > 1:
                gaps.append({
                    'start': gap_start.isoformat(),
                    'end': gap_end.isoformat(),
                    'days': gap_days
                })
        
        # Check gap at end
        if sorted_timestamps[-1] < end_date:
            gaps.append({
                'start': sorted_timestamps[-1].isoformat(),
                'end': end_date.isoformat(),
                'days': (end_date - sorted_timestamps[-1]).days
            })
        
        return gaps
    
    def _generate_recommendations(self, report: Dict) -> List[str]:
        """Generate recommendations based on data availability."""
        recommendations = []
        
        # Check risk engine data
        risk_data_available = any(
            data.get('available', False)
            for data in report['risk_engine_data'].values()
        )
        
        if not risk_data_available:
            recommendations.append(
                "No historical risk engine data found. Need to generate from OHLCV and external data."
            )
        
        # Check external data
        external_sources_available = sum(
            1 for data in report['external_data'].values()
            if data.get('available', False)
        )
        
        if external_sources_available < len(report['external_data']):
            missing = [
                source for source, data in report['external_data'].items()
                if not data.get('available', False)
            ]
            recommendations.append(
                f"Missing external data sources: {', '.join(missing)}. "
                "These will need to be fetched from APIs."
            )
        
        # Check coverage
        for pair, data in report['risk_engine_data'].items():
            if data.get('available', False):
                coverage = data.get('coverage', 0.0)
                if coverage < 80.0:
                    recommendations.append(
                        f"Low coverage ({coverage:.1f}%) for {pair}. "
                        "Consider fetching missing periods."
                    )
        
        if not recommendations:
            recommendations.append("Data availability looks good!")
        
        return recommendations

