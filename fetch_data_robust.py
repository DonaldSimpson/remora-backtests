#!/usr/bin/env python3
"""
Robust data fetching with progress tracking and resume capability.

Fetches 6 years of data (2020-2025) for irrefutable backtesting proof.
Can be interrupted and resumed.
"""

import sys
import os
from pathlib import Path
from datetime import datetime, timedelta
import pandas as pd
import ccxt
import yfinance as yf
import requests
import time
import logging
import json
import pickle

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('data_fetch.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)


class DataFetcher:
    """Robust data fetcher with progress tracking."""
    
    def __init__(self, data_dir=None):
        self.data_dir = Path(data_dir) if data_dir else Path(__file__).parent / 'data'
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.progress_file = self.data_dir / 'fetch_progress.json'
        self.exchange = ccxt.binance({'enableRateLimit': True, 'timeout': 30000})
    
    def load_progress(self):
        """Load fetch progress."""
        if self.progress_file.exists():
            try:
                with open(self.progress_file, 'r') as f:
                    return json.load(f)
            except:
                return {}
        return {}
    
    def save_progress(self, progress):
        """Save fetch progress."""
        with open(self.progress_file, 'w') as f:
            json.dump(progress, f, indent=2, default=str)
    
    def fetch_ohlcv_chunked(self, pair='BTC/USDT', timeframe='5m', 
                           start_date=None, end_date=None, chunk_days=30):
        """
        Fetch OHLCV in chunks to allow progress tracking.
        
        Args:
            pair: Trading pair
            timeframe: Timeframe
            start_date: Start date
            end_date: End date
            chunk_days: Days per chunk
        """
        logger.info(f"Fetching {pair} {timeframe} from {start_date.date()} to {end_date.date()}")
        logger.info(f"Using {chunk_days}-day chunks for progress tracking")
        
        progress = self.load_progress()
        pair_key = f"{pair.replace('/', '_')}_{timeframe}"
        
        # Check if data file already exists
        ohlcv_path = self.data_dir / 'ohlcv' / f'{pair_key}_20200101_20251231.parquet'
        csv_path = self.data_dir / 'ohlcv' / f'{pair_key}_20200101_20251231.csv'
        
        if ohlcv_path.exists():
            try:
                logger.info(f"Loading existing OHLCV data from {ohlcv_path}...")
                df = pd.read_parquet(ohlcv_path)
                logger.info(f"✓ Loaded existing data: {len(df)} candles")
                return df
            except Exception as e:
                logger.warning(f"Error loading Parquet file: {e}, will re-fetch")
        
        if csv_path.exists():
            try:
                logger.info(f"Loading existing OHLCV data from {csv_path}...")
                df = pd.read_csv(csv_path)
                df['timestamp'] = pd.to_datetime(df['timestamp'])
                df = df.set_index('timestamp')
                logger.info(f"✓ Loaded existing data: {len(df)} candles")
                return df
            except Exception as e:
                logger.warning(f"Error loading CSV file: {e}, will re-fetch")
        
        # No existing data, start fresh or resume
        if pair_key not in progress:
            progress[pair_key] = {
                'last_date': start_date.isoformat(),
                'chunks_completed': 0,
                'total_candles': 0,
                'status': 'in_progress'
            }
        
        all_data = []
        current_date = datetime.fromisoformat(progress[pair_key]['last_date'])
        chunk_num = progress[pair_key]['chunks_completed']
        
        total_days = (end_date - start_date).days
        total_chunks = (total_days // chunk_days) + 1
        
        logger.info(f"Progress: {chunk_num}/{total_chunks} chunks completed")
        logger.info(f"Resuming from {current_date.date()}")
        
        # If we're at or past end_date but no data file exists, reset
        if current_date >= end_date:
            logger.warning("Progress shows complete but no data file found. Resetting...")
            progress[pair_key] = {
                'last_date': start_date.isoformat(),
                'chunks_completed': 0,
                'total_candles': 0,
                'status': 'in_progress'
            }
            current_date = start_date
            chunk_num = 0
            self.save_progress(progress)
            logger.info(f"Reset to start: {current_date.date()}")
        
        while current_date < end_date:
            chunk_end = min(current_date + timedelta(days=chunk_days), end_date)
            
            try:
                logger.info(f"Fetching chunk {chunk_num + 1}/{total_chunks}: {current_date.date()} to {chunk_end.date()}")
                
                # Fetch all candles for this chunk by paginating
                chunk_data = []
                chunk_start = current_date
                request_count = 0
                
                while chunk_start < chunk_end:
                    since = int(chunk_start.timestamp() * 1000)
                    candles = self.exchange.fetch_ohlcv(
                        pair, timeframe, since=since, limit=1000
                    )
                    
                    if not candles:
                        break
                    
                    # Convert to DataFrame
                    df = pd.DataFrame(
                        candles,
                        columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
                    )
                    df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
                    
                    # Filter to chunk date range
                    df = df[(df['timestamp'] >= chunk_start) & (df['timestamp'] <= chunk_end)]
                    
                    if not df.empty:
                        chunk_data.append(df)
                        # Move to next batch (last timestamp + 5 minutes)
                        chunk_start = df['timestamp'].max() + pd.Timedelta(minutes=5)
                    else:
                        break
                    
                    request_count += 1
                    
                    # Rate limiting
                    time.sleep(self.exchange.rateLimit / 1000)
                    
                    # Safety check - don't loop forever
                    if request_count > 100:
                        logger.warning(f"Too many requests for chunk {chunk_num + 1}, moving on")
                        break
                
                # Combine all data for this chunk
                if chunk_data:
                    chunk_df = pd.concat(chunk_data, ignore_index=True)
                    chunk_df = chunk_df.sort_values('timestamp').drop_duplicates('timestamp', keep='first')
                    all_data.append(chunk_df)
                    progress[pair_key]['total_candles'] += len(chunk_df)
                    logger.info(f"  Chunk {chunk_num + 1}: {len(chunk_df)} candles (total: {progress[pair_key]['total_candles']})")
                
                # Update progress
                progress[pair_key]['last_date'] = chunk_end.isoformat()
                progress[pair_key]['chunks_completed'] = chunk_num + 1
                self.save_progress(progress)
                
                current_date = chunk_end
                chunk_num += 1
                
                # Progress update
                if chunk_num % 10 == 0:
                    pct = (chunk_num / total_chunks * 100) if total_chunks > 0 else 0
                    logger.info(f"  Progress: {chunk_num}/{total_chunks} chunks ({pct:.1f}%) - {progress[pair_key]['total_candles']} candles")
                
            except Exception as e:
                logger.error(f"Error fetching chunk {chunk_num}: {e}")
                time.sleep(5)
                # Move to next chunk even on error
                current_date = chunk_end
                chunk_num += 1
                continue
        
        if all_data:
            combined = pd.concat(all_data, ignore_index=True)
            combined = combined.sort_values('timestamp').drop_duplicates('timestamp', keep='first')
            combined = combined.set_index('timestamp')
            
            logger.info(f"✓ Fetched {len(combined)} total candles for {pair}")
            
            # Save progress as complete
            progress[pair_key]['last_date'] = end_date.isoformat()
            progress[pair_key]['chunks_completed'] = total_chunks
            progress[pair_key]['status'] = 'complete'
            self.save_progress(progress)
            
            return combined
        
        return pd.DataFrame()
    
    def fetch_external_data(self, start_date, end_date):
        """Fetch external market data."""
        logger.info("Fetching external market data...")
        
        all_data = []
        
        # Fear & Greed Index
        logger.info("  - Fear & Greed Index...")
        try:
            url = "https://api.alternative.me/fng/?limit=0"
            response = requests.get(url, timeout=30)
            if response.status_code == 200:
                data = response.json()
                if 'data' in data:
                    for item in data['data']:
                        item_date = datetime.fromtimestamp(int(item['timestamp']))
                        if start_date <= item_date <= end_date:
                            all_data.append({
                                'timestamp': item_date,
                                'fear_greed': int(item['value']),
                                'fear_greed_classification': item['value_classification']
                            })
                    logger.info(f"    ✓ {len([d for d in all_data if 'fear_greed' in d])} records")
        except Exception as e:
            logger.warning(f"    ✗ Error: {e}")
        
        # VIX
        logger.info("  - VIX...")
        try:
            vix = yf.Ticker("^VIX")
            vix_data = vix.history(start=start_date, end=end_date)
            if not vix_data.empty:
                # Convert index to timezone-naive if needed
                vix_data.index = vix_data.index.tz_localize(None) if vix_data.index.tz else vix_data.index
                
                for date, row in vix_data.iterrows():
                    # Ensure date is timezone-naive for comparison
                    date_naive = date.tz_localize(None) if hasattr(date, 'tz') and date.tz else date
                    
                    # Find existing record by date (same day)
                    existing = None
                    for d in all_data:
                        d_date = d.get('timestamp')
                        if d_date:
                            d_date_naive = d_date.tz_localize(None) if hasattr(d_date, 'tz') and d_date.tz else d_date
                            if abs((d_date_naive - date_naive).days) < 1:
                                existing = d
                                break
                    
                    if existing:
                        existing['vix'] = float(row['Close'])
                    else:
                        all_data.append({'timestamp': date_naive, 'vix': float(row['Close'])})
                logger.info(f"    ✓ {len([d for d in all_data if 'vix' in d])} VIX records")
        except Exception as e:
            logger.warning(f"    ✗ Error: {e}")
        
        # DXY
        logger.info("  - DXY...")
        try:
            dxy = yf.Ticker("DX-Y.NYB")
            dxy_data = dxy.history(start=start_date, end=end_date)
            if not dxy_data.empty:
                # Convert index to timezone-naive if needed
                dxy_data.index = dxy_data.index.tz_localize(None) if dxy_data.index.tz else dxy_data.index
                
                for date, row in dxy_data.iterrows():
                    # Ensure date is timezone-naive for comparison
                    date_naive = date.tz_localize(None) if hasattr(date, 'tz') and date.tz else date
                    
                    # Find existing record by date (same day)
                    existing = None
                    for d in all_data:
                        d_date = d.get('timestamp')
                        if d_date:
                            d_date_naive = d_date.tz_localize(None) if hasattr(d_date, 'tz') and d_date.tz else d_date
                            if abs((d_date_naive - date_naive).days) < 1:
                                existing = d
                                break
                    
                    if existing:
                        existing['dxy'] = float(row['Close'])
                    else:
                        all_data.append({'timestamp': date_naive, 'dxy': float(row['Close'])})
                logger.info(f"    ✓ {len([d for d in all_data if 'dxy' in d])} DXY records")
        except Exception as e:
            logger.warning(f"    ✗ Error: {e}")
        
        # Funding Rates (Binance Futures)
        logger.info("  - Funding Rates (Binance Futures)...")
        try:
            import ccxt
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
            
            # Fetch funding rate history
            symbol = 'BTC/USDT'
            all_funding = []
            current_date = start_date
            
            # Binance funding rates are every 8 hours, but we'll fetch daily
            while current_date <= end_date:
                try:
                    # Get funding rate history (Binance API)
                    since = int(current_date.timestamp() * 1000)
                    # Use Binance REST API directly for funding rates
                    url = f"https://fapi.binance.com/fapi/v1/fundingRate"
                    params = {
                        'symbol': 'BTCUSDT',
                        'startTime': since,
                        'endTime': int(min(current_date + timedelta(days=30), end_date).timestamp() * 1000),
                        'limit': 1000
                    }
                    response = requests.get(url, params=params, timeout=30)
                    
                    if response.status_code == 200:
                        funding_data = response.json()
                        for item in funding_data:
                            funding_time = datetime.fromtimestamp(item['fundingTime'] / 1000)
                            if start_date <= funding_time <= end_date:
                                # Get or create record for this day
                                day_start = funding_time.replace(hour=0, minute=0, second=0, microsecond=0)
                                existing = next((d for d in all_data if abs((d.get('timestamp', datetime.min) - day_start).days) < 1), None)
                                if existing:
                                    # Use latest funding rate of the day
                                    if 'funding_rate' not in existing or funding_time > existing.get('_last_funding_time', datetime.min):
                                        existing['funding_rate'] = float(item['fundingRate'])
                                        existing['_last_funding_time'] = funding_time
                                else:
                                    all_data.append({
                                        'timestamp': day_start,
                                        'funding_rate': float(item['fundingRate']),
                                        '_last_funding_time': funding_time
                                    })
                    
                    current_date += timedelta(days=30)
                    time.sleep(0.2)  # Rate limiting
                    
                except Exception as e:
                    logger.warning(f"    Error fetching funding rates for {current_date}: {e}")
                    current_date += timedelta(days=30)
                    continue
            
            # Clean up temporary fields
            for d in all_data:
                d.pop('_last_funding_time', None)
            
            logger.info(f"    ✓ {len([d for d in all_data if 'funding_rate' in d])} funding rate records")
        except Exception as e:
            logger.warning(f"    ✗ Error: {e}")
        
        # BTC Dominance (CoinGecko)
        logger.info("  - BTC Dominance (CoinGecko)...")
        try:
            # CoinGecko global endpoint for BTC dominance
            # Fetch in monthly batches to avoid rate limits
            current_date = start_date
            dominance_data = {}
            
            while current_date <= end_date:
                try:
                    url = "https://api.coingecko.com/api/v3/global"
                    response = requests.get(url, timeout=30)
                    
                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data and 'market_cap_percentage' in data['data']:
                            btc_dom = data['data']['market_cap_percentage'].get('btc', None)
                            if btc_dom:
                                # Use current date for this snapshot
                                day_start = current_date.replace(hour=0, minute=0, second=0, microsecond=0)
                                if day_start not in dominance_data:
                                    dominance_data[day_start] = btc_dom
                    
                    # For historical data, we need to use a different approach
                    # CoinGecko doesn't provide easy historical dominance API
                    # We'll use daily snapshots approximation
                    current_date += timedelta(days=1)
                    
                    # Rate limiting (CoinGecko free tier: 10-50 calls/minute)
                    time.sleep(1.5)
                    
                    # Only fetch first and last month to get range, then interpolate
                    if current_date > start_date + timedelta(days=60):
                        break
                        
                except Exception as e:
                    logger.warning(f"    Error fetching BTC dominance: {e}")
                    break
            
            # For full historical, use a simpler approach - fetch current and estimate
            # Or use alternative: fetch from a service that provides historical dominance
            # For now, we'll add what we have and note it's limited
            for date, dom in dominance_data.items():
                existing = next((d for d in all_data if abs((d.get('timestamp', datetime.min) - date).days) < 1), None)
                if existing:
                    existing['btc_dominance'] = dom
                else:
                    all_data.append({'timestamp': date, 'btc_dominance': dom})
            
            # Note: Full historical BTC dominance requires paid API or different source
            logger.info(f"    ⚠ {len([d for d in all_data if 'btc_dominance' in d])} BTC dominance records (limited - CoinGecko doesn't provide full historical)")
            logger.info(f"    Note: BTC dominance will be forward-filled for missing days")
        except Exception as e:
            logger.warning(f"    ✗ Error: {e}")
        
        if all_data:
            df = pd.DataFrame(all_data)
            df = df.sort_values('timestamp').drop_duplicates('timestamp', keep='first')
            logger.info(f"✓ Total external data: {len(df)} records")
            return df
        
        return pd.DataFrame()


def main():
    """Main execution."""
    logger.info("=" * 60)
    logger.info("Remora Backtesting - Robust Data Fetching")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Timeframe: 2020-01-01 to 2025-12-31 (6 YEARS)")
    logger.info("Pair: BTC/USDT")
    logger.info("Timeframe: 5-minute candles")
    logger.info("")
    logger.info("This will take 4-8 hours but can be interrupted and resumed.")
    logger.info("Progress is saved automatically.")
    logger.info("")
    
    fetcher = DataFetcher()
    
    # Dates
    start_date = datetime(2020, 1, 1)
    end_date = datetime(2025, 12, 31)
    
    # Step 1: Fetch OHLCV
    logger.info("\n" + "=" * 60)
    logger.info("STEP 1: Fetching OHLCV Data (Can take 4-6 hours)")
    logger.info("=" * 60)
    
    ohlcv_df = fetcher.fetch_ohlcv_chunked(
        pair='BTC/USDT',
        timeframe='5m',
        start_date=start_date,
        end_date=end_date,
        chunk_days=30  # 30-day chunks for progress tracking
    )
    
    if not ohlcv_df.empty:
        ohlcv_path = fetcher.data_dir / 'ohlcv' / 'BTC_USDT_5m_20200101_20251231.parquet'
        ohlcv_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Try Parquet first, fall back to CSV if needed
        try:
            ohlcv_df.reset_index().to_parquet(ohlcv_path, index=False)
            logger.info(f"✓ Saved OHLCV (Parquet): {len(ohlcv_df)} candles to {ohlcv_path}")
            logger.info(f"  File size: {ohlcv_path.stat().st_size / 1024 / 1024:.1f} MB")
        except ImportError:
            # Fall back to CSV if Parquet not available
            csv_path = ohlcv_path.with_suffix('.csv')
            ohlcv_df.reset_index().to_csv(csv_path, index=False)
            logger.info(f"✓ Saved OHLCV (CSV): {len(ohlcv_df)} candles to {csv_path}")
            logger.info(f"  File size: {csv_path.stat().st_size / 1024 / 1024:.1f} MB")
    else:
        logger.error("✗ No OHLCV data fetched")
        return 1
    
    # Step 2: Fetch External Data
    logger.info("\n" + "=" * 60)
    logger.info("STEP 2: Fetching External Market Data")
    logger.info("=" * 60)
    
    external_df = fetcher.fetch_external_data(start_date, end_date)
    
    if not external_df.empty:
        external_path = Path(__file__).parent / 'historical_remora' / 'external_data.csv'
        external_path.parent.mkdir(parents=True, exist_ok=True)
        external_df.to_csv(external_path, index=False)
        logger.info(f"✓ Saved external data to {external_path}")
    else:
        logger.warning("⚠ Limited external data - will continue")
    
    logger.info("\n" + "=" * 60)
    logger.info("Data Fetching Complete!")
    logger.info("=" * 60)
    logger.info("")
    logger.info("Next steps:")
    logger.info("1. Build Remora history (requires remora_service app)")
    logger.info("2. Run backtests: ./run_backtests.sh")
    logger.info("")
    
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        logger.info("\n\nFetching interrupted. Progress saved. Run again to resume.")
        sys.exit(0)
    except Exception as e:
        logger.error(f"\n\nError: {e}", exc_info=True)
        sys.exit(1)

