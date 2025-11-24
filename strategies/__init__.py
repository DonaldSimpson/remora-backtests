"""Backtesting strategies."""

# Baseline strategies
from .NFIQuickstartStrategy import NFIQuickstartStrategy
from .MACDCrossStrategy import MACDCrossStrategy
from .RSIEMAStrategy import RSIEMAStrategy
from .BollingerBreakoutStrategy import BollingerBreakoutStrategy

# Remora-enhanced strategies
from .NFIQuickstartRemoraStrategy import NFIQuickstartRemoraStrategy
from .MACDCrossRemoraStrategy import MACDCrossRemoraStrategy
from .RSIEMARemoraStrategy import RSIEMARemoraStrategy
from .BollingerBreakoutRemoraStrategy import BollingerBreakoutRemoraStrategy

# Remora wrapper
from .RemoraStrategyWrapper import RemoraStrategyWrapper, create_remora_strategy

__all__ = [
    'NFIQuickstartStrategy',
    'MACDCrossStrategy',
    'RSIEMAStrategy',
    'BollingerBreakoutStrategy',
    'NFIQuickstartRemoraStrategy',
    'MACDCrossRemoraStrategy',
    'RSIEMARemoraStrategy',
    'BollingerBreakoutRemoraStrategy',
    'RemoraStrategyWrapper',
    'create_remora_strategy'
]

