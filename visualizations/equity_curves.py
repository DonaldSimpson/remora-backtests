"""Generate equity curve comparison charts."""

import logging
import pandas as pd
import matplotlib.pyplot as plt
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from pathlib import Path
from typing import Dict, Optional
import json

logger = logging.getLogger(__name__)


def generate_equity_curves(
    baseline_results: Dict,
    remora_results: Dict,
    output_dir: str,
    strategy_name: str,
    period: str
):
    """
    Generate equity curve comparison chart.
    
    Args:
        baseline_results: Baseline backtest results
        remora_results: Remora-enhanced backtest results
        output_dir: Output directory
        strategy_name: Strategy name
        period: Time period
    """
    logger.info(f"Generating equity curves for {strategy_name} - {period}")
    
    # Extract equity curve data if available
    # Note: This would need to be extracted from Freqtrade backtest results
    # For now, we'll create a placeholder implementation
    
    # Create figure
    fig = go.Figure()
    
    # Add baseline equity curve (placeholder - would use actual data)
    # In real implementation, this would come from Freqtrade results
    fig.add_trace(go.Scatter(
        x=[],
        y=[],
        mode='lines',
        name='Baseline',
        line=dict(color='blue', width=2)
    ))
    
    # Add Remora equity curve
    fig.add_trace(go.Scatter(
        x=[],
        y=[],
        mode='lines',
        name='Remora-Enhanced',
        line=dict(color='green', width=2)
    ))
    
    # Update layout
    fig.update_layout(
        title=f'Equity Curve Comparison: {strategy_name} ({period})',
        xaxis_title='Time',
        yaxis_title='Equity',
        hovermode='x unified',
        template='plotly_white',
        height=600
    )
    
    # Save as HTML
    output_path = Path(output_dir) / f"equity_curve_{strategy_name}_{period}.html"
    fig.write_html(str(output_path))
    logger.info(f"Saved equity curve to {output_path}")
    
    # Also save as PNG
    fig_png = go.Figure(fig)
    fig_png.update_layout(width=1200, height=600)
    png_path = Path(output_dir) / f"equity_curve_{strategy_name}_{period}.png"
    fig_png.write_image(str(png_path))
    logger.info(f"Saved equity curve PNG to {png_path}")


def generate_all_equity_curves(results_dir: str, output_dir: str):
    """
    Generate equity curves for all backtest results.
    
    Args:
        results_dir: Directory with backtest results
        output_dir: Output directory for charts
    """
    results_path = Path(results_dir)
    output_path = Path(output_dir)
    output_path.mkdir(parents=True, exist_ok=True)
    
    # Find all comparison JSON files
    comparison_files = list(results_path.glob("comparison_*.json"))
    
    for comp_file in comparison_files:
        try:
            with open(comp_file, 'r') as f:
                comparison = json.load(f)
            
            baseline = comparison.get('baseline', {})
            remora = comparison.get('remora', {})
            strategy = baseline.get('strategy', 'unknown')
            period = baseline.get('timerange', 'unknown')
            
            generate_equity_curves(
                baseline,
                remora,
                str(output_path),
                strategy,
                period
            )
        except Exception as e:
            logger.error(f"Error processing {comp_file}: {e}")

