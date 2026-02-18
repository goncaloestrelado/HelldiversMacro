"""
Core functionality module
"""

from .macro_engine import MacroEngine
from .stratagem_data import STRATAGEMS, STRATAGEMS_BY_DEPARTMENT

__all__ = [
    'MacroEngine',
    'STRATAGEMS',
    'STRATAGEMS_BY_DEPARTMENT',
]
