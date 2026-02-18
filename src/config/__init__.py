"""
Configuration module
Re-exports commonly used functions
"""

from .config import (
    get_app_data_dir,
    is_installed,
    get_install_type,
    is_admin,
    run_as_admin,
    find_svg_path,
    load_settings,
    save_settings,
    get_theme_stylesheet,
    PROFILES_DIR,
    ASSETS_DIR,
    SETTINGS_FILE,
)

from .constants import (
    THEME_FILES,
    DEFAULT_SETTINGS,
    NUMPAD_LAYOUT,
    KEYBIND_MAPPINGS,
    ARROW_ICONS,
)

from .version import (
    VERSION,
    APP_NAME,
    GITHUB_REPO_OWNER,
    GITHUB_REPO_NAME,
)

__all__ = [
    # config.py
    'get_app_data_dir',
    'is_installed',
    'get_install_type',
    'is_admin',
    'run_as_admin',
    'find_svg_path',
    'load_settings',
    'save_settings',
    'get_theme_stylesheet',
    'PROFILES_DIR',
    'ASSETS_DIR',
    'SETTINGS_FILE',
    # constants.py
    'THEME_FILES',
    'DEFAULT_SETTINGS',
    'NUMPAD_LAYOUT',
    'KEYBIND_MAPPINGS',
    'ARROW_ICONS',
    # version.py
    'VERSION',
    'APP_NAME',
    'GITHUB_REPO_OWNER',
    'GITHUB_REPO_NAME',
]
