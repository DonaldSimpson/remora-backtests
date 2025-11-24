"""Aggregate all backtest results into summary reports."""

import logging
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List
from datetime import datetime

logger = logging.getLogger(__name__)


class ResultsAggregator:
    """Aggregate backtest results into summary reports."""
    
    def __init__(self, results_dir: str):
        """
        Initialize aggregator.
        
        Args:
            results_dir: Directory with backtest results
        """
        self.results_dir = Path(results_dir)
    
    def aggregate_all_results(self) -> pd.DataFrame:
        """
        Aggregate all backtest results into a single DataFrame.
        
        Returns:
            DataFrame with all results
        """
        logger.info("Aggregating all results")
        
        all_results = []
        
        # Find all comparison files
        comparison_files = list(self.results_dir.glob("comparison_*.json"))
        
        for comp_file in comparison_files:
            try:
                with open(comp_file, 'r') as f:
                    comparison = json.load(f)
                
                baseline = comparison.get('baseline', {})
                remora = comparison.get('remora', {})
                improvements = comparison.get('improvements', {})
                
                # Create row for baseline
                baseline_row = {
                    'strategy': baseline.get('strategy', 'unknown'),
                    'version': 'baseline',
                    'timerange': baseline.get('timerange', 'unknown'),
                    'pair': baseline.get('pair', 'unknown'),
                    'total_profit_pct': baseline.get('total_profit_pct', 0),
                    'total_trades': baseline.get('total_trades', 0),
                    'win_rate': baseline.get('win_rate', 0),
                    'profit_factor': baseline.get('profit_factor', 0),
                    'sharpe_ratio': baseline.get('sharpe_ratio', 0),
                    'sortino_ratio': baseline.get('sortino_ratio', 0),
                    'max_drawdown': baseline.get('max_drawdown', 0)
                }
                all_results.append(baseline_row)
                
                # Create row for Remora
                remora_row = {
                    'strategy': remora.get('strategy', 'unknown'),
                    'version': 'remora',
                    'timerange': remora.get('timerange', 'unknown'),
                    'pair': remora.get('pair', 'unknown'),
                    'total_profit_pct': remora.get('total_profit_pct', 0),
                    'total_trades': remora.get('total_trades', 0),
                    'win_rate': remora.get('win_rate', 0),
                    'profit_factor': remora.get('profit_factor', 0),
                    'sharpe_ratio': remora.get('sharpe_ratio', 0),
                    'sortino_ratio': remora.get('sortino_ratio', 0),
                    'max_drawdown': remora.get('max_drawdown', 0)
                }
                all_results.append(remora_row)
                
            except Exception as e:
                logger.error(f"Error processing {comp_file}: {e}")
        
        df = pd.DataFrame(all_results)
        
        if not df.empty:
            logger.info(f"Aggregated {len(df)} result rows")
        
        return df
    
    def generate_summary_json(self, output_path: str):
        """
        Generate summary JSON file.
        
        Args:
            output_path: Path to save summary JSON
        """
        df = self.aggregate_all_results()
        
        if df.empty:
            logger.warning("No results to aggregate")
            return
        
        # Group by strategy and version
        summary = {}
        
        for strategy in df['strategy'].unique():
            strategy_df = df[df['strategy'] == strategy]
            baseline_df = strategy_df[strategy_df['version'] == 'baseline']
            remora_df = strategy_df[strategy_df['version'] == 'remora']
            
            summary[strategy] = {
                'baseline': baseline_df.to_dict('records') if not baseline_df.empty else [],
                'remora': remora_df.to_dict('records') if not remora_df.empty else []
            }
        
        with open(output_path, 'w') as f:
            json.dump(summary, f, indent=2, default=str)
        
        logger.info(f"Summary saved to {output_path}")
    
    def generate_summary_csv(self, output_path: str):
        """
        Generate summary CSV file.
        
        Args:
            output_path: Path to save summary CSV
        """
        df = self.aggregate_all_results()
        
        if df.empty:
            logger.warning("No results to aggregate")
            return
        
        df.to_csv(output_path, index=False)
        logger.info(f"Summary CSV saved to {output_path}")

