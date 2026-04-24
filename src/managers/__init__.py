"""
Managers module - Profile and update management
"""

from .profile_manager import ProfileManager
from .plugin_manager import PluginManager
from .update_manager import check_for_updates_startup, UpdateDialog, SetupDialog
from . import update_checker
from . import wiki_fetcher

__all__ = [
    'ProfileManager',
    'PluginManager',
    'check_for_updates_startup',
    'UpdateDialog',
    'SetupDialog',
    'update_checker',
    'wiki_fetcher',
]
