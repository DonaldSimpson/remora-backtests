"""Extract and analyze metrics from Freqtrade backtest results."""

import logging
import json
import pandas as pd
from pathlib import Path
from typing import Dict, List, Optional
from datetime import datetime

logger = logging.getLogger(__name__)


class MetricsExtractor:
    """Extract metrics from backtest results."""
    
    def __init__(self, results_dir: str):
        """
        Initialize metrics extractor.
        
        Args:
            results_dir: Directory containing backtest results
        """
        self.results_dir = Path(results_dir)
    
    def extract_from_json(self, json_file: str) -> Dict:
        """
        Extract metrics from a JSON results file.
        
        Args:
            json_file: Path to JSON file
            
        Returns:
            Dictionary with extracted metrics
        """
        filepath = self.results_dir / json_file
        
        if not filepath.exists():
            logger.warning(f"Results file not found: {filepath}")
            return {}
        
        try:
            with open(filepath, 'r') as f:
                data = json.load(f)
            
            return self._extract_metrics(data)
        except Exception as e:
            logger.error(f"Error extracting metrics from {json_file}: {e}")
            return {}
    
    def _extract_metrics(self, data: Dict) -> Dict:
        """
        Extract all metrics from backtest data.
        
        Args:
            data: Backtest results dictionary
            
        Returns:
            Dictionary with extracted metrics
        """
        metrics = {}
        
        # Trading metrics
        metrics['total_profit_pct'] = data.get('total_profit_pct', 0.0)
        metrics['total_trades'] = data.get('total_trades', 0)
        metrics['win_rate'] = data.get('win_rate', 0.0)
        metrics['profit_factor'] = data.get('profit_factor', 0.0)
        metrics['sharpe_ratio'] = data.get('sharpe_ratio', 0.0)
        metrics['sortino_ratio'] = data.get('sortino_ratio', 0.0)
        metrics['max_drawdown'] = data.get('max_drawdown', 0.0)
        
        # Additional metrics if available
        metrics['exposure_time'] = data.get('exposure_time', 0.0)
        metrics['avg_trade_duration'] = data.get('avg_trade_duration', 0.0)
        
        # Strategy and period info
        metrics['strategy'] = data.get('strategy', 'unknown')
        metrics['timerange'] = data.get('timerange', 'unknown')
        metrics['pair'] = data.get('pair', 'unknown')
        metrics['timeframe'] = data.get('timeframe', 'unknown')
        
        return metrics
    
    def extract_remora_metrics(
        self,
        baseline_results: Dict,
        remora_results: Dict,
        remora_history_path: Optional[str] = None
    ) -> Dict:
        """
        Extract Remora-specific metrics from comparison.
        
        Args:
            baseline_results: Baseline backtest results
            remora_results: Remora-enhanced backtest results
            remora_history_path: Path to Remora history CSV (optional)
            
        Returns:
            Dictionary with Remora-specific metrics
        """
        remora_metrics = {}
        
        # Calculate trade filtering percentage
        baseline_trades = baseline_results.get('total_trades', 0)
        remora_trades = remora_results.get('total_trades', 0)
        
        if baseline_trades > 0:
            trades_filtered = baseline_trades - remora_trades
            remora_metrics['trades_filtered_pct'] = (trades_filtered / baseline_trades) * 100
            remora_metrics['trades_filtered_count'] = trades_filtered
        else:
            remora_metrics['trades_filtered_pct'] = 0.0
            remora_metrics['trades_filtered_count'] = 0
        
        # If we have Remora history, analyze risk scores
        if remora_history_path and Path(remora_history_path).exists():
            risk_analysis = self._analyze_risk_scores(remora_history_path)
            remora_metrics.update(risk_analysis)
        
        return remora_metrics
    
    def _analyze_risk_scores(self, remora_history_path: str) -> Dict:
        """
        Analyze risk scores from Remora history.
        
        Args:
            remora_history_path: Path to Remora history CSV
            
        Returns:
            Dictionary with risk analysis
        """
        try:
            df = pd.read_csv(remora_history_path)
            
            if 'risk_score' not in df.columns:
                return {}
            
            analysis = {
                'avg_risk_score': float(df['risk_score'].mean()) if 'risk_score' in df.columns else 0.0,
                'high_risk_periods': int((df['risk_score'] > 0.7).sum()) if 'risk_score' in df.columns else 0,
                'blocked_periods': int((df['safe_to_trade'] == False).sum()) if 'safe_to_trade' in df.columns else 0
            }
            
            # Risk class distribution
            if 'risk_class' in df.columns:
                analysis['risk_class_distribution'] = df['risk_class'].value_counts().to_dict()
            
            # Regime distribution
            if 'regime' in df.columns:
                analysis['regime_distribution'] = df['regime'].value_counts().to_dict()
            
            return analysis
            
        except Exception as e:
            logger.error(f"Error analyzing risk scores: {e}")
            return {}
    
    def aggregate_results(
        self,
        results_files: List[str]
    ) -> pd.DataFrame:
        """
        Aggregate results from multiple backtest files.
        
        Args:
            results_files: List of result file names
            
        Returns:
            DataFrame with aggregated results
        """
        all_metrics = []
        
        for file in results_files:
            metrics = self.extract_from_json(file)
            if metrics:
                all_metrics.append(metrics)
        
        if not all_metrics:
            return pd.DataFrame()
        
        df = pd.DataFrame(all_metrics)
        return df
    
    def generate_summary_report(
        self,
        comparison_results: Dict,
        output_path: Optional[str] = None
    ) -> str:
        """
        Generate a summary report from comparison results.
        
        Args:
            comparison_results: Comparison results dictionary
            output_path: Optional path to save report
            
        Returns:
            Report text
        """
        baseline = comparison_results.get('baseline', {})
        remora = comparison_results.get('remora', {})
        improvements = comparison_results.get('improvements', {})
        
        report_lines = [
            "# Backtest Comparison Report",
            "",
            f"**Strategy:** {baseline.get('strategy', 'unknown')} vs {remora.get('strategy', 'unknown')}",
            f"**Period:** {baseline.get('timerange', 'unknown')}",
            f"**Pair:** {baseline.get('pair', 'unknown')}",
            "",
            "## Results Summary",
            "",
            "### Baseline Strategy",
            f"- Total Profit: {baseline.get('total_profit_pct', 0):.2f}%",
            f"- Total Trades: {baseline.get('total_trades', 0)}",
            f"- Win Rate: {baseline.get('win_rate', 0):.2f}%",
            f"- Profit Factor: {baseline.get('profit_factor', 0):.2f}",
            f"- Sharpe Ratio: {baseline.get('sharpe_ratio', 0):.2f}",
            f"- Max Drawdown: {baseline.get('max_drawdown', 0):.2f}%",
            "",
            "### Remora-Enhanced Strategy",
            f"- Total Profit: {remora.get('total_profit_pct', 0):.2f}%",
            f"- Total Trades: {remora.get('total_trades', 0)}",
            f"- Win Rate: {remora.get('win_rate', 0):.2f}%",
            f"- Profit Factor: {remora.get('profit_factor', 0):.2f}",
            f"- Sharpe Ratio: {remora.get('sharpe_ratio', 0):.2f}",
            f"- Max Drawdown: {remora.get('max_drawdown', 0):.2f}%",
            "",
            "## Improvements",
            ""
        ]
        
        for metric, improvement_data in improvements.items():
            improvement_pct = improvement_data.get('improvement_pct', 0)
            report_lines.append(
                f"- **{metric.replace('_', ' ').title()}:** "
                f"{improvement_pct:+.2f}% "
                f"({improvement_data.get('improvement_abs', 0):+.2f})"
            )
        
        report_text = "\n".join(report_lines)
        
        if output_path:
            with open(output_path, 'w') as f:
                f.write(report_text)
            logger.info(f"Report saved to {output_path}")
        
        return report_text

