"""Generate drawdown comparison charts."""

import logging
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict
import json

logger = logging.getLogger(__name__)


def generate_drawdown_comparison(
    baseline_results: Dict,
    remora_results: Dict,
    output_dir: str,
    strategy_name: str,
    period: str
):
    """
    Generate drawdown comparison chart.
    
    Args:
        baseline_results: Baseline backtest results
        remora_results: Remora-enhanced backtest results
        output_dir: Output directory
        strategy_name: Strategy name
        period: Time period
    """
    logger.info(f"Generating drawdown comparison for {strategy_name} - {period}")
    
    # Extract drawdown data
    baseline_dd = baseline_results.get('max_drawdown', 0)
    remora_dd = remora_results.get('max_drawdown', 0)
    
    # Create bar chart
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        x=['Baseline', 'Remora-Enhanced'],
        y=[abs(baseline_dd), abs(remora_dd)],
        marker_color=['red', 'green'],
        text=[f'{baseline_dd:.2f}%', f'{remora_dd:.2f}%'],
        textposition='auto'
    ))
    
    # Calculate improvement
    improvement = ((baseline_dd - remora_dd) / abs(baseline_dd) * 100) if baseline_dd != 0 else 0
    
    fig.update_layout(
        title=f'Maximum Drawdown Comparison: {strategy_name} ({period})<br>'
              f'<sub>Improvement: {improvement:.1f}%</sub>',
        xaxis_title='Strategy',
        yaxis_title='Maximum Drawdown (%)',
        template='plotly_white',
        height=500
    )
    
    # Save
    output_path = Path(output_dir) / f"drawdown_{strategy_name}_{period}.html"
    fig.write_html(str(output_path))
    logger.info(f"Saved drawdown comparison to {output_path}")


def generate_all_drawdown_comparisons(results_dir: str, output_dir: str):
    """Generate drawdown comparisons for all results."""
    results_path = Path(results_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    comparison_files = list(results_path.glob("comparison_*.json"))
    
    for comp_file in comparison_files:
        try:
            with open(comp_file, 'r') as f:
                comparison = json.load(f)
            
            baseline = comparison.get('baseline', {})
            remora = comparison.get('remora', {})
            strategy = baseline.get('strategy', 'unknown')
            period = baseline.get('timerange', 'unknown')
            
            generate_drawdown_comparison(
                baseline,
                remora,
                str(output_path),
                strategy,
                period
            )
        except Exception as e:
            logger.error(f"Error processing {comp_file}: {e}")

