"""Run Freqtrade backtests for baseline and Remora-enhanced strategies."""

import logging
import subprocess
import json
import os
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from pathlib import Path

logger = logging.getLogger(__name__)


class BacktestRunner:
    """Run Freqtrade backtests and capture results."""
    
    def __init__(
        self,
        freqtrade_path: str = "freqtrade",
        user_data_dir: str = None,
        results_dir: str = None
    ):
        """
        Initialize backtest runner.
        
        Args:
            freqtrade_path: Path to freqtrade command
            user_data_dir: Freqtrade user_data directory
            results_dir: Directory to save results
        """
        self.freqtrade_path = freqtrade_path
        self.user_data_dir = user_data_dir or os.path.join(
            os.path.dirname(__file__),
            'user_data'
        )
        self.results_dir = results_dir or os.path.join(
            os.path.dirname(__file__),
            'results'
        )
        
        # Create results directory
        os.makedirs(self.results_dir, exist_ok=True)
    
    def run_backtest(
        self,
        strategy_name: str,
        timerange: str,
        pair: str = "BTC/USDT",
        timeframe: str = "5m",
        stake_amount: str = "100",
        dry_run: bool = True
    ) -> Dict:
        """
        Run a single Freqtrade backtest.
        
        Args:
            strategy_name: Name of the strategy class
            timerange: Timerange in format "20200101-20211231"
            pair: Trading pair
            timeframe: Timeframe
            stake_amount: Stake amount per trade
            dry_run: Whether to run in dry-run mode
            
        Returns:
            Dictionary with backtest results
        """
        logger.info(f"Running backtest: {strategy_name} for {timerange}")
        
        # Build freqtrade command
        cmd = [
            self.freqtrade_path,
            "backtesting",
            "--strategy", strategy_name,
            "--timerange", timerange,
            "--timeframe", timeframe,
            "--stake-amount", stake_amount,
            "--breakdown", "day",
            "--cache", "none",  # Don't use cache for reproducibility
            "--data-format-ohlcv", "jsongz",  # Use jsongz format (compressed JSON)
        ]
        
        # Note: --dry-run is not needed for backtesting (backtesting is always dry-run)
        
        # Set user_data directory if specified (this also sets config path)
        if self.user_data_dir:
            cmd.extend(["--user-data-dir", self.user_data_dir])
            # Also explicitly set config file
            config_path = os.path.join(self.user_data_dir, "config.json")
            if os.path.exists(config_path):
                cmd.extend(["-c", config_path])
        
        # Add pair if specified
        if pair:
            cmd.extend(["--pairs", pair])
        
        try:
            # Run backtest
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=3600  # 1 hour timeout
            )
            
            if result.returncode != 0:
                logger.error(f"Backtest failed: {result.stderr}")
                return {
                    'success': False,
                    'error': result.stderr,
                    'strategy': strategy_name,
                    'timerange': timerange
                }
            
            # Parse output
            output = result.stdout
            
            # Try to extract JSON results if available
            results = self._parse_backtest_output(output)
            
            results.update({
                'success': True,
                'strategy': strategy_name,
                'timerange': timerange,
                'pair': pair,
                'timeframe': timeframe,
                'raw_output': output
            })
            
            # Save results to file
            self._save_results(results, strategy_name, timerange)
            
            logger.info(f"✓ Backtest completed: {strategy_name} for {timerange}")
            return results
            
        except subprocess.TimeoutExpired:
            logger.error(f"Backtest timed out: {strategy_name} for {timerange}")
            return {
                'success': False,
                'error': 'Timeout',
                'strategy': strategy_name,
                'timerange': timerange
            }
        except Exception as e:
            logger.error(f"Error running backtest: {e}")
            return {
                'success': False,
                'error': str(e),
                'strategy': strategy_name,
                'timerange': timerange
            }
    
    def _parse_backtest_output(self, output: str) -> Dict:
        """
        Parse Freqtrade backtest output.
        
        Args:
            output: Backtest output text
            
        Returns:
            Dictionary with parsed metrics
        """
        results = {}
        
        # Try to extract key metrics from output
        # Freqtrade outputs metrics in a specific format
        
        # Look for profit percentage
        import re
        
        # Total profit
        profit_match = re.search(r'Total profit\s+([\d.]+)%', output)
        if profit_match:
            results['total_profit_pct'] = float(profit_match.group(1))
        
        # Number of trades
        trades_match = re.search(r'Total trades\s+(\d+)', output)
        if trades_match:
            results['total_trades'] = int(trades_match.group(1))
        
        # Win rate
        winrate_match = re.search(r'Win rate\s+([\d.]+)%', output)
        if winrate_match:
            results['win_rate'] = float(winrate_match.group(1))
        
        # Profit factor
        pf_match = re.search(r'Profit factor\s+([\d.]+)', output)
        if pf_match:
            results['profit_factor'] = float(pf_match.group(1))
        
        # Sharpe ratio
        sharpe_match = re.search(r'Sharpe ratio\s+([\d.]+)', output)
        if sharpe_match:
            results['sharpe_ratio'] = float(sharpe_match.group(1))
        
        # Sortino ratio
        sortino_match = re.search(r'Sortino ratio\s+([\d.]+)', output)
        if sortino_match:
            results['sortino_ratio'] = float(sortino_match.group(1))
        
        # Max drawdown
        dd_match = re.search(r'Max drawdown\s+([\d.]+)%', output)
        if dd_match:
            results['max_drawdown'] = float(dd_match.group(1))
        
        return results
    
    def _save_results(self, results: Dict, strategy_name: str, timerange: str):
        """
        Save backtest results to file.
        
        Args:
            results: Results dictionary
            strategy_name: Strategy name
            timerange: Timerange
        """
        filename = f"{strategy_name}_{timerange}.json"
        filepath = os.path.join(self.results_dir, filename)
        
        with open(filepath, 'w') as f:
            json.dump(results, f, indent=2, default=str)
        
        logger.debug(f"Saved results to {filepath}")
    
    def run_comparison(
        self,
        baseline_strategy: str,
        remora_strategy: str,
        timerange: str,
        pair: str = "BTC/USDT",
        timeframe: str = "5m"
    ) -> Dict:
        """
        Run backtest comparison between baseline and Remora-enhanced strategies.
        
        Args:
            baseline_strategy: Baseline strategy name
            remora_strategy: Remora-enhanced strategy name
            timerange: Timerange
            pair: Trading pair
            timeframe: Timeframe
            
        Returns:
            Dictionary with comparison results
        """
        logger.info(f"Running comparison: {baseline_strategy} vs {remora_strategy}")
        
        # Run baseline
        baseline_results = self.run_backtest(
            baseline_strategy,
            timerange,
            pair,
            timeframe
        )
        
        # Run Remora-enhanced
        remora_results = self.run_backtest(
            remora_strategy,
            timerange,
            pair,
            timeframe
        )
        
        # Compare results
        comparison = self._compare_results(baseline_results, remora_results)
        
        # Save comparison
        comparison_filename = f"comparison_{baseline_strategy}_{remora_strategy}_{timerange}.json"
        comparison_filepath = os.path.join(self.results_dir, comparison_filename)
        
        with open(comparison_filepath, 'w') as f:
            json.dump(comparison, f, indent=2, default=str)
        
        logger.info(f"✓ Comparison saved to {comparison_filepath}")
        return comparison
    
    def _compare_results(self, baseline: Dict, remora: Dict) -> Dict:
        """
        Compare baseline and Remora results.
        
        Args:
            baseline: Baseline results
            remora: Remora results
            
        Returns:
            Comparison dictionary
        """
        comparison = {
            'baseline': baseline,
            'remora': remora,
            'improvements': {}
        }
        
        # Calculate improvements for each metric
        metrics = [
            'total_profit_pct',
            'win_rate',
            'profit_factor',
            'sharpe_ratio',
            'sortino_ratio',
            'max_drawdown',
            'total_trades'
        ]
        
        for metric in metrics:
            baseline_val = baseline.get(metric)
            remora_val = remora.get(metric)
            
            if baseline_val is not None and remora_val is not None:
                if metric == 'max_drawdown':
                    # For drawdown, negative is better (less drawdown)
                    improvement = ((baseline_val - remora_val) / abs(baseline_val) * 100) if baseline_val != 0 else 0
                else:
                    # For other metrics, positive is better
                    improvement = ((remora_val - baseline_val) / abs(baseline_val) * 100) if baseline_val != 0 else 0
                
                comparison['improvements'][metric] = {
                    'baseline': baseline_val,
                    'remora': remora_val,
                    'improvement_pct': improvement,
                    'improvement_abs': remora_val - baseline_val
                }
        
        return comparison

