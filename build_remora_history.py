#!/usr/bin/env python3
"""
Build Remora history from OHLCV and external data.

This script computes historical risk scores for all timestamps using
the same RiskCalculator as production Remora.
"""

import sys
import os
from pathlib import Path
import pandas as pd
import numpy as np
from datetime import datetime
import logging

# Add remora_service to path - need to be in remora_service directory
remora_service_path = Path(__file__).parent.parent.parent
if (remora_service_path / 'app').exists():
    # We're in remora_service/backtesting, add parent
    sys.path.insert(0, str(remora_service_path))
else:
    # Try alternative path
    alt_path = Path(__file__).parent.parent
    if (alt_path / 'app').exists():
        sys.path.insert(0, str(alt_path))
    else:
        # Last resort: add current working directory
        sys.path.insert(0, str(Path.cwd()))

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

try:
    from app.engine.risk_calculator import RiskCalculator
    from app.engine.regime_detector import RegimeDetector
    from app.engine.volatility import VolatilityScorer
    REMORA_AVAILABLE = True
except ImportError as e:
    logger.error(f"Could not import Remora modules: {e}")
    logger.error("Make sure you're running from remora_service directory or PYTHONPATH is set")
    REMORA_AVAILABLE = False


def build_remora_history():
    """Build complete Remora history from OHLCV and external data."""
    
    if not REMORA_AVAILABLE:
        logger.error("Remora modules not available. Cannot build history.")
        return False
    
    base_path = Path(__file__).parent
    
    # Load OHLCV data
    ohlcv_path = base_path / 'data' / 'ohlcv' / 'BTC_USDT_5m_20200101_20251231.parquet'
    if not ohlcv_path.exists():
        logger.error(f"OHLCV file not found: {ohlcv_path}")
        return False
    
    logger.info(f"Loading OHLCV data from {ohlcv_path}...")
    ohlcv_df = pd.read_parquet(ohlcv_path)
    
    # Ensure timestamp is index
    if 'timestamp' in ohlcv_df.columns:
        ohlcv_df['timestamp'] = pd.to_datetime(ohlcv_df['timestamp'])
        ohlcv_df = ohlcv_df.set_index('timestamp')
    
    logger.info(f"Loaded {len(ohlcv_df):,} OHLCV records")
    logger.info(f"Date range: {ohlcv_df.index.min()} to {ohlcv_df.index.max()}")
    
    # Load external data
    external_path = base_path / 'historical_remora' / 'external_data.csv'
    if not external_path.exists():
        logger.warning(f"External data file not found: {external_path}")
        external_df = pd.DataFrame()
    else:
        logger.info(f"Loading external data from {external_path}...")
        external_df = pd.read_csv(external_path)
        external_df['timestamp'] = pd.to_datetime(external_df['timestamp'])
        external_df = external_df.set_index('timestamp')
        logger.info(f"Loaded {len(external_df):,} external data records")
    
    # Initialize Remora components
    logger.info("Initializing Remora risk calculator...")
    risk_calculator = RiskCalculator()
    regime_detector = RegimeDetector()
    volatility_scorer = VolatilityScorer()
    
    # Prepare output
    output_data = []
    total_records = len(ohlcv_df)
    batch_size = 1000
    
    logger.info(f"Computing Remora risk scores for {total_records:,} timestamps...")
    logger.info("This will take a while... Progress updates every 1000 records")
    
    # Process in batches for progress tracking
    for i in range(0, total_records, batch_size):
        batch_end = min(i + batch_size, total_records)
        batch_df = ohlcv_df.iloc[i:batch_end].copy()
        
        # For each timestamp in batch
        for timestamp, row in batch_df.iterrows():
            try:
                # Get historical context (lookback window)
                lookback_start = max(0, i - 200)  # 200 periods lookback
                lookback_end = i + 1
                context_df = ohlcv_df.iloc[lookback_start:lookback_end]
                
                # Get external metrics for this timestamp
                external_metrics = {}
                if not external_df.empty:
                    # Find closest external data (daily, so find same day)
                    day_start = timestamp.replace(hour=0, minute=0, second=0, microsecond=0)
                    if day_start in external_df.index:
                        ext_row = external_df.loc[day_start]
                        if pd.notna(ext_row.get('vix')):
                            external_metrics['vix'] = float(ext_row['vix'])
                        if pd.notna(ext_row.get('dxy')):
                            external_metrics['dxy'] = float(ext_row['dxy'])
                        if pd.notna(ext_row.get('fear_greed')):
                            external_metrics['fear_greed_index'] = float(ext_row['fear_greed'])
                        if pd.notna(ext_row.get('funding_rate')):
                            external_metrics['funding_rate'] = float(ext_row['funding_rate'])
                        if pd.notna(ext_row.get('btc_dominance')):
                            external_metrics['btc_dominance'] = float(ext_row['btc_dominance'])
                
                # Calculate risk using Remora
                risk_result = risk_calculator.calculate_risk(
                    dataframe_5m=context_df,
                    external_metrics=external_metrics if external_metrics else None
                )
                
                # Get volatility
                volatility_result = volatility_scorer.calculate_volatility_score(context_df)
                
                # Get regime
                regime_result = regime_detector.detect_regime(context_df)
                
                # Build output record
                output_data.append({
                    'timestamp': timestamp,
                    'pair': 'BTC/USDT',
                    'risk_score': risk_result.get('risk_score', 0.5),
                    'safe_to_trade': risk_result.get('safe_to_trade', True),
                    'regime': regime_result.get('regime', 'unknown'),
                    'volatility': volatility_result.get('volatility_score', 0.5),
                    'volatility_classification': volatility_result.get('classification', 'normal'),
                    'confidence': risk_result.get('confidence', 0.5),
                    'vix': external_metrics.get('vix'),
                    'dxy': external_metrics.get('dxy'),
                    'fear_greed': external_metrics.get('fear_greed_index'),
                    'funding_rate': external_metrics.get('funding_rate'),
                    'btc_dominance': external_metrics.get('btc_dominance')
                })
                
            except Exception as e:
                logger.warning(f"Error processing timestamp {timestamp}: {e}")
                # Add default record on error
                output_data.append({
                    'timestamp': timestamp,
                    'pair': 'BTC/USDT',
                    'risk_score': 0.5,
                    'safe_to_trade': True,
                    'regime': 'unknown',
                    'volatility': 0.5,
                    'volatility_classification': 'normal',
                    'confidence': 0.0
                })
        
        # Progress update
        if (i // batch_size + 1) % 10 == 0:
            pct = (batch_end / total_records * 100)
            logger.info(f"  Progress: {batch_end:,}/{total_records:,} ({pct:.1f}%)")
    
    # Create DataFrame
    remora_df = pd.DataFrame(output_data)
    remora_df = remora_df.set_index('timestamp')
    remora_df = remora_df.sort_index()
    
    # Save to CSV
    output_path = base_path / 'historical_remora' / 'remora_history.csv'
    remora_df.to_csv(output_path)
    
    logger.info(f"\n✅ Remora history built successfully!")
    logger.info(f"   Records: {len(remora_df):,}")
    logger.info(f"   Date range: {remora_df.index.min()} to {remora_df.index.max()}")
    logger.info(f"   Saved to: {output_path}")
    logger.info(f"   File size: {output_path.stat().st_size / 1024 / 1024:.1f} MB")
    
    # Summary statistics
    logger.info(f"\n📊 Summary Statistics:")
    logger.info(f"   Average risk score: {remora_df['risk_score'].mean():.3f}")
    logger.info(f"   Safe to trade: {remora_df['safe_to_trade'].sum():,} ({remora_df['safe_to_trade'].sum()/len(remora_df)*100:.1f}%)")
    logger.info(f"   Regimes: {remora_df['regime'].value_counts().to_dict()}")
    
    return True


def main():
    """Main execution."""
    logger.info("=" * 60)
    logger.info("Building Remora History")
    logger.info("=" * 60)
    logger.info("")
    logger.info("This will compute risk scores for all 619,776 timestamps")
    logger.info("using the same RiskCalculator as production Remora.")
    logger.info("")
    logger.info("Estimated time: 1-3 hours")
    logger.info("")
    
    if not REMORA_AVAILABLE:
        logger.error("Cannot proceed - Remora modules not available")
        logger.info("")
        logger.info("To fix:")
        logger.info("1. Make sure you're in remora_service directory")
        logger.info("2. Or set PYTHONPATH to include remora_service")
        logger.info("3. Or run: cd remora_service && python backtesting/build_remora_history.py")
        return 1
    
    try:
        success = build_remora_history()
        if success:
            logger.info("\n" + "=" * 60)
            logger.info("✅ Remora History Building Complete!")
            logger.info("=" * 60)
            logger.info("")
            logger.info("Next step: Run backtests with ./run_backtests.sh")
            return 0
        else:
            logger.error("\n✗ Failed to build Remora history")
            return 1
            
    except KeyboardInterrupt:
        logger.info("\n\nBuilding cancelled by user")
        return 1
    except Exception as e:
        logger.error(f"\n\nError building Remora history: {e}", exc_info=True)
        return 1


if __name__ == "__main__":
    sys.exit(main())

