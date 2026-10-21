"""
Stratagem data module for Helldivers Numpad Macros.

Provides offline fallback default stratagem data and backward compatibility.
At runtime, data is loaded from the wiki cache when available, falling back to
the bundled default dataset.
"""

import json
import os
import sys


def _load_default_stratagems():
    if getattr(sys, 'frozen', False):
        base_path = getattr(sys, '_MEIPASS', os.path.dirname(sys.executable))
    else:
        base_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))

    default_json = os.path.join(base_path, "assets", "stratagems_default.json")
    if os.path.exists(default_json):
        try:
            with open(default_json, "r", encoding="utf-8") as f:
                return json.load(f)
        except Exception:
            pass
    return {}


_default_data = _load_default_stratagems()
STRATAGEMS_BY_DEPARTMENT = _default_data.get("stratagems_by_department", {})
STRATAGEMS = {}
for _dept, _items in STRATAGEMS_BY_DEPARTMENT.items():
    if isinstance(_items, dict):
        STRATAGEMS.update(_items)
