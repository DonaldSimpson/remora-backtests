"""Generate risk metrics comparison charts (Sharpe, Sortino, etc.)."""

import logging
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List
import json

logger = logging.getLogger(__name__)


def generate_risk_metrics_comparison(
    comparisons: List[Dict],
    output_dir: str
):
    """
    Generate risk metrics comparison across all strategies.
    
    Args:
        comparisons: List of comparison dictionaries
        output_dir: Output directory
    """
    logger.info("Generating risk metrics comparison")
    
    strategies = []
    baseline_sharpe = []
    remora_sharpe = []
    baseline_sortino = []
    remora_sortino = []
    
    for comp in comparisons:
        baseline = comp.get('baseline', {})
        remora = comp.get('remora', {})
        
        strategy = baseline.get('strategy', 'unknown')
        strategies.append(strategy.replace('Strategy', ''))
        
        baseline_sharpe.append(baseline.get('sharpe_ratio', 0))
        remora_sharpe.append(remora.get('sharpe_ratio', 0))
        baseline_sortino.append(baseline.get('sortino_ratio', 0))
        remora_sortino.append(remora.get('sortino_ratio', 0))
    
    # Create subplots
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Sharpe Ratio', 'Sortino Ratio'),
        shared_xaxes=True
    )
    
    # Sharpe ratio
    fig.add_trace(
        go.Bar(x=strategies, y=baseline_sharpe, name='Baseline', marker_color='blue'),
        row=1, col=1
    )
    fig.add_trace(
        go.Bar(x=strategies, y=remora_sharpe, name='Remora-Enhanced', marker_color='green'),
        row=1, col=1
    )
    
    # Sortino ratio
    fig.add_trace(
        go.Bar(x=strategies, y=baseline_sortino, name='Baseline', marker_color='blue', showlegend=False),
        row=1, col=2
    )
    fig.add_trace(
        go.Bar(x=strategies, y=remora_sortino, name='Remora-Enhanced', marker_color='green', showlegend=False),
        row=1, col=2
    )
    
    fig.update_layout(
        title='Risk-Adjusted Returns Comparison',
        height=500,
        template='plotly_white'
    )
    
    # Save
    output_path = Path(output_dir) / "risk_metrics_comparison.html"
    fig.write_html(str(output_path))
    logger.info(f"Saved risk metrics comparison to {output_path}")

