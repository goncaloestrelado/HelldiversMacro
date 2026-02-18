"""
Constants for Helldivers Numpad Macros
Central location for all application constants
"""

THEME_FILES = {
    "Dark (Default)": "theme_dark_default.qss",
    "Dark with Blue Accent": "theme_dark_blue.qss",
    "Dark with Red Accent": "theme_dark_red.qss",
}

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

NUMPAD_GRID_WIDTH = 396
NUMPAD_GRID_HEIGHT = 498
NUMPAD_GRID_SPACING = 12

ICON_SIZE = 80
ICON_SPACING = 8
HEADER_HEIGHT = 32

SEARCH_HEIGHT = 32

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

ARROW_ICONS = {
    "up": "↑",
    "down": "↓",
    "left": "←",
    "right": "→"
}
