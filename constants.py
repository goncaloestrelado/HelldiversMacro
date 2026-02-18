"""
Constants for Helldivers Numpad Macros
Central location for all application constants
"""

# Theme file mappings
THEME_FILES = {
    "Dark (Default)": "theme_dark_default.qss",
    "Dark with Blue Accent": "theme_dark_blue.qss",
    "Dark with Red Accent": "theme_dark_red.qss",
}

# Default settings
DEFAULT_SETTINGS = {
    "latency": 20,
    "macros_enabled": False,
    "keybind_mode": "arrows",
    "require_admin": False,
    "sound_enabled": False,
    "visual_enabled": True,
    "minimize_to_tray": False,
    "auto_check_updates": True,
    "autoload_profile": False,
    "theme": "Dark (Default)",
}

# Numpad layout configuration: (scan_code, label, row, col, rowspan, colspan)
NUMPAD_LAYOUT = [
    ('53', '/', 0, 1, 1, 1),
    ('55', '*', 0, 2, 1, 1),
    ('74', '-', 0, 3, 1, 1),
    ('71', '7', 1, 0, 1, 1),
    ('72', '8', 1, 1, 1, 1),
    ('73', '9', 1, 2, 1, 1),
    ('78', '+', 1, 3, 2, 1),
    ('75', '4', 2, 0, 1, 1),
    ('76', '5', 2, 1, 1, 1),
    ('77', '6', 2, 2, 1, 1),
    ('79', '1', 3, 0, 1, 1),
    ('80', '2', 3, 1, 1, 1),
    ('81', '3', 3, 2, 1, 1),
    ('28', 'Enter', 3, 3, 2, 1),
    ('82', '0', 4, 0, 1, 2),
    ('83', '.', 4, 2, 1, 1),
]

# Grid dimensions
NUMPAD_GRID_WIDTH = 396  # 4 cols × 90px + 3 gaps × 12px
NUMPAD_GRID_HEIGHT = 498  # 5 rows × 90px + 4 gaps × 12px
NUMPAD_GRID_SPACING = 12

# Icon list settings
ICON_SIZE = 80
ICON_SPACING = 8
HEADER_HEIGHT = 32

# Search bar settings
SEARCH_HEIGHT = 32

# Department header style
DEPARTMENT_HEADER_STYLE = """
    QLabel {
        color: #00d4ff;
        font-weight: bold;
        font-size: 12px;
        padding: 10px 8px 8px 8px;
        background: rgba(0, 100, 120, 0.2);
        border-bottom: 1px solid rgba(0, 212, 255, 0.3);
        border-radius: 0px;
    }
"""

# Key binding mappings
KEYBIND_MAPPINGS = {
    "arrows": {
        "up": "up",
        "down": "down",
        "left": "left",
        "right": "right"
    },
    "wasd": {
        "up": "w",
        "down": "s",
        "left": "a",
        "right": "d"
    }
}

# Arrow display icons for test environment
ARROW_ICONS = {
    "up": "↑",
    "down": "↓",
    "left": "←",
    "right": "→"
}
