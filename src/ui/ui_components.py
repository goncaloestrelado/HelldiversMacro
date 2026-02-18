"""
UI components module for Helldivers Numpad Macros
DEPRECATED: This module is kept for backwards compatibility only.
All components have been moved to:
- dialogs.py: TestEnvironment, SettingsDialog, SettingsWindow
- widgets.py: Comm, DraggableIcon, NumpadSlot

Import from those modules directly in new code.
"""

from .dialogs import TestEnvironment, SettingsDialog, SettingsWindow
from .widgets import Comm, DraggableIcon, NumpadSlot, comm

__all__ = [
    'TestEnvironment',
    'SettingsDialog', 
    'SettingsWindow',
    'Comm',
    'comm',
    'DraggableIcon',
    'NumpadSlot',
]
