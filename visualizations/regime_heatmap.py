"""Generate regime performance heatmap."""

import logging
import pandas as pd
import plotly.graph_objects as go
from pathlib import Path
from typing import Dict, List
import json

logger = logging.getLogger(__name__)


def generate_regime_heatmap(
    comparisons: List[Dict],
    output_dir: str
):
    """
    Generate heatmap showing PnL by market regime.
    
    Args:
        comparisons: List of comparison dictionaries
        output_dir: Output directory
    """
    logger.info("Generating regime performance heatmap")
    
    # Extract regime data from comparisons
    # This would need regime information from backtest results
    regimes = ['bull', 'bear', 'choppy', 'sideways', 'high_vol', 'panic']
    strategies = []
    regime_data = {}
    
    for comp in comparisons:
        strategy = comp.get('baseline', {}).get('strategy', 'unknown')
        strategies.append(strategy.replace('Strategy', ''))
        
        # Placeholder - would extract from actual backtest data
        regime_data[strategy] = {
            'bull': 0.0,
            'bear': 0.0,
            'choppy': 0.0,
            'sideways': 0.0,
            'high_vol': 0.0,
            'panic': 0.0
        }
    
    # Create heatmap data
    z_data = []
    for strategy in strategies:
        row = [regime_data.get(strategy, {}).get(regime, 0) for regime in regimes]
        z_data.append(row)
    
    fig = go.Figure(data=go.Heatmap(
        z=z_data,
        x=regimes,
        y=strategies,
        colorscale='RdYlGn',
        text=z_data,
        texttemplate='%{text:.1f}%',
        textfont={"size": 10},
        colorbar=dict(title="PnL %")
    ))
    
    fig.update_layout(
        title='Performance by Market Regime',
        xaxis_title='Market Regime',
        yaxis_title='Strategy',
        height=400,
        template='plotly_white'
    )
    
    output_path = Path(output_dir) / "regime_heatmap.html"
    fig.write_html(str(output_path))
    logger.info(f"Saved regime heatmap to {output_path}")

