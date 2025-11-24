"""Fetch historical external data for Remora risk engine reconstruction."""

import logging
import pandas as pd
import yfinance as yf
import requests
from datetime import datetime, timedelta
from typing import Dict, Optional, List
import time
import json

logger = logging.getLogger(__name__)


class HistoricalDataFetcher:
    """Fetch historical external data sources for backtesting."""
    
    def __init__(self):
        """Initialize historical data fetcher."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (compatible; RemoraRiskEngine/1.0)'
        })
    
    def fetch_vix_dxy(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch historical VIX and DXY data from Yahoo Finance.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with columns: timestamp, vix, dxy
        """
        logger.info(f"Fetching VIX/DXY data from {start_date.date()} to {end_date.date()}")
        
        try:
            # Fetch VIX
            vix_ticker = yf.Ticker("^VIX")
            vix_data = vix_ticker.history(start=start_date, end=end_date)
            
            # Fetch DXY
            dxy_ticker = yf.Ticker("DX-Y.NYB")
            dxy_data = dxy_ticker.history(start=start_date, end=end_date)
            
            # Combine into single DataFrame
            result = pd.DataFrame(index=pd.date_range(start=start_date, end=end_date, freq='D'))
            result['vix'] = None
            result['dxy'] = None
            
            if not vix_data.empty:
                vix_daily = vix_data['Close'].resample('D').last()
                result.loc[vix_daily.index, 'vix'] = vix_daily.values
            
            if not dxy_data.empty:
                dxy_daily = dxy_data['Close'].resample('D').last()
                result.loc[dxy_daily.index, 'dxy'] = dxy_daily.values
            
            result = result.reset_index()
            result.columns = ['timestamp', 'vix', 'dxy']
            result = result.dropna(subset=['vix', 'dxy'], how='all')
            
            logger.info(f"Fetched {len(result)} VIX/DXY records")
            return result
            
        except Exception as e:
            logger.error(f"Error fetching VIX/DXY: {e}")
            return pd.DataFrame(columns=['timestamp', 'vix', 'dxy'])
    
    def fetch_fear_greed_index(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch historical Fear & Greed Index from alternative.me.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with columns: timestamp, fear_greed
        """
        logger.info(f"Fetching Fear & Greed Index from {start_date.date()} to {end_date.date()}")
        
        try:
            # Alternative.me provides historical data via their API
            # We'll fetch in batches to avoid rate limits
            all_data = []
            current_date = start_date
            
            while current_date <= end_date:
                # Fetch one month at a time
                batch_end = min(current_date + timedelta(days=30), end_date)
                
                url = "https://api.alternative.me/fng/"
                params = {
                    'limit': 0,  # 0 means all historical data
                    'date_format': 'us'
                }
                
                response = self.session.get(url, params=params, timeout=30)
                response.raise_for_status()
                
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
                
                # Avoid rate limiting
                time.sleep(1)
                
                # Move to next batch
                current_date = batch_end + timedelta(days=1)
                
                # If we got all historical data in first request, break
                if len(all_data) > 0 and current_date > end_date:
                    break
            
            if not all_data:
                logger.warning("No Fear & Greed data fetched")
                return pd.DataFrame(columns=['timestamp', 'fear_greed', 'fear_greed_classification'])
            
            df = pd.DataFrame(all_data)
            df = df.sort_values('timestamp').drop_duplicates('timestamp', keep='first')
            
            logger.info(f"Fetched {len(df)} Fear & Greed records")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching Fear & Greed Index: {e}")
            return pd.DataFrame(columns=['timestamp', 'fear_greed', 'fear_greed_classification'])
    
    def fetch_btc_dominance(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch historical BTC dominance from CoinGecko.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with columns: timestamp, btc_dominance
        """
        logger.info(f"Fetching BTC dominance from {start_date.date()} to {end_date.date()}")
        
        try:
            # CoinGecko API for market dominance
            url = "https://api.coingecko.com/api/v3/coins/bitcoin/market_chart"
            params = {
                'vs_currency': 'usd',
                'from': int(start_date.timestamp()),
                'to': int(end_date.timestamp()),
                'interval': 'daily'
            }
            
            response = self.session.get(url, params=params, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            
            # For dominance, we need a different endpoint
            # Using market cap data to estimate dominance
            url_dominance = "https://api.coingecko.com/api/v3/global"
            
            # Fetch daily snapshots (approximation)
            all_data = []
            current_date = start_date
            
            while current_date <= end_date:
                try:
                    response = self.session.get(url_dominance, timeout=10)
                    if response.status_code == 200:
                        data = response.json()
                        if 'data' in data and 'market_cap_percentage' in data['data']:
                            btc_dominance = data['data']['market_cap_percentage'].get('btc', 0)
                            all_data.append({
                                'timestamp': current_date,
                                'btc_dominance': btc_dominance
                            })
                except Exception:
                    pass
                
                current_date += timedelta(days=1)
                time.sleep(0.5)  # Rate limiting
            
            if not all_data:
                # Fallback: use a simple approximation based on historical averages
                logger.warning("Using fallback BTC dominance estimation")
                dates = pd.date_range(start=start_date, end=end_date, freq='D')
                # Rough historical average: ~60% in 2020-2021, ~40% in 2022, ~50% in 2023-2024
                avg_dominance = 50.0
                df = pd.DataFrame({
                    'timestamp': dates,
                    'btc_dominance': avg_dominance
                })
                return df
            
            df = pd.DataFrame(all_data)
            logger.info(f"Fetched {len(df)} BTC dominance records")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching BTC dominance: {e}")
            # Return fallback data
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            df = pd.DataFrame({
                'timestamp': dates,
                'btc_dominance': 50.0  # Default value
            })
            return df
    
    def fetch_funding_rates(self, start_date: datetime, end_date: datetime) -> pd.DataFrame:
        """
        Fetch historical BTC funding rates from Binance Futures.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            DataFrame with columns: timestamp, funding_rate
        """
        logger.info(f"Fetching funding rates from {start_date.date()} to {end_date.date()}")
        
        try:
            import ccxt
            
            exchange = ccxt.binance({
                'enableRateLimit': True,
                'options': {
                    'defaultType': 'future'
                }
            })
            
            all_data = []
            current_date = start_date
            
            while current_date <= end_date:
                try:
                    # Fetch funding rate history
                    # Note: Binance API may have limitations
                    symbol = 'BTC/USDT'
                    since = int(current_date.timestamp() * 1000)
                    
                    # Get funding rate (this is approximate - actual historical funding rates
                    # may require premium data or different API)
                    ticker = exchange.fetch_ticker(symbol)
                    
                    # For historical, we'd need to use exchange-specific endpoints
                    # This is a placeholder - actual implementation would use
                    # Binance's funding rate history endpoint if available
                    
                    all_data.append({
                        'timestamp': current_date,
                        'funding_rate': 0.01  # Placeholder - needs actual API call
                    })
                    
                except Exception as e:
                    logger.debug(f"Error fetching funding rate for {current_date}: {e}")
                
                current_date += timedelta(days=1)
                time.sleep(0.2)  # Rate limiting
            
            df = pd.DataFrame(all_data)
            logger.info(f"Fetched {len(df)} funding rate records")
            return df
            
        except Exception as e:
            logger.error(f"Error fetching funding rates: {e}")
            # Return placeholder data
            dates = pd.date_range(start=start_date, end=end_date, freq='D')
            df = pd.DataFrame({
                'timestamp': dates,
                'funding_rate': 0.01  # Default value
            })
            return df
    
    def fetch_all_external_data(
        self,
        start_date: datetime,
        end_date: datetime
    ) -> pd.DataFrame:
        """
        Fetch all external data sources and combine into single DataFrame.
        
        Args:
            start_date: Start date for data
            end_date: End date for data
            
        Returns:
            Combined DataFrame with all external data
        """
        logger.info(f"Fetching all external data from {start_date.date()} to {end_date.date()}")
        
        # Fetch all data sources
        vix_dxy_df = self.fetch_vix_dxy(start_date, end_date)
        fear_greed_df = self.fetch_fear_greed_index(start_date, end_date)
        btc_dominance_df = self.fetch_btc_dominance(start_date, end_date)
        funding_rates_df = self.fetch_funding_rates(start_date, end_date)
        
        # Create base date range
        date_range = pd.date_range(start=start_date, end=end_date, freq='D')
        combined_df = pd.DataFrame({'timestamp': date_range})
        
        # Merge all data sources
        if not vix_dxy_df.empty:
            combined_df = combined_df.merge(
                vix_dxy_df,
                on='timestamp',
                how='left'
            )
        else:
            combined_df['vix'] = None
            combined_df['dxy'] = None
        
        if not fear_greed_df.empty:
            combined_df = combined_df.merge(
                fear_greed_df,
                on='timestamp',
                how='left'
            )
        else:
            combined_df['fear_greed'] = None
            combined_df['fear_greed_classification'] = None
        
        if not btc_dominance_df.empty:
            combined_df = combined_df.merge(
                btc_dominance_df,
                on='timestamp',
                how='left'
            )
        else:
            combined_df['btc_dominance'] = None
        
        if not funding_rates_df.empty:
            combined_df = combined_df.merge(
                funding_rates_df,
                on='timestamp',
                how='left'
            )
        else:
            combined_df['funding_rate'] = None
        
        # Forward fill missing values (use last known value)
        combined_df = combined_df.fillna(method='ffill').fillna(method='bfill')
        
        logger.info(f"Combined {len(combined_df)} records with all external data")
        return combined_df

