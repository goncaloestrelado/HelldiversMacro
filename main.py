import sys
import os
import ctypes
import json

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, QLabel,
                             QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, QComboBox,
                             QMessageBox, QListWidget, QToolButton, QCheckBox,
                             QSizePolicy, QListWidgetItem, QSlider, QInputDialog,
                             QFileDialog, QStackedWidget, QFormLayout, QDialog, QBoxLayout,
                             QPlainTextEdit, QStyle, QColorDialog)
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize, pyqtSignal, QByteArray, QPoint
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor, QCursor, QKeySequence
from PyQt6.QtSvg import QSvgRenderer

from src.config import (PROFILES_DIR, ASSETS_DIR, get_theme_stylesheet, load_settings, 
                       save_settings, get_asset_path, set_icon_overrides)
from src.config.constants import NUMPAD_LAYOUT, THEME_FILES, KEYBIND_MAPPINGS, NUMPAD_GRID_WIDTH, NUMPAD_GRID_HEIGHT
from src.core.stratagem_data import STRATAGEMS_BY_DEPARTMENT as BASE_STRATAGEMS_BY_DEPARTMENT
from src.config.version import VERSION, APP_NAME
from src.ui.dialogs import TestEnvironment, SettingsWindow
from src.ui.widgets import DraggableIcon, NumpadSlot, comm, CollapsibleDepartmentHeader, DeletableComboBox
from src.managers.profile_manager import ProfileManager
from src.managers.plugin_manager import PluginManager
from src.core.macro_engine import MacroEngine
from src.ui.tray_manager import TrayManager
from src.managers.update_manager import check_for_updates_startup


DEFAULT_SLOT_LAYOUT_NAME = "Default Numpad"
NEW_LAYOUT_OPTION_LABEL = "New Layout..."
MAX_CUSTOM_LAYOUT_KEYS = 20
GRID_PICKER_MAX_ROWS = 5
GRID_PICKER_MAX_COLS = 10
CUSTOM_SLOT_SCAN_CODES = [
    "53", "55", "74",
    "71", "72", "73", "78",
    "75", "76", "77",
    "79", "80", "81", "28",
    "82", "83", "69",
    "custom_18", "custom_19", "custom_20", "custom_21",
]


class SequenceRecorderDialog(QDialog):
    """Simple direction recorder dialog for stratagem sequence."""

    VALID_STEPS = ["up", "down", "left", "right"]

    def __init__(self, parent=None, initial_sequence=None):
        super().__init__(parent)
        self.setWindowTitle("Record Sequence")
        self.setModal(True)
        self.setMinimumWidth(460)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)

        self.sequence = []
        if isinstance(initial_sequence, list):
            self.sequence = [step for step in initial_sequence if step in self.VALID_STEPS]

        layout = QVBoxLayout(self)

        instruction_label = QLabel("Press Arrow Keys or your selected key mode (WASD/ESDF) to record input")
        instruction_label.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(instruction_label)

        self.sequence_label = QLabel("")
        self.sequence_label.setWordWrap(True)
        self.sequence_label.setStyleSheet("font-size: 15px; font-weight: bold;")
        self.sequence_label.setMinimumHeight(70)
        self.sequence_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._refresh_label()
        layout.addWidget(self.sequence_label)

        row = QGridLayout()
        btn_up = QPushButton("↑")
        btn_down = QPushButton("↓")
        btn_left = QPushButton("←")
        btn_right = QPushButton("→")
        for btn in (btn_up, btn_down, btn_left, btn_right):
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
            btn.setFixedSize(48, 36)
        btn_up.clicked.connect(lambda: self._add_step("up"))
        btn_down.clicked.connect(lambda: self._add_step("down"))
        btn_left.clicked.connect(lambda: self._add_step("left"))
        btn_right.clicked.connect(lambda: self._add_step("right"))
        row.addWidget(btn_up, 0, 1)
        row.addWidget(btn_left, 1, 0)
        row.addWidget(btn_down, 1, 1)
        row.addWidget(btn_right, 1, 2)
        layout.addLayout(row)

        actions = QHBoxLayout()
        clear_btn = QPushButton("Clear")
        clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        clear_btn.clicked.connect(self._clear)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        save_btn.clicked.connect(self.accept)
        actions.addWidget(clear_btn)
        actions.addStretch(1)
        actions.addWidget(cancel_btn)
        actions.addWidget(save_btn)
        layout.addLayout(actions)

    def showEvent(self, event):
        """Start capturing keyboard input when recorder opens."""
        super().showEvent(event)
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)
        self.grabKeyboard()

    def closeEvent(self, event):
        """Release keyboard capture when recorder closes."""
        self.releaseKeyboard()
        super().closeEvent(event)

    def _add_step(self, step):
        self.sequence.append(step)
        self._refresh_label()

    def _clear(self):
        self.sequence = []
        self._refresh_label()

    def _refresh_label(self):
        if not self.sequence:
            self.sequence_label.setText("Input: (empty)")
            return

        symbol_map = {
            "up": "↑",
            "down": "↓",
            "left": "←",
            "right": "→",
        }
        symbols = " ".join(symbol_map.get(step, step) for step in self.sequence)
        words = ", ".join(self.sequence)
        self.sequence_label.setText(f"Input: {symbols}\n({words})")

    def keyPressEvent(self, event):
        """Capture arrow keys and active configured key mode as sequence input."""
        key_map = {
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
        }

        active_mode = "arrows"
        if self.parent() and hasattr(self.parent(), "global_settings"):
            active_mode = self.parent().global_settings.get("keybind_mode", "arrows")

        if active_mode == "wasd":
            key_map.update({
                Qt.Key.Key_W: "up",
                Qt.Key.Key_S: "down",
                Qt.Key.Key_A: "left",
                Qt.Key.Key_D: "right",
            })
        elif active_mode == "esdf":
            key_map.update({
                Qt.Key.Key_E: "up",
                Qt.Key.Key_D: "down",
                Qt.Key.Key_S: "left",
                Qt.Key.Key_F: "right",
            })

        mapped = key_map.get(event.key())
        if mapped:
            self._add_step(mapped)
            event.accept()
            return

        if event.key() == Qt.Key.Key_Backspace and self.sequence:
            self.sequence.pop()
            self._refresh_label()
            event.accept()
            return

        if event.key() in (Qt.Key.Key_Return, Qt.Key.Key_Enter):
            self.accept()
            event.accept()
            return

        super().keyPressEvent(event)


class SvgPathDialog(QDialog):
    """Dialog to choose an SVG path by typing or browsing file."""

    def __init__(self, parent=None, initial_path="", initial_svg_code=""):
        super().__init__(parent)
        self.setWindowTitle("Associate SVG")
        self.setModal(True)
        self.setMinimumWidth(520)

        layout = QVBoxLayout(self)
        info = QLabel("Choose an SVG file path or paste SVG code:")
        info.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(info)

        row = QHBoxLayout()
        self.path_input = QLineEdit(initial_path or "")
        self.path_input.setPlaceholderText("C:/path/to/icon.svg")
        row.addWidget(self.path_input, 1)

        browse_btn = QPushButton("Browse")
        browse_btn.clicked.connect(self.browse_svg)
        row.addWidget(browse_btn)
        layout.addLayout(row)

        code_label = QLabel("Or paste SVG code:")
        code_label.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(code_label)

        self.svg_code_input = QPlainTextEdit()
        self.svg_code_input.setPlaceholderText("<svg ...>...</svg>")
        self.svg_code_input.setPlainText(initial_svg_code or "")
        self.svg_code_input.setMinimumHeight(140)
        layout.addWidget(self.svg_code_input)

        actions = QHBoxLayout()
        actions.addStretch(1)
        cancel_btn = QPushButton("Cancel")
        cancel_btn.clicked.connect(self.reject)
        save_btn = QPushButton("Save")
        save_btn.clicked.connect(self.accept)
        actions.addWidget(cancel_btn)
        actions.addWidget(save_btn)
        layout.addLayout(actions)

    def browse_svg(self):
        """Open file dialog to choose SVG file."""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Choose SVG",
            "",
            "SVG Files (*.svg);;All Files (*.*)",
        )
        if file_path:
            self.path_input.setText(file_path)

    def get_selection(self):
        """Return selected SVG path and pasted SVG code."""
        return self.path_input.text().strip(), self.svg_code_input.toPlainText().strip()


class KeyCaptureDialog(QDialog):
    """Dialog that captures next pressed key for slot assignment."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Assign Key")
        self.setModal(True)
        self.setMinimumWidth(360)
        self.captured_scan_code = None
        self.captured_label = None

        layout = QVBoxLayout(self)
        info = QLabel("Press the key to assign to this slot.\nPress Esc to cancel.")
        info.setStyleSheet("color: #aaa;")
        layout.addWidget(info)

        self.capture_label = QLabel("Waiting for key input...")
        self.capture_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.capture_label.setStyleSheet("font-size: 14px; font-weight: bold;")
        layout.addWidget(self.capture_label)

    def showEvent(self, event):
        super().showEvent(event)
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.reject()
            return

        scan_code = int(event.nativeScanCode()) if hasattr(event, "nativeScanCode") else 0
        if scan_code <= 0:
            return

        key_label = QKeySequence(event.key()).toString()
        if not key_label:
            key_label = event.text().strip().upper() if event.text() else "Unknown"
        if not key_label:
            key_label = f"SC {scan_code}"

        self.captured_scan_code = str(scan_code)
        self.captured_label = key_label
        self.capture_label.setText(f"Assigned: {key_label}")
        self.accept()


class StratagemEntryWidget(QWidget):
    """Single stratagem entry row with name + sequence record/save."""

    VALID_STEPS = {"up", "down", "left", "right"}
    entryUpdated = pyqtSignal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.saved_name = None
        self.saved_sequence = None
        self.saved_svg_path = None
        self.saved_svg_code = None
        self.svg_path = ""
        self.svg_code = ""

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        top_row = QHBoxLayout()

        self.name_input = QLineEdit()
        self.name_input.setPlaceholderText("Stratagem name")
        top_row.addWidget(self.name_input, 2)

        self.sequence_input = QLineEdit()
        self.sequence_input.setPlaceholderText("down,left,up,right")
        top_row.addWidget(self.sequence_input, 2)

        layout.addLayout(top_row)

        actions_row = QHBoxLayout()

        self.record_btn = QPushButton("Record")
        self.record_btn.setMinimumWidth(100)
        self.record_btn.setMaximumWidth(120)
        self.record_btn.setFixedHeight(32)
        self.record_btn.clicked.connect(self.record_sequence)
        actions_row.addWidget(self.record_btn)

        self.svg_btn = QPushButton("Associate SVG")
        self.svg_btn.setMinimumWidth(130)
        self.svg_btn.setMaximumWidth(160)
        self.svg_btn.setFixedHeight(32)
        self.svg_btn.clicked.connect(self.select_svg)
        actions_row.addWidget(self.svg_btn)

        self.save_btn = QPushButton("Save")
        self.save_btn.setMinimumWidth(90)
        self.save_btn.setMaximumWidth(110)
        self.save_btn.setFixedHeight(32)
        self.save_btn.clicked.connect(self.save_entry)
        actions_row.addWidget(self.save_btn)

        actions_row.addStretch(1)

        layout.addLayout(actions_row)

        self.svg_path_label = QLabel("SVG: not set")
        self.svg_path_label.setStyleSheet("color: #888; font-size: 10px;")
        self.svg_path_label.setWordWrap(True)
        layout.addWidget(self.svg_path_label)

        self.state_label = QLabel("")
        self.state_label.setStyleSheet("color: #888; font-size: 10px;")
        layout.addWidget(self.state_label)

        self.name_input.textChanged.connect(self._mark_dirty)
        self.sequence_input.textChanged.connect(self._mark_dirty)

    def record_sequence(self):
        current_sequence = self._parse_sequence_text(self.sequence_input.text())
        dialog = SequenceRecorderDialog(self, initial_sequence=current_sequence)
        if dialog.exec():
            self.sequence_input.setText(",".join(dialog.sequence))

    def select_svg(self):
        """Choose svg path by dialog."""
        dialog = SvgPathDialog(self, initial_path=self.svg_path, initial_svg_code=self.svg_code)
        if dialog.exec():
            selected_path, selected_code = dialog.get_selection()
            self.svg_path = selected_path
            self.svg_code = selected_code
            if selected_code:
                self.svg_path_label.setText("SVG: code pasted")
            elif selected_path:
                self.svg_path_label.setText(f"SVG: {selected_path}")
            else:
                self.svg_path_label.setText("SVG: not set")
            self._mark_dirty()

    def _mark_dirty(self):
        """Reset saved state after edits."""
        self.saved_name = None
        self.saved_sequence = None
        self.saved_svg_path = None
        self.saved_svg_code = None
        self.state_label.setText("Unsaved")
        self.entryUpdated.emit()

    def _parse_sequence_text(self, text):
        if not isinstance(text, str):
            return []
        return [step.strip().lower() for step in text.split(",") if step.strip()]

    def save_entry(self):
        name = self.name_input.text().strip()
        sequence = self._parse_sequence_text(self.sequence_input.text())
        if not name:
            self.state_label.setText("Name required")
            return False
        if not sequence or any(step not in self.VALID_STEPS for step in sequence):
            self.state_label.setText("Invalid sequence")
            return False
        has_svg_path = bool(self.svg_path)
        has_svg_code = bool(self.svg_code)
        if not has_svg_path and not has_svg_code:
            self.state_label.setText("SVG required")
            return False
        if has_svg_path and not self.svg_path.lower().endswith(".svg"):
            self.state_label.setText("SVG path must end with .svg")
            return False
        if has_svg_code and "<svg" not in self.svg_code.lower():
            self.state_label.setText("Invalid SVG code")
            return False

        self.saved_name = name
        self.saved_sequence = sequence
        self.saved_svg_path = self.svg_path
        self.saved_svg_code = self.svg_code
        self.state_label.setText("Saved")
        self.entryUpdated.emit()
        return True

    def has_any_input(self):
        """Check whether row has any user input."""
        return bool(
            self.name_input.text().strip()
            or self.sequence_input.text().strip()
            or self.svg_path.strip()
            or self.svg_code.strip()
        )

    def get_saved_entry(self):
        if self.saved_name and self.saved_sequence and (self.saved_svg_path or self.saved_svg_code):
            return self.saved_name, self.saved_sequence, self.saved_svg_path, self.saved_svg_code
        return None


class StratagemApp(QMainWindow):
    """Main application window for Helldivers 2 Numpad Commander"""
    
    def __init__(self):
        super().__init__()
        self.slots = {}
        self.setWindowTitle(f"{APP_NAME} - Numpad Commander")
        self.global_settings = load_settings()
        self.slot_layouts = self._load_slot_layouts_from_settings()
        self.active_slot_layout_name = self._sanitize_layout_name(
            self.global_settings.get("active_slot_layout", DEFAULT_SLOT_LAYOUT_NAME)
        )
        if self.active_slot_layout_name not in self.slot_layouts:
            self.active_slot_layout_name = DEFAULT_SLOT_LAYOUT_NAME

        self.grid_picker_selected_rows = 4
        self.grid_picker_selected_cols = 4
        self.grid_picker_selected_rows, self.grid_picker_selected_cols = self._clamp_picker_size(
            self.grid_picker_selected_rows,
            self.grid_picker_selected_cols,
        )
        self.grid_picker_preview_size = None
        self.grid_picker_cells = []
        self.pending_layout_key_bindings = {}
        self.pending_cleared_slot_indexes = set()
        self.grid_picker_close_timer = QTimer(self)
        self.grid_picker_close_timer.setSingleShot(True)
        self.grid_picker_close_timer.setInterval(240)
        self.grid_picker_close_timer.timeout.connect(self._hide_grid_picker_popup_if_outside)
        self.slots_resize_timer = QTimer(self)
        self.slots_resize_timer.setSingleShot(True)
        self.slots_resize_timer.setInterval(5)
        self.slots_resize_timer.timeout.connect(self._auto_adjust_window_for_slots_preview)
        self.main_resize_timer = QTimer(self)
        self.main_resize_timer.setSingleShot(True)
        self.main_resize_timer.setInterval(20)
        self.main_resize_timer.timeout.connect(self._auto_adjust_window_for_main_slots)

        self.plugin_creator_dirty = False
        self._macro_state_before_plugins = None
        self._macro_forced_by_plugins = False
        self._load_runtime_plugin_data()
        self.saved_state = None
        self.undo_btn = None
        self.save_btn = None
        self.department_expanded_state = {}  # Track which departments are expanded/collapsed
        
        self.macro_engine = MacroEngine(
            lambda: self.slots,
            lambda: self.global_settings,
            self.map_direction_to_key
        )
        
        self.initUI()
        self.refresh_profiles()
        
        self.tray_manager = TrayManager(
            self.app_icon if hasattr(self, 'app_icon') and self.app_icon else None
        )
        self.tray_manager.toggle_macros.connect(self.set_macros_enabled)
        self.tray_manager.show_window.connect(self._show_window)
        self.tray_manager.quit_app.connect(self.quit_application)
        self.tray_manager.setup()
        
        self._autoload_last_profile()
        
        if self.global_settings.get("auto_check_updates", True):
            QTimer.singleShot(1000, self.check_for_updates_startup)

    def _sanitize_layout_name(self, name):
        """Return a cleaned layout name, or empty string when invalid."""
        if not isinstance(name, str):
            return ""
        return name.strip()

    def _clamp_picker_size(self, rows, cols):
        """Clamp picker dimensions to picker bounds and max allowed key count."""
        try:
            rows = int(rows)
        except (TypeError, ValueError):
            rows = 1
        try:
            cols = int(cols)
        except (TypeError, ValueError):
            cols = 1

        rows = max(1, min(rows, GRID_PICKER_MAX_ROWS))
        cols = max(1, min(cols, GRID_PICKER_MAX_COLS))

        while rows * cols > MAX_CUSTOM_LAYOUT_KEYS:
            if cols >= rows and cols > 1:
                cols -= 1
            elif rows > 1:
                rows -= 1
            else:
                break

        return rows, cols

    def _default_slot_layout_definition(self):
        """Return default fixed numpad layout definition."""
        return {
            "type": "default_numpad",
        }

    def _default_numpad_preview_template(self):
        """Return preview data that visually matches the classic default numpad layout."""
        return {
            "rows": 5,
            "cols": 4,
            "key_bindings": {
                "1": {"scan_code": "53", "label": "/"},
                "2": {"scan_code": "55", "label": "*"},
                "3": {"scan_code": "74", "label": "-"},
                "4": {"scan_code": "71", "label": "7"},
                "5": {"scan_code": "72", "label": "8"},
                "6": {"scan_code": "73", "label": "9"},
                "7": {"scan_code": "78", "label": "+"},
                "8": {"scan_code": "75", "label": "4"},
                "9": {"scan_code": "76", "label": "5"},
                "10": {"scan_code": "77", "label": "6"},
                "12": {"scan_code": "79", "label": "1"},
                "13": {"scan_code": "80", "label": "2"},
                "14": {"scan_code": "81", "label": "3"},
                "15": {"scan_code": "28", "label": "Enter"},
                "16": {"scan_code": "82", "label": "0"},
                "18": {"scan_code": "83", "label": "."},
            },
            "cleared_slots": [0, 11, 17, 19],
        }

    def _normalize_custom_layout_definition(self, layout_definition):
        """Normalize a custom grid layout definition."""
        if not isinstance(layout_definition, dict):
            return None

        layout_type = layout_definition.get("type", "")
        if layout_type != "grid":
            return None

        try:
            rows = int(layout_definition.get("rows", 0))
            cols = int(layout_definition.get("cols", 0))
        except (TypeError, ValueError):
            return None

        if rows < 1 or cols < 1:
            return None
        if rows > GRID_PICKER_MAX_ROWS or cols > GRID_PICKER_MAX_COLS:
            return None
        if rows * cols > MAX_CUSTOM_LAYOUT_KEYS:
            return None

        key_bindings = {}
        raw_bindings = layout_definition.get("key_bindings", {})
        if isinstance(raw_bindings, dict):
            slot_count = min(rows * cols, MAX_CUSTOM_LAYOUT_KEYS, len(CUSTOM_SLOT_SCAN_CODES))
            for key, binding in raw_bindings.items():
                try:
                    index = int(key)
                except (TypeError, ValueError):
                    continue
                if index < 0 or index >= slot_count:
                    continue
                if not isinstance(binding, dict):
                    continue

                scan_code = str(binding.get("scan_code", "")).strip()
                if not scan_code:
                    continue

                label = str(binding.get("label", "")).strip()
                if not label:
                    label = f"Key {index + 1}"

                key_bindings[str(index)] = {
                    "scan_code": scan_code,
                    "label": label,
                }

        cleared_slots = set()
        raw_cleared = layout_definition.get("cleared_slots", [])
        if not isinstance(raw_cleared, list):
            raw_cleared = layout_definition.get("hidden_slots", [])  # backward compatibility
        if isinstance(raw_cleared, list):
            slot_count = min(rows * cols, MAX_CUSTOM_LAYOUT_KEYS, len(CUSTOM_SLOT_SCAN_CODES))
            for value in raw_cleared:
                try:
                    index = int(value)
                except (TypeError, ValueError):
                    continue
                if 0 <= index < slot_count:
                    cleared_slots.add(index)

        return {
            "type": "grid",
            "rows": rows,
            "cols": cols,
            "key_bindings": key_bindings,
            "cleared_slots": sorted(cleared_slots),
        }

    def _load_slot_layouts_from_settings(self):
        """Load layout presets from settings and ensure a default exists."""
        layouts = {
            DEFAULT_SLOT_LAYOUT_NAME: self._default_slot_layout_definition(),
        }

        raw_layouts = self.global_settings.get("slot_layouts", {})
        if not isinstance(raw_layouts, dict):
            return layouts

        for layout_name, layout_definition in raw_layouts.items():
            clean_name = self._sanitize_layout_name(layout_name)
            if not clean_name or clean_name == DEFAULT_SLOT_LAYOUT_NAME:
                continue

            normalized = self._normalize_custom_layout_definition(layout_definition)
            if normalized:
                layouts[clean_name] = normalized

        return layouts

    def _persist_slot_layout_settings(self):
        """Persist slot layouts and active layout into global settings."""
        custom_layouts = {
            name: definition
            for name, definition in self.slot_layouts.items()
            if name != DEFAULT_SLOT_LAYOUT_NAME
        }

        self.global_settings["slot_layouts"] = custom_layouts
        self.global_settings["active_slot_layout"] = self.active_slot_layout_name
        self.save_global_settings()

    def _build_slot_entries_for_layout(self, layout_name):
        """Build slot tuple entries matching NumpadSlot constructor format."""
        layout_definition = self.slot_layouts.get(layout_name)
        if not layout_definition:
            layout_definition = self._default_slot_layout_definition()

        if layout_definition.get("type") == "default_numpad":
            return [(scan, label, row, col, rowspan, colspan, False) for scan, label, row, col, rowspan, colspan in NUMPAD_LAYOUT]

        if layout_definition.get("type") == "grid":
            rows = int(layout_definition.get("rows", 1))
            cols = int(layout_definition.get("cols", 1))
            slot_count = min(rows * cols, MAX_CUSTOM_LAYOUT_KEYS, len(CUSTOM_SLOT_SCAN_CODES))
            key_bindings = layout_definition.get("key_bindings", {}) if isinstance(layout_definition, dict) else {}
            cleared_slots = set()
            raw_cleared = layout_definition.get("cleared_slots", []) if isinstance(layout_definition, dict) else []
            if not isinstance(raw_cleared, list) and isinstance(layout_definition, dict):
                raw_cleared = layout_definition.get("hidden_slots", [])  # backward compatibility
            if isinstance(raw_cleared, list):
                for value in raw_cleared:
                    try:
                        cleared_slots.add(int(value))
                    except (TypeError, ValueError):
                        continue
            entries = []
            for index in range(slot_count):
                row = index // cols
                col = index % cols
                default_scan_code = str(CUSTOM_SLOT_SCAN_CODES[index])
                default_label = str(index + 1)
                hidden = index in cleared_slots

                binding = key_bindings.get(str(index), {}) if isinstance(key_bindings, dict) else {}
                scan_code = str(binding.get("scan_code", default_scan_code)).strip() or default_scan_code
                label = str(binding.get("label", default_label)).strip() or default_label
                entries.append((scan_code, label, row, col, 1, 1, hidden))
            return entries

        return [(scan, label, row, col, rowspan, colspan, False) for scan, label, row, col, rowspan, colspan in NUMPAD_LAYOUT]

    def _load_runtime_plugin_data(self):
        """Load merged runtime plugin data into app state."""
        runtime_data = PluginManager.build_runtime_data(BASE_STRATAGEMS_BY_DEPARTMENT, THEME_FILES)
        self.stratagems_by_department = runtime_data["stratagems_by_department"]
        self.stratagems = runtime_data["stratagems"]
        self.theme_files = runtime_data["theme_files"]
        self.theme_sources = runtime_data.get("theme_sources", {})
        self.loaded_plugins = runtime_data["loaded_plugins"]
        self._merge_custom_themes_into_runtime()
        set_icon_overrides(runtime_data["icon_overrides"])

    def _normalize_custom_theme_colors(self, colors):
        """Normalize custom theme palette values into expected keys."""
        if not isinstance(colors, dict):
            return {
                "background_color": "#151a18",
                "border_color": "#2f7a5d",
                "accent_color": "#4bbf8a",
            }

        background = colors.get("background_color") or colors.get("background")
        border = colors.get("border_color") or colors.get("border")
        accent = colors.get("accent_color") or colors.get("accent")

        background = background.strip() if isinstance(background, str) and background.strip() else "#151a18"
        border = border.strip() if isinstance(border, str) and border.strip() else "#2f7a5d"
        accent = accent.strip() if isinstance(accent, str) and accent.strip() else "#4bbf8a"

        return {
            "background_color": background,
            "border_color": border,
            "accent_color": accent,
        }

    def _merge_custom_themes_into_runtime(self):
        """Merge persisted user custom themes into runtime theme list."""
        custom_themes = self.global_settings.get("custom_themes", {})
        if not isinstance(custom_themes, dict):
            return

        for theme_name, palette in custom_themes.items():
            if not isinstance(theme_name, str) or not theme_name.strip():
                continue

            clean_name = theme_name.strip()
            self.theme_files[clean_name] = self._normalize_custom_theme_colors(palette)
            self.theme_sources[clean_name] = "User custom"

    def save_custom_theme(self, theme_name, colors):
        """Persist a user-created custom theme and inject it into runtime theme list."""
        if not isinstance(theme_name, str) or not theme_name.strip():
            return False

        clean_name = theme_name.strip()
        palette = self._normalize_custom_theme_colors(colors)

        custom_themes = self.global_settings.get("custom_themes", {})
        if not isinstance(custom_themes, dict):
            custom_themes = {}

        custom_themes[clean_name] = palette
        self.global_settings["custom_themes"] = custom_themes
        self.theme_files[clean_name] = palette
        self.theme_sources[clean_name] = "User custom"
        self.save_global_settings()
        return True

    def delete_custom_theme(self, theme_name):
        """Delete a user custom theme from settings/runtime state."""
        if not isinstance(theme_name, str) or not theme_name.strip():
            return False

        clean_name = theme_name.strip()
        custom_themes = self.global_settings.get("custom_themes", {})
        if not isinstance(custom_themes, dict) or clean_name not in custom_themes:
            return False

        custom_themes.pop(clean_name, None)
        self.global_settings["custom_themes"] = custom_themes

        self.theme_files.pop(clean_name, None)
        self.theme_sources.pop(clean_name, None)

        if self.global_settings.get("theme") == clean_name:
            self.global_settings["theme"] = "Dark (Default)"
            self.apply_theme("Dark (Default)")

        self.save_global_settings()
        return True

    def _rebuild_icon_sidebar(self):
        """Rebuild stratagem sidebar list after plugin/theme runtime changes."""
        if not hasattr(self, "icon_list"):
            return

        search_text = self.search.text() if hasattr(self, "search") else ""
        self.icon_list.clear()
        self.icon_widgets = []
        self.icon_items = []
        self.header_items = []
        self.department_expanded_state = {}
        self.toggle_all_collapsed = False
        self.update_toggle_all_button_state()

        self._populate_icon_list()
        self.filter_icons(search_text)
        self.update_header_widths()

    def apply_plugin_manifest_selection(self, selected_manifest_paths):
        """Apply plugin checkbox selection, reload runtime data and refresh sidebar/themes."""
        if not PluginManager.set_enabled_manifests(selected_manifest_paths):
            self.show_status("Plugin selection invalid", 2000)
            return

        self._load_runtime_plugin_data()
        self._rebuild_icon_sidebar()

        theme_name = self.global_settings.get("theme", "Dark (Default)")
        if theme_name not in self.theme_files:
            theme_name = "Dark (Default)"
            self.global_settings["theme"] = theme_name
            self.save_global_settings()

        self.apply_theme(theme_name)
        self.refresh_main_plugins_page()
        self.show_status("Customizations applied and reloaded", 2200)

    def initUI(self):
        """Initialize the user interface"""
        self.setObjectName("main_window")
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        
        # Apply theme
        theme_name = self.global_settings.get("theme", "Dark (Default)")
        if theme_name not in self.theme_files:
            theme_name = "Dark (Default)"
            self.global_settings["theme"] = theme_name
            self.save_global_settings()
        self.apply_theme(theme_name)
        
        self._load_app_icon()
        
        central_widget = QWidget()
        root_layout = QHBoxLayout(central_widget)
        root_layout.setContentsMargins(0, 0, 0, 0)
        root_layout.setSpacing(0)

        self._create_left_nav_bar(root_layout)

        content_widget = QWidget()
        main_vbox = QVBoxLayout(content_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)

        root_layout.addWidget(content_widget, 1)
        self.setCentralWidget(central_widget)
        
        self._create_top_bar(main_vbox)
        self._create_status_label(main_vbox)
        self._create_main_content(main_vbox)
        self._create_bottom_bar(main_vbox)
        
        self.setMinimumWidth(900)

    def _create_left_nav_bar(self, root_layout):
        """Create collapsible left navigation bar with quick actions."""
        nav_widget = QWidget()
        nav_widget.setObjectName("left_nav_bar")
        self.nav_widget = nav_widget
        self.nav_expanded = False

        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)
        self.nav_layout = nav_layout

        self.nav_toggle_btn = QPushButton()
        self.nav_toggle_btn.setObjectName("nav_toggle_btn")
        self.nav_toggle_btn.setToolTip("Collapse/Expand")
        self.nav_toggle_btn.clicked.connect(self.toggle_left_nav_bar)
        nav_layout.addWidget(self.nav_toggle_btn)

        self.nav_home_btn = QPushButton()
        self.nav_home_btn.setObjectName("nav_icon_btn")
        self.nav_home_btn.setToolTip("Helldivers")
        self.nav_home_btn.clicked.connect(self.show_main_section)
        nav_layout.addWidget(self.nav_home_btn)

        self.nav_slots_btn = QPushButton()
        self.nav_slots_btn.setObjectName("nav_icon_btn")
        self.nav_slots_btn.setToolTip("Slot Layouts")
        self.nav_slots_btn.clicked.connect(self.show_slots_section)
        nav_layout.addWidget(self.nav_slots_btn)

        nav_layout.addStretch(1)

        self.nav_settings_btn = QPushButton()
        self.nav_settings_btn.setObjectName("nav_settings_btn")
        self.nav_settings_btn.setToolTip("Settings")
        self.nav_settings_btn.clicked.connect(self.open_settings)
        nav_layout.addWidget(self.nav_settings_btn)

        root_layout.addWidget(nav_widget)
        self._apply_left_nav_layout_state()
        self._update_left_nav_labels()

    def _apply_left_nav_layout_state(self):
        """Apply width and margins for expanded/collapsed left nav states."""
        if not hasattr(self, "nav_widget"):
            return

        collapsed = not self.nav_expanded
        nav_buttons = [
            self.nav_toggle_btn,
            self.nav_home_btn,
            self.nav_slots_btn,
            self.nav_settings_btn,
        ]
        for btn in nav_buttons:
            btn.setProperty("collapsed", collapsed)
            btn.style().unpolish(btn)
            btn.style().polish(btn)
            btn.update()

        if self.nav_expanded:
            self.nav_widget.setFixedWidth(160)
            if hasattr(self, "nav_layout"):
                self.nav_layout.setContentsMargins(8, 8, 8, 8)
        else:
            self.nav_widget.setFixedWidth(46)
            if hasattr(self, "nav_layout"):
                self.nav_layout.setContentsMargins(8, 8, 8, 8)

    def _update_left_nav_labels(self):
        """Update nav button labels based on expanded/collapsed state."""
        if self.nav_expanded:
            self.nav_toggle_btn.setText("☰  Menu")
            self.nav_home_btn.setText("☠  Helldivers")
            self.nav_slots_btn.setText("⌗  Slots")
            self.nav_settings_btn.setText("⚙  Settings")
        else:
            self.nav_toggle_btn.setText("☰")
            self.nav_home_btn.setText("☠")
            self.nav_slots_btn.setText("⌗")
            self.nav_settings_btn.setText("⚙")

    def toggle_left_nav_bar(self):
        """Collapse or expand left navigation bar."""
        self.nav_expanded = not self.nav_expanded
        self._apply_left_nav_layout_state()
        self._update_left_nav_labels()
        QTimer.singleShot(0, self.update_header_widths)

    def show_main_section(self):
        """Show default commander section."""
        if hasattr(self, "content_stack"):
            self.content_stack.setCurrentIndex(0)
        self._apply_commander_layout_mode()
        if hasattr(self, "top_bar_widget"):
            self.top_bar_widget.show()
        if hasattr(self, "status_label"):
            self.status_label.show()
        if hasattr(self, "status_spacer"):
            self.status_spacer.show()
        self._schedule_main_window_adjust()

    def show_slots_section(self):
        """Show slot layout customization section."""
        if hasattr(self, "content_stack"):
            self.content_stack.setCurrentIndex(1)
        if hasattr(self, "top_bar_widget"):
            self.top_bar_widget.hide()
        if hasattr(self, "status_label"):
            self.status_label.show()
        if hasattr(self, "status_spacer"):
            self.status_spacer.show()
        self._schedule_slots_window_adjust()

    def _schedule_slots_window_adjust(self):
        """Debounced schedule for Slots-window auto-adjust during rapid UI updates."""
        if hasattr(self, "slots_resize_timer"):
            self.slots_resize_timer.start()

    def _schedule_main_window_adjust(self):
        """Debounced schedule for Main-tab auto-adjust when slots may be clipped."""
        if hasattr(self, "main_resize_timer"):
            self.main_resize_timer.start()

    def _auto_adjust_window_for_main_slots(self):
        """Grow window if main-tab slot grid area is clipped by current window size."""
        if not hasattr(self, "content_stack") or not hasattr(self, "grid_container"):
            return
        if self.content_stack.currentIndex() != 0:
            return
        if not hasattr(self, "side_container") or not hasattr(self, "commander_layout"):
            return

        grid_width = self.grid_container.width()
        grid_height = self.grid_container.height()
        side_hint = self.side_container.sizeHint()
        spacing = self.commander_layout.spacing()

        if self.commander_layout.direction() == QBoxLayout.Direction.TopToBottom:
            required_width = max(grid_width, side_hint.width())
            required_height = grid_height + side_hint.height() + max(0, spacing)
        else:
            required_width = grid_width + side_hint.width() + max(0, spacing)
            required_height = max(grid_height, side_hint.height())

        available = self.content_stack.size()
        delta_w = required_width - available.width()
        delta_h = required_height - available.height()

        # Only grow when content is clipped.
        if delta_w <= 0 and delta_h <= 0:
            return

        target_w = self.width() + max(0, delta_w)
        target_h = self.height() + max(0, delta_h)

        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            target_w = min(target_w, geometry.width())
            target_h = min(target_h, geometry.height())

        self.resize(int(target_w), int(target_h))

    def _auto_adjust_window_for_slots_preview(self):
        """Auto-adjust window size to fit slots preview content (grow and shrink)."""
        if not hasattr(self, "content_stack") or not hasattr(self, "slots_customization_widget"):
            return
        if self.content_stack.currentIndex() != 1:
            return

        self.slots_customization_widget.adjustSize()
        required = self.slots_customization_widget.sizeHint()
        available = self.content_stack.size()

        delta_w = required.width() - available.width()
        delta_h = required.height() - available.height()

        # Avoid tiny jitter resizes from sizeHint fluctuations.
        if abs(delta_w) <= 4:
            delta_w = 0
        if abs(delta_h) <= 4:
            delta_h = 0

        if delta_w == 0 and delta_h == 0:
            return

        target_w = self.width() + delta_w
        target_h = self.height() + delta_h

        min_height = max(self.minimumHeight(), self.minimumSizeHint().height())

        target_w = max(self.minimumWidth(), int(target_w))
        target_h = max(min_height, int(target_h))

        # Respect available screen geometry.
        screen = self.screen() or QApplication.primaryScreen()
        if screen:
            geometry = screen.availableGeometry()
            target_w = min(target_w, geometry.width())
            target_h = min(target_h, geometry.height())

        self.resize(target_w, target_h)

    def _load_app_icon(self):
        """Load application icon"""
        try:
            icon_path = get_asset_path("icon.ico")
            if os.path.exists(icon_path):
                self.app_icon = QIcon(icon_path)
                self.setWindowIcon(self.app_icon)
            else:
                self.app_icon = None
        except Exception:
            self.app_icon = None

    def _create_top_bar(self, main_layout):
        """Create top bar with settings and profile controls"""
        top_bar = QWidget()
        self.top_bar_widget = top_bar
        top_bar.setObjectName("top_bar")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(8, 6, 8, 6)
        top_bar_layout.setSpacing(8)
        
        left_sidebar = QVBoxLayout()
        left_sidebar.setContentsMargins(8, 8, 0, 8)
        
        self.speed_btn = QPushButton(f"Latency: {self.global_settings.get('latency', 20)}ms")
        self.speed_btn.setObjectName("speed_btn")
        self.speed_btn.clicked.connect(self.open_settings)
        
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setObjectName("speed_slider")
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(self.global_settings.get("latency", 20))
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        self.speed_slider.valueChanged.connect(self.on_change)
        self.speed_slider.setVisible(False)
        
        left_sidebar.addWidget(self.speed_btn)
        top_bar_layout.addLayout(left_sidebar)
        
        right_sidebar = QVBoxLayout()
        right_sidebar.setContentsMargins(0, 8, 8, 8)
        
        btn_import = QPushButton("")
        btn_export = QPushButton("")
        import_icon_path = get_asset_path("import.svg")
        export_icon_path = get_asset_path("export.svg")
        if os.path.exists(import_icon_path):
            btn_import.setIcon(QIcon(import_icon_path))
        if os.path.exists(export_icon_path):
            btn_export.setIcon(QIcon(export_icon_path))
        btn_import.setIconSize(QSize(18, 18))
        btn_export.setIconSize(QSize(18, 18))

        self.profile_box = DeletableComboBox()
        self.profile_box.setObjectName("profile_box_styled")
        self.profile_box.currentIndexChanged.connect(self.profile_changed)
        self.profile_box.deleteRequested.connect(self.delete_profile_from_select)

        profile_row = QHBoxLayout()
        profile_row.setSpacing(6)
        profile_row.addStretch(1)
        profile_row.addWidget(btn_import)
        profile_row.addWidget(btn_export)
        profile_row.addWidget(self.profile_box, 1)
        right_sidebar.addLayout(profile_row)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        btn_layout.addStretch(1)
        
        self.undo_btn = QPushButton("↶")
        self.save_btn = QPushButton("💾")
        btn_test = QPushButton("🧪")
        btn_clear = QPushButton("🗑️")
        
        buttons = [
            (self.undo_btn, "Undo Changes", self.undo_changes),
            (self.save_btn, "Save Profile", self.manual_save),
            (btn_test, "Test Mode", lambda: TestEnvironment().exec()),
            (btn_clear, "Clear", self.confirm_clear)
        ]
        
        for btn, tooltip, handler in buttons:
            btn.setToolTip(tooltip)
            btn.setProperty("role", "action")
            btn.clicked.connect(handler)
            btn_layout.addWidget(btn)

        btn_import.setToolTip("Import Profile")
        btn_import.setProperty("role", "action")
        btn_import.clicked.connect(self.import_profile)
        btn_import.setFixedSize(40, 40)

        btn_export.setToolTip("Export Profile")
        btn_export.setProperty("role", "action")
        btn_export.clicked.connect(self.export_profile)
        btn_export.setFixedSize(40, 40)
        
        self.update_undo_state()
        right_sidebar.addLayout(btn_layout)
        top_bar_layout.addLayout(right_sidebar)
        main_layout.addWidget(top_bar)

    def _create_status_label(self, main_layout):
        """Create status message label"""
        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        main_layout.addWidget(self.status_label)
        self.status_spacer = QWidget()
        self.status_spacer.setFixedHeight(6)
        main_layout.addWidget(self.status_spacer)

    def _create_main_content(self, main_layout):
        """Create main commander content section."""
        self.content_stack = QStackedWidget()

        commander_widget = QWidget()
        self.commander_layout = QBoxLayout(QBoxLayout.Direction.LeftToRight, commander_widget)
        self.commander_layout.setContentsMargins(0, 0, 0, 0)
        self.commander_layout.setSpacing(0)
        self._create_sidebar(self.commander_layout)
        self._create_numpad_grid(self.commander_layout)
        self._apply_commander_layout_mode()
        self.content_stack.addWidget(commander_widget)

        slots_widget = self._create_slots_customization_section()
        self.content_stack.addWidget(slots_widget)

        main_layout.addWidget(self.content_stack)

    def _should_use_vertical_commander_layout(self):
        """Return True when slots should appear above list on main tab."""
        definition = self.slot_layouts.get(self.active_slot_layout_name, {})
        if definition.get("type") != "grid":
            return False

        rows, cols = self._clamp_picker_size(
            definition.get("rows", 1),
            definition.get("cols", 1),
        )
        # Short-and-wide layouts should stack vertically: slots on top, list below.
        return rows < 3 and cols > rows

    def _apply_commander_layout_mode(self):
        """Apply main-tab layout orientation/order based on active slot layout dimensions."""
        if not hasattr(self, "commander_layout"):
            return
        if not hasattr(self, "side_container") or not hasattr(self, "grid_container"):
            return

        vertical_mode = self._should_use_vertical_commander_layout()
        desired_direction = (
            QBoxLayout.Direction.TopToBottom
            if vertical_mode
            else QBoxLayout.Direction.LeftToRight
        )
        self.commander_layout.setDirection(desired_direction)

        while self.commander_layout.count():
            self.commander_layout.takeAt(0)

        if vertical_mode:
            self.commander_layout.addWidget(self.grid_container, 0, Qt.AlignmentFlag.AlignHCenter)
            self.commander_layout.addWidget(self.side_container, 1)
        else:
            self.commander_layout.addWidget(self.side_container, 1)
            self.commander_layout.addWidget(self.grid_container, 0)

        # Recompute header widths after Qt finishes relayout, so department headers
        # always span the full visible list width.
        QTimer.singleShot(0, self.update_header_widths)
        QTimer.singleShot(60, self.update_header_widths)
        self._schedule_main_window_adjust()

    def _create_plugins_main_section(self):
        """Create plugin management section shown from left navigation."""
        plugins_widget = QWidget()
        layout = QVBoxLayout(plugins_widget)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(10)

        self.plugins_section_stack = QStackedWidget()

        list_page = QWidget()
        list_layout = QVBoxLayout(list_page)
        list_layout.setContentsMargins(0, 0, 0, 0)
        list_layout.setSpacing(8)

        title = QLabel("Installed Plugins")
        title.setStyleSheet("font-weight: bold; color: #ddd;")
        list_layout.addWidget(title)

        self.plugins_main_list = QListWidget()
        self.plugins_main_list.setObjectName("plugins_main_list")
        list_layout.addWidget(self.plugins_main_list, 1)

        list_actions = QHBoxLayout()
        refresh_btn = QPushButton("Refresh Plugins")
        refresh_btn.setMinimumWidth(170)
        refresh_btn.setMaximumWidth(220)
        refresh_btn.setFixedHeight(34)
        refresh_btn.setStyleSheet("font-size: 10px; padding: 4px 8px;")
        refresh_btn.clicked.connect(self.refresh_main_plugins_page)
        list_actions.addWidget(refresh_btn)

        open_create_btn = QPushButton("Create Plugin")
        open_create_btn.setMinimumWidth(170)
        open_create_btn.setMaximumWidth(220)
        open_create_btn.setFixedHeight(34)
        open_create_btn.setStyleSheet("font-size: 10px; padding: 4px 8px;")
        open_create_btn.clicked.connect(self.show_plugin_creator_view)
        list_actions.addWidget(open_create_btn)
        list_layout.addLayout(list_actions)

        self.plugins_section_stack.addWidget(list_page)

        create_page = QWidget()
        create_layout = QVBoxLayout(create_page)
        create_layout.setContentsMargins(0, 0, 0, 0)
        create_layout.setSpacing(8)

        create_header = QHBoxLayout()
        create_title = QLabel("Create Plugin (Easy UI)")
        create_title.setStyleSheet("font-weight: bold; color: #ddd;")
        create_header.addWidget(create_title)
        create_header.addStretch(1)
        back_btn = QPushButton("Back")
        back_btn.setMinimumWidth(110)
        back_btn.setMaximumWidth(160)
        back_btn.setFixedHeight(34)
        back_btn.setStyleSheet("font-size: 10px; padding: 4px 8px;")
        back_btn.clicked.connect(lambda: self.show_plugins_list_view())
        create_header.addWidget(back_btn)
        create_layout.addLayout(create_header)

        self.create_stratagems_check = QCheckBox("Create Stratagems")
        self.create_stratagems_check.setChecked(False)
        self.create_themes_check = QCheckBox("Create Themes")
        self.create_themes_check.setChecked(False)
        self.create_stratagems_check.toggled.connect(self._update_plugin_creator_visibility)
        self.create_themes_check.toggled.connect(self._update_plugin_creator_visibility)
        self.create_stratagems_check.toggled.connect(self._mark_plugin_creator_dirty)
        self.create_themes_check.toggled.connect(self._mark_plugin_creator_dirty)
        create_layout.addWidget(self.create_stratagems_check)
        create_layout.addWidget(self.create_themes_check)

        form = QFormLayout()
        self.plugin_name_input = QLineEdit()
        self.plugin_name_input.setPlaceholderText("Plugin Name")
        self.plugin_name_input.textChanged.connect(self._mark_plugin_creator_dirty)
        form.addRow("Plugin", self.plugin_name_input)
        create_layout.addLayout(form)

        self.stratagem_creator_widget = QWidget()
        stratagem_layout = QVBoxLayout(self.stratagem_creator_widget)
        stratagem_layout.setContentsMargins(0, 0, 0, 0)
        stratagem_layout.setSpacing(6)

        self.plugin_department_input = QLineEdit()
        self.plugin_department_input.setPlaceholderText("Custom Stratagems")
        self.plugin_department_input.textChanged.connect(self._mark_plugin_creator_dirty)
        stratagem_layout.addWidget(QLabel("Department"))
        stratagem_layout.addWidget(self.plugin_department_input)

        stratagem_layout.addWidget(QLabel("Stratagem Entry"))

        self.stratagem_entries_layout = QVBoxLayout()
        self.stratagem_entries_layout.setContentsMargins(0, 0, 0, 0)
        self.stratagem_entries_layout.setSpacing(6)
        stratagem_layout.addLayout(self.stratagem_entries_layout)

        saved_stratagems_label = QLabel("Saved Stratagems")
        saved_stratagems_label.setStyleSheet("color: #aaa; font-size: 11px;")
        stratagem_layout.addWidget(saved_stratagems_label)

        self.saved_stratagems_list = QListWidget()
        self.saved_stratagems_list.setObjectName("saved_stratagems_list")
        self.saved_stratagems_list.setMaximumHeight(110)
        stratagem_layout.addWidget(self.saved_stratagems_list)

        create_layout.addWidget(self.stratagem_creator_widget)

        self.theme_creator_widget = QWidget()
        theme_form = QFormLayout(self.theme_creator_widget)

        self.plugin_theme_name_input = QLineEdit()
        self.plugin_theme_name_input.setPlaceholderText("My Custom Theme")
        self.plugin_theme_name_input.textChanged.connect(self._mark_plugin_creator_dirty)
        theme_form.addRow("Theme Name", self.plugin_theme_name_input)

        self.plugin_bg_color_input = QLineEdit()
        self.plugin_bg_color_input.setPlaceholderText("#151a18")
        self.plugin_bg_color_input.textChanged.connect(self._mark_plugin_creator_dirty)
        theme_form.addRow("Background", self._create_color_input_with_picker(self.plugin_bg_color_input))

        self.plugin_border_color_input = QLineEdit()
        self.plugin_border_color_input.setPlaceholderText("#2f7a5d")
        self.plugin_border_color_input.textChanged.connect(self._mark_plugin_creator_dirty)
        theme_form.addRow("Border", self._create_color_input_with_picker(self.plugin_border_color_input))

        self.plugin_accent_color_input = QLineEdit()
        self.plugin_accent_color_input.setPlaceholderText("#4bbf8a")
        self.plugin_accent_color_input.textChanged.connect(self._mark_plugin_creator_dirty)
        theme_form.addRow("Accent", self._create_color_input_with_picker(self.plugin_accent_color_input))

        create_layout.addWidget(self.theme_creator_widget)

        create_btn = QPushButton("Create Plugin")
        create_btn.setMinimumWidth(190)
        create_btn.setMaximumWidth(260)
        create_btn.setFixedHeight(36)
        create_btn.setStyleSheet("font-size: 10px; padding: 4px 10px;")
        create_btn.clicked.connect(self.create_plugin_from_main_ui)
        create_layout.addWidget(create_btn)
        create_layout.addStretch(1)

        self.plugins_section_stack.addWidget(create_page)

        layout.addWidget(self.plugins_section_stack)
        self._set_single_stratagem_entry()
        self._refresh_saved_stratagems_preview()
        self._update_plugin_creator_visibility()
        self.show_plugins_list_view()
        self.refresh_main_plugins_page()
        return plugins_widget

    def show_plugin_creator_view(self):
        """Show plugin creation view and hide plugin list."""
        if hasattr(self, "plugins_section_stack"):
            self.plugins_section_stack.setCurrentIndex(1)

    def show_plugins_list_view(self, _checked=False, confirm_unsaved=True, reset_form=True):
        """Show installed plugins list view."""
        if confirm_unsaved and not self._prepare_leave_plugin_creator():
            return False

        if reset_form:
            self.reset_plugin_creator_form()

        if hasattr(self, "plugins_section_stack"):
            self.plugins_section_stack.setCurrentIndex(0)
        return True

    def reset_plugin_creator_mode_defaults(self):
        """Reset create-mode checkboxes to default state when leaving creator."""
        if hasattr(self, "create_stratagems_check"):
            self.create_stratagems_check.setChecked(False)
        if hasattr(self, "create_themes_check"):
            self.create_themes_check.setChecked(False)
        self._update_plugin_creator_visibility()

    def _is_plugin_creator_active(self):
        """Check if plugin creator page is selected."""
        if not hasattr(self, "plugins_section_stack"):
            return False
        return self.plugins_section_stack.currentIndex() == 1

    def _has_unsaved_plugin_creator_changes(self):
        """Detect unsaved input in plugin creator form."""
        if not self._is_plugin_creator_active():
            return False

        if getattr(self, "plugin_creator_dirty", False):
            return True

        if hasattr(self, "create_stratagems_check") and self.create_stratagems_check.isChecked():
            return True
        if hasattr(self, "create_themes_check") and self.create_themes_check.isChecked():
            return True

        text_fields = [
            "plugin_name_input",
            "plugin_department_input",
            "plugin_theme_name_input",
            "plugin_bg_color_input",
            "plugin_border_color_input",
            "plugin_accent_color_input",
        ]
        for field_name in text_fields:
            widget = getattr(self, field_name, None)
            if widget and widget.text().strip():
                return True

        if hasattr(self, "stratagem_entries_layout"):
            for index in range(self.stratagem_entries_layout.count()):
                item = self.stratagem_entries_layout.itemAt(index)
                widget = item.widget() if item else None
                if isinstance(widget, StratagemEntryWidget) and widget.has_any_input():
                    return True

        return False

    def _prepare_leave_plugin_creator(self):
        """Confirm leaving plugin creator when there are unsaved changes."""
        if not self._is_plugin_creator_active():
            return True

        if not self._has_unsaved_plugin_creator_changes():
            return True

        reply = QMessageBox.question(
            self,
            "Unsaved Changes",
            "You have unsaved plugin creation changes. Leave this form?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return False

        self.reset_plugin_creator_form()
        return True

    def reset_plugin_creator_form(self):
        """Clear plugin creator inputs and return to default form state."""
        self.reset_plugin_creator_mode_defaults()

        text_fields = [
            "plugin_name_input",
            "plugin_department_input",
            "plugin_theme_name_input",
            "plugin_bg_color_input",
            "plugin_border_color_input",
            "plugin_accent_color_input",
        ]
        for field_name in text_fields:
            widget = getattr(self, field_name, None)
            if widget:
                widget.clear()

        if hasattr(self, "stratagem_entries_layout"):
            while self.stratagem_entries_layout.count():
                item = self.stratagem_entries_layout.takeAt(0)
                widget = item.widget() if item else None
                if widget:
                    widget.deleteLater()
            self._set_single_stratagem_entry()
        self._refresh_saved_stratagems_preview()
        self.plugin_creator_dirty = False

    def _mark_plugin_creator_dirty(self):
        """Mark plugin creator form as dirty after any user input."""
        self.plugin_creator_dirty = True

    def _create_color_input_with_picker(self, color_input):
        """Create a row widget with a color input and color picker button."""
        container = QWidget()
        row = QHBoxLayout(container)
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(6)
        row.addWidget(color_input, 1)

        pick_btn = QPushButton("")
        pick_btn.setToolTip("Pick color")
        pick_btn.setFixedSize(32, 28)
        pick_btn.clicked.connect(lambda: self._pick_color_for_input(color_input))
        color_input._picker_button = pick_btn
        color_input.textChanged.connect(lambda _=None, input_ref=color_input: self._update_color_picker_button(input_ref))
        self._update_color_picker_button(color_input)
        row.addWidget(pick_btn)

        return container

    def _pick_color_for_input(self, color_input):
        """Open color dialog and write selected color as hex value."""
        start_text = color_input.text().strip() or color_input.placeholderText().strip()
        start_color = QColor(start_text)
        if not start_color.isValid():
            start_color = QColor("#ffffff")

        selected_color = QColorDialog.getColor(start_color, self, "Pick Color")
        if selected_color.isValid():
            color_input.setText(selected_color.name())

    def _update_color_picker_button(self, color_input):
        """Update picker button swatch color from input or placeholder."""
        pick_btn = getattr(color_input, "_picker_button", None)
        if not pick_btn:
            return

        candidate = color_input.text().strip() or color_input.placeholderText().strip()
        qcolor = QColor(candidate)
        if not qcolor.isValid():
            qcolor = QColor("#2b2b2b")

        pick_btn.setStyleSheet(
            f"background-color: {qcolor.name()}; border: 1px solid #555; border-radius: 4px;"
        )

    def _update_plugin_creator_visibility(self):
        """Show/hide stratagem/theme creation sections by selected mode."""
        create_stratagems = self.create_stratagems_check.isChecked() if hasattr(self, "create_stratagems_check") else True
        create_themes = self.create_themes_check.isChecked() if hasattr(self, "create_themes_check") else True

        if hasattr(self, "stratagem_creator_widget"):
            self.stratagem_creator_widget.setVisible(create_stratagems)
        if hasattr(self, "theme_creator_widget"):
            self.theme_creator_widget.setVisible(create_themes)

    def _set_single_stratagem_entry(self):
        """Ensure plugin creator has a single stratagem entry row."""
        if not hasattr(self, "stratagem_entries_layout"):
            return
        while self.stratagem_entries_layout.count():
            item = self.stratagem_entries_layout.takeAt(0)
            widget = item.widget() if item else None
            if widget:
                widget.deleteLater()

        entry = StratagemEntryWidget(self)
        entry.entryUpdated.connect(self._refresh_saved_stratagems_preview)
        entry.entryUpdated.connect(self._mark_plugin_creator_dirty)
        self.stratagem_entries_layout.addWidget(entry)
        self._refresh_saved_stratagems_preview()

    def _refresh_saved_stratagems_preview(self):
        """Refresh small preview list with saved stratagem entries."""
        if not hasattr(self, "saved_stratagems_list"):
            return

        self.saved_stratagems_list.clear()
        if not hasattr(self, "stratagem_entries_layout"):
            return

        for index in range(self.stratagem_entries_layout.count()):
            item = self.stratagem_entries_layout.itemAt(index)
            widget = item.widget() if item else None
            if isinstance(widget, StratagemEntryWidget):
                entry = widget.get_saved_entry()
                if not entry:
                    continue
                name, sequence, svg_path, svg_code = entry
                sequence_text = ",".join(sequence)

                list_item = QListWidgetItem()
                row_widget = QWidget()
                row_layout = QHBoxLayout(row_widget)
                row_layout.setContentsMargins(4, 2, 4, 2)
                row_layout.setSpacing(6)

                icon_label = QLabel()
                icon_label.setFixedSize(16, 16)
                icon = self._build_saved_stratagem_icon(svg_path, svg_code)
                if icon:
                    icon_label.setPixmap(icon.pixmap(16, 16))
                row_layout.addWidget(icon_label)

                text_label = QLabel(f"{name}  [{sequence_text}]")
                text_label.setStyleSheet("color: #ddd;")
                row_layout.addWidget(text_label, 1)

                remove_btn = QToolButton()
                remove_btn.setToolTip("Remove stratagem")
                remove_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))
                remove_btn.setAutoRaise(True)
                remove_btn.clicked.connect(lambda _=False, target=widget: self._remove_saved_stratagem_entry(target))
                row_layout.addWidget(remove_btn)

                self.saved_stratagems_list.addItem(list_item)
                self.saved_stratagems_list.setItemWidget(list_item, row_widget)
                list_item.setSizeHint(row_widget.sizeHint())

        if self.saved_stratagems_list.count() == 0:
            self.saved_stratagems_list.addItem("No saved stratagems yet")

    def _remove_saved_stratagem_entry(self, target_widget):
        """Remove a saved stratagem entry row from the creator form."""
        if not hasattr(self, "stratagem_entries_layout"):
            return

        for index in range(self.stratagem_entries_layout.count()):
            item = self.stratagem_entries_layout.itemAt(index)
            widget = item.widget() if item else None
            if widget is target_widget:
                removed_item = self.stratagem_entries_layout.takeAt(index)
                removed_widget = removed_item.widget() if removed_item else None
                if removed_widget:
                    removed_widget.deleteLater()
                break

        self._refresh_saved_stratagems_preview()

    def _build_saved_stratagem_icon(self, svg_path, svg_code):
        """Build a small icon from svg path or pasted svg code."""
        icon_size = QSize(16, 16)

        if svg_path and os.path.exists(svg_path):
            return QIcon(svg_path)

        if svg_code:
            renderer = QSvgRenderer(QByteArray(svg_code.encode("utf-8")))
            if not renderer.isValid():
                return None

            pixmap = QPixmap(icon_size)
            pixmap.fill(Qt.GlobalColor.transparent)

            painter = QPainter(pixmap)
            renderer.render(painter)
            painter.end()

            return QIcon(pixmap)

        return None

    def refresh_main_plugins_page(self):
        """Refresh plugin list in in-app plugins section."""
        if not hasattr(self, "plugins_main_list"):
            return

        self.plugins_main_list.clear()
        plugins = PluginManager.list_plugins()
        if not plugins:
            self.plugins_main_list.addItem("No plugins installed")
            return

        for plugin in plugins:
            marker = "✓" if plugin.get("enabled", True) else "○"
            self.plugins_main_list.addItem(f"{marker} {plugin.get('name', 'Unknown')} ({plugin.get('id', 'unknown')})")

    def create_plugin_from_main_ui(self):
        """Create plugin JSON using simplified main-section form."""
        plugin_name = self.plugin_name_input.text().strip() if hasattr(self, "plugin_name_input") else ""
        if not plugin_name:
            QMessageBox.warning(self, "Create Plugin", "Plugin name is required.")
            return

        safe_name = "".join(ch for ch in plugin_name if ch.isalnum() or ch in ("-", "_", " ")).strip().replace(" ", "_")
        if not safe_name:
            QMessageBox.warning(self, "Create Plugin", "Plugin name is invalid.")
            return

        create_stratagems = self.create_stratagems_check.isChecked() if hasattr(self, "create_stratagems_check") else True
        create_themes = self.create_themes_check.isChecked() if hasattr(self, "create_themes_check") else True

        if not create_stratagems and not create_themes:
            QMessageBox.warning(self, "Create Plugin", "Select stratagems and/or themes to create.")
            return

        plugin_roots = PluginManager.get_plugin_roots()
        target_dir = plugin_roots[0] if plugin_roots else os.path.abspath("plugins")
        os.makedirs(target_dir, exist_ok=True)

        department = self.plugin_department_input.text().strip() if hasattr(self, "plugin_department_input") else ""
        if not department:
            department = "Custom Stratagems"

        theme_name = self.plugin_theme_name_input.text().strip() if hasattr(self, "plugin_theme_name_input") else ""
        if not theme_name:
            theme_name = f"{plugin_name} Theme"

        bg_color = self.plugin_bg_color_input.text().strip() if hasattr(self, "plugin_bg_color_input") else ""
        border_color = self.plugin_border_color_input.text().strip() if hasattr(self, "plugin_border_color_input") else ""
        accent_color = self.plugin_accent_color_input.text().strip() if hasattr(self, "plugin_accent_color_input") else ""

        plugin_data = {
            "id": safe_name.lower(),
            "name": plugin_name,
            "enabled": True,
        }

        if create_stratagems:
            saved_entries = []
            if hasattr(self, "stratagem_entries_layout"):
                for index in range(self.stratagem_entries_layout.count()):
                    item = self.stratagem_entries_layout.itemAt(index)
                    widget = item.widget() if item else None
                    if isinstance(widget, StratagemEntryWidget):
                        if not widget.has_any_input():
                            continue

                        entry = widget.get_saved_entry()
                        if not entry:
                            if not widget.save_entry():
                                QMessageBox.warning(
                                    self,
                                    "Create Plugin",
                                    f"Stratagem entry {index + 1} must include name, sequence and SVG, then be saved."
                                )
                                return
                            entry = widget.get_saved_entry()

                        if entry:
                            saved_entries.append(entry)

            if not saved_entries:
                QMessageBox.warning(self, "Create Plugin", "Save at least one stratagem entry before creating.")
                return

            icon_overrides = {}
            stratagem_map = {}
            generated_svg_dir = os.path.join(target_dir, "generated_svgs")
            os.makedirs(generated_svg_dir, exist_ok=True)

            for name, sequence, svg_path, svg_code in saved_entries:
                stratagem_map[name] = sequence

                if svg_code:
                    safe_stratagem_name = "".join(
                        ch for ch in name if ch.isalnum() or ch in ("-", "_", " ")
                    ).strip().replace(" ", "_")
                    if not safe_stratagem_name:
                        safe_stratagem_name = "stratagem"
                    generated_svg_name = f"{safe_name}_{safe_stratagem_name}.svg"
                    generated_svg_path = os.path.join(generated_svg_dir, generated_svg_name)
                    try:
                        with open(generated_svg_path, "w", encoding="utf-8") as svg_file:
                            svg_file.write(svg_code)
                    except Exception as e:
                        QMessageBox.warning(self, "Create Plugin", f"Failed writing SVG code file:\n{e}")
                        return

                    icon_overrides[name] = os.path.join("generated_svgs", generated_svg_name)
                else:
                    icon_overrides[name] = svg_path

            plugin_data["stratagems_by_department"] = {
                department: stratagem_map
            }
            plugin_data["icon_overrides"] = icon_overrides

        if create_themes:
            plugin_data["themes"] = [
                {
                    "name": theme_name,
                    "colors": {
                        "background_color": bg_color or "#151a18",
                        "border_color": border_color or "#2f7a5d",
                        "accent_color": accent_color or "#4bbf8a"
                    }
                }
            ]

        target_file = os.path.join(target_dir, f"{safe_name}.json")

        if os.path.exists(target_file):
            overwrite = QMessageBox.question(
                self,
                "Plugin Exists",
                f"{os.path.basename(target_file)} already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if overwrite != QMessageBox.StandardButton.Yes:
                return

        try:
            with open(target_file, "w", encoding="utf-8") as plugin_file:
                json.dump(plugin_data, plugin_file, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Create Plugin", f"Failed writing plugin file:\n{e}")
            return

        self.show_plugins_list_view(confirm_unsaved=False, reset_form=True)
        self.plugin_creator_dirty = False
        self.refresh_main_plugins_page()
        self.show_status("Plugin created", 1800)

    def _create_sidebar(self, content_layout):
        """Create sidebar with search and stratagem icons"""
        side_container = QWidget()
        side_container.setObjectName("search_scroll_container")
        self.side_container = side_container
        
        side = QVBoxLayout(side_container)
        side.setSpacing(0)
        side.setContentsMargins(0, 0, 0, 0)
        side_container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        self.search = QLineEdit()
        self.search.setObjectName("search_input")
        self.search.setPlaceholderText("Search...")
        self.search.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.search.setFixedHeight(32)
        self.search.textChanged.connect(self.filter_icons)
        self.search.textChanged.connect(self.update_search_clear_visibility)
        
        self.search_clear_btn = QToolButton(self.search)
        self.search_clear_btn.setObjectName("search_clear_btn")
        self.search_clear_btn.setText("x")
        self.search_clear_btn.setFixedSize(16, 16)
        self.search_clear_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.search_clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.search_clear_btn.clicked.connect(self.search.clear)
        self.search_clear_btn.hide()
        
        self.search.installEventFilter(self)
        self.update_search_clear_visibility(self.search.text())
        side.addWidget(self.search)
        
        # Add collapse/expand all button
        self.toggle_all_btn = QPushButton("▼ Collapse All")
        self.toggle_all_btn.setObjectName("toggle_all_btn")
        self.toggle_all_btn.setFixedHeight(28)
        self.toggle_all_btn.clicked.connect(self.toggle_all_departments)
        self.toggle_all_collapsed = False  # Track if all are currently collapsed
        self.update_toggle_all_button_state()
        side.addWidget(self.toggle_all_btn)
        
        self.icon_list = QListWidget()
        self.icon_list.setObjectName("icon_list")
        self.icon_list.setViewMode(QListWidget.ViewMode.IconMode)
        self.icon_list.setFlow(QListWidget.Flow.LeftToRight)
        self.icon_list.setWrapping(True)
        self.icon_list.setResizeMode(QListWidget.ResizeMode.Adjust)
        self.icon_list.setMovement(QListWidget.Movement.Static)
        self.icon_list.setSelectionMode(QListWidget.SelectionMode.NoSelection)
        self.icon_list.setSpacing(8)
        self.icon_list.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.icon_list.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.icon_list.installEventFilter(self)
        self.icon_list.viewport().installEventFilter(self)
        
        self.icon_widgets = []
        self.icon_items = []
        self.header_items = []
        
        self._populate_icon_list()
        
        side.addWidget(self.icon_list)
        QTimer.singleShot(100, self.update_header_widths)
        
        content_layout.addWidget(side_container)

    def _populate_icon_list(self):
        """Populate the icon list with stratagems organized by department"""
        for department, stratagems in self.stratagems_by_department.items():
            # Initialize expanded state for this department
            self.department_expanded_state[department] = True
            
            header_item = QListWidgetItem()
            header_container = CollapsibleDepartmentHeader(department, parent_app=self)
            
            header_item.setSizeHint(QSize(800, 32))
            self.icon_list.addItem(header_item)
            self.icon_list.setItemWidget(header_item, header_container)
            self.header_items.append((header_item, header_container, department))
            
            for name in sorted(stratagems.keys()):
                w = DraggableIcon(name)
                item = QListWidgetItem()
                item.setSizeHint(QSize(80, 80))
                # Store department info with the item
                item.stratagem_department = department
                self.icon_list.addItem(item)
                self.icon_list.setItemWidget(item, w)
                self.icon_widgets.append(w)
                self.icon_items.append((item, w))

    def _create_numpad_grid(self, content_layout):
        """Create the numpad grid layout"""
        self.grid_container = QWidget()
        self.grid_container_layout = QVBoxLayout(self.grid_container)
        self.grid_container_layout.setContentsMargins(0, 0, 0, 0)
        self.grid_container_layout.setSpacing(0)
        self.numpad_grid_widget = None
        self.grid_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        content_layout.addWidget(self.grid_container)
        self.apply_slot_layout(self.active_slot_layout_name, show_status=False)

    def _create_slots_customization_section(self):
        """Create slot layout customization page."""
        slots_widget = QWidget()
        self.slots_customization_widget = slots_widget
        layout = QVBoxLayout(slots_widget)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(10)

        title = QLabel("Slot Layout Customization")
        title.setStyleSheet("font-weight: bold; font-size: 14px;")
        layout.addWidget(title)

        subtitle = QLabel("Choose, save, and apply slot grid layouts (up to 21 keys)")
        subtitle.setStyleSheet("color: #aaa; font-size: 11px;")
        layout.addWidget(subtitle)

        self.slot_layout_box = DeletableComboBox()
        self.slot_layout_box.setObjectName("profile_box_styled")
        self.slot_layout_box.currentIndexChanged.connect(self.slot_layout_changed)
        self.slot_layout_box.deleteRequested.connect(self.delete_slot_layout_from_select)

        main_row = QHBoxLayout()
        main_row.setSpacing(18)

        left_panel = QVBoxLayout()
        left_panel.setSpacing(10)

        left_panel.addWidget(self.slot_layout_box)

        self.grid_size_label = QLabel("")
        self.grid_size_label.setStyleSheet("color: #ddd;")
        left_panel.addWidget(self.grid_size_label)

        self.grid_picker_button = QPushButton("Pick Grid Size")
        self.grid_picker_button.setToolTip("Hover to open grid picker")
        self.grid_picker_button.installEventFilter(self)
        left_panel.addWidget(self.grid_picker_button, alignment=Qt.AlignmentFlag.AlignLeft)

        self.grid_picker_hint_label = QLabel("The absolute maximum stratagem in a mission is 20.")
        self.grid_picker_hint_label.setStyleSheet("color: #888; font-size: 10px;")
        left_panel.addWidget(self.grid_picker_hint_label, alignment=Qt.AlignmentFlag.AlignLeft)

        self.save_slot_layout_btn = QPushButton("Save Layout")
        self.save_slot_layout_btn.clicked.connect(self.save_slot_layout_from_picker)
        left_panel.addWidget(self.save_slot_layout_btn, alignment=Qt.AlignmentFlag.AlignLeft)
        left_panel.addStretch(1)

        main_row.addLayout(left_panel, 0)

        right_panel = QVBoxLayout()
        right_panel.setSpacing(8)
        preview_title = QLabel("Layout Preview")
        preview_title.setStyleSheet("font-weight: bold; color: #ddd;")
        right_panel.addWidget(preview_title)

        self.slot_layout_preview = QWidget()
        self.slot_layout_preview_layout = QGridLayout(self.slot_layout_preview)
        self.slot_layout_preview_layout.setContentsMargins(0, 0, 0, 0)
        self.slot_layout_preview_layout.setHorizontalSpacing(10)
        self.slot_layout_preview_layout.setVerticalSpacing(10)
        self.preview_slot_cells = []
        right_panel.addWidget(self.slot_layout_preview, alignment=Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)
        right_panel.addStretch(1)

        main_row.addLayout(right_panel, 1)
        layout.addLayout(main_row, 1)

        self.grid_picker_popup = QWidget(slots_widget)
        self.grid_picker_popup.setObjectName("grid_picker_popup")
        self.grid_picker_popup.setAttribute(Qt.WidgetAttribute.WA_StyledBackground, True)
        self.grid_picker_popup.setStyleSheet(
            "QWidget#grid_picker_popup {"
            "background: #111; border: 1px solid #3a3a3a; border-radius: 8px;"
            "}"
        )
        self.grid_picker_popup.installEventFilter(self)
        picker_layout = QGridLayout(self.grid_picker_popup)
        picker_layout.setContentsMargins(8, 8, 8, 8)
        picker_layout.setHorizontalSpacing(6)
        picker_layout.setVerticalSpacing(6)

        self.grid_picker_cells = []
        for row in range(GRID_PICKER_MAX_ROWS):
            for col in range(GRID_PICKER_MAX_COLS):
                cell = QPushButton("")
                cell.setFixedSize(26, 26)
                cell.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                cell.setProperty("grid_picker_row", row)
                cell.setProperty("grid_picker_col", col)
                cell.installEventFilter(self)
                picker_layout.addWidget(cell, row, col)
                self.grid_picker_cells.append(cell)

        self.grid_picker_popup.adjustSize()
        self.grid_picker_popup.hide()

        self.refresh_slot_layouts_select()
        self._refresh_grid_picker_highlight()
        self._update_grid_size_label()
        self._refresh_slot_layout_preview()
        return slots_widget

    def _position_grid_picker_popup(self):
        """Position floating picker popup below picker button with viewport clamping."""
        if not hasattr(self, "grid_picker_popup") or not hasattr(self, "grid_picker_button"):
            return
        if not hasattr(self, "slots_customization_widget"):
            return

        self.grid_picker_popup.adjustSize()

        popup_size = self.grid_picker_popup.sizeHint()
        button_pos = self.grid_picker_button.mapTo(self.slots_customization_widget, QPoint(0, self.grid_picker_button.height()))

        max_x = max(8, self.slots_customization_widget.width() - popup_size.width() - 8)
        max_y = max(8, self.slots_customization_widget.height() - popup_size.height() - 8)
        x = min(max(8, button_pos.x()), max_x)
        y = min(max(8, button_pos.y()), max_y)
        self.grid_picker_popup.move(x, y)

    def _is_cursor_inside_grid_picker_zone(self):
        """Return True if cursor is over picker button or popup."""
        if not hasattr(self, "grid_picker_button") or not hasattr(self, "grid_picker_popup"):
            return False

        cursor_pos = QCursor.pos()
        button_local = self.grid_picker_button.mapFromGlobal(cursor_pos)
        if self.grid_picker_button.rect().contains(button_local):
            return True

        if self.grid_picker_popup.isVisible():
            popup_local = self.grid_picker_popup.mapFromGlobal(cursor_pos)
            if self.grid_picker_popup.rect().contains(popup_local):
                return True

        return False

    def _hide_grid_picker_popup_if_outside(self):
        """Hide floating picker only after mouse fully leaves picker zone."""
        if not hasattr(self, "grid_picker_popup"):
            return
        if self._is_cursor_inside_grid_picker_zone():
            return

        self.grid_picker_popup.hide()
        self.grid_picker_preview_size = None
        self._refresh_grid_picker_highlight()
        self._update_grid_size_label()
        self._refresh_slot_layout_preview()

    def _schedule_grid_picker_close(self):
        """Schedule delayed picker close to allow button→popup hover transition."""
        if hasattr(self, "grid_picker_close_timer"):
            self.grid_picker_close_timer.start()

    def _cancel_grid_picker_close(self):
        """Cancel pending picker close."""
        if hasattr(self, "grid_picker_close_timer") and self.grid_picker_close_timer.isActive():
            self.grid_picker_close_timer.stop()

    def _update_grid_size_label(self, preview_rows=None, preview_cols=None):
        """Refresh textual display for selected grid size."""
        rows = preview_rows if preview_rows is not None else self.grid_picker_selected_rows
        cols = preview_cols if preview_cols is not None else self.grid_picker_selected_cols
        key_count = rows * cols
        self.grid_size_label.setText(f"Grid: {rows} × {cols} ({key_count} keys)")

    def _refresh_grid_picker_highlight(self):
        """Refresh picker hover/selected colors."""
        if self.grid_picker_preview_size:
            active_rows, active_cols = self.grid_picker_preview_size
        else:
            active_rows, active_cols = self.grid_picker_selected_rows, self.grid_picker_selected_cols

        for cell in self.grid_picker_cells:
            row = int(cell.property("grid_picker_row"))
            col = int(cell.property("grid_picker_col"))
            is_allowed_endpoint = ((row + 1) * (col + 1)) <= MAX_CUSTOM_LAYOUT_KEYS
            selected = row < active_rows and col < active_cols

            if not is_allowed_endpoint:
                cell.setStyleSheet("background: #111111; border: 1px solid #1f1f1f; border-radius: 4px;")
            elif selected:
                cell.setStyleSheet("background: #4bbf8a; border: 1px solid #3a9f72; border-radius: 4px;")
            else:
                cell.setStyleSheet("background: #1a1a1a; border: 1px solid #3a3a3a; border-radius: 4px;")

    def _refresh_slot_layout_preview(self, preview_rows=None, preview_cols=None):
        """Rebuild a compact preview of the current picker selection."""
        if not hasattr(self, "slot_layout_preview_layout"):
            return

        rows = preview_rows if preview_rows is not None else self.grid_picker_selected_rows
        cols = preview_cols if preview_cols is not None else self.grid_picker_selected_cols

        if not hasattr(self, "preview_slot_cells"):
            self.preview_slot_cells = []
        self.preview_slot_cells = []

        selected_name = self.slot_layout_box.currentText() if hasattr(self, "slot_layout_box") else ""
        is_new_layout_mode = selected_name == NEW_LAYOUT_OPTION_LABEL
        editable_mode = is_new_layout_mode or self.active_slot_layout_name != DEFAULT_SLOT_LAYOUT_NAME

        key_bindings = self.pending_layout_key_bindings if isinstance(self.pending_layout_key_bindings, dict) else {}
        cleared_slots = self.pending_cleared_slot_indexes if isinstance(self.pending_cleared_slot_indexes, set) else set()

        while self.slot_layout_preview_layout.count():
            item = self.slot_layout_preview_layout.takeAt(0)
            widget = item.widget()
            if widget:
                widget.deleteLater()

        key_count = rows * cols
        for index in range(key_count):
            row = index // cols
            col = index % cols
            preview_cell = QWidget()
            preview_cell.setFixedSize(82, 82)
            preview_cell.setCursor(Qt.CursorShape.PointingHandCursor if editable_mode else Qt.CursorShape.ArrowCursor)
            preview_cell.setProperty("preview_slot_index", index)
            preview_cell.setProperty("preview_slot_editable", editable_mode)
            preview_cell.installEventFilter(self)

            is_cleared = index in cleared_slots
            if is_cleared:
                preview_cell.setStyleSheet(
                    "QWidget { border: 2px dashed #444; background: transparent; border-radius: 8px; } "
                    "QWidget:hover { border: 2px dashed #444; background: transparent; }"
                )
            else:
                preview_cell.setStyleSheet(
                    "QWidget { border: 2px dashed #444; background: #0a0a0a; border-radius: 8px; "
                    "color: #888; font-weight: bold; } "
                    "QWidget:hover { border: 2px solid #ffcc00; background: #151515; }"
                )

            preview_layout = QVBoxLayout(preview_cell)
            preview_layout.setContentsMargins(0, 0, 0, 0)
            preview_layout.setSpacing(0)

            binding = key_bindings.get(str(index), {}) if isinstance(key_bindings, dict) else {}
            if not is_cleared:
                label_text = str(binding.get("label", str(index + 1)))
                cell_label = QLabel(label_text)
                cell_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
                preview_layout.addWidget(cell_label)

            if is_cleared and editable_mode:
                add_btn = QPushButton("+")
                add_btn.setToolTip("Add keybind")
                add_btn.setFixedSize(26, 26)
                add_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                add_btn.setFlat(True)
                add_btn.setStyleSheet(
                    "font-size: 20px; font-weight: bold; padding: 0px; "
                    "border: none; background: transparent;"
                )
                add_btn.clicked.connect(lambda _checked=False, idx=index: self._assign_key_to_preview_slot(idx))
                preview_layout.addStretch(1)
                preview_layout.addWidget(add_btn, alignment=Qt.AlignmentFlag.AlignCenter)
                preview_layout.addStretch(1)
            elif not is_cleared and editable_mode:
                clear_btn = QPushButton("🗑", preview_cell)
                clear_btn.setToolTip("Clear keybind")
                clear_btn.setFixedSize(20, 20)
                clear_btn.move(58, 4)
                clear_btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)
                clear_btn.setStyleSheet("font-size: 10px; padding: 0px;")
                clear_btn.hide()
                clear_btn.clicked.connect(lambda _checked=False, idx=index: self._clear_preview_slot_keybind(idx))
                preview_cell.clear_btn = clear_btn

            self.preview_slot_cells.append(preview_cell)
            self.slot_layout_preview_layout.addWidget(preview_cell, row, col)

        self.slot_layout_preview.updateGeometry()
        self.slots_customization_widget.updateGeometry()
        self._schedule_slots_window_adjust()

    def _clear_preview_slot_keybind(self, slot_index):
        """Stage clear-keybind action for a preview slot (applies only after Save Layout)."""
        selected_name = self.slot_layout_box.currentText() if hasattr(self, "slot_layout_box") else ""
        is_new_layout_mode = selected_name == NEW_LAYOUT_OPTION_LABEL
        if self.active_slot_layout_name == DEFAULT_SLOT_LAYOUT_NAME and not is_new_layout_mode:
            self.show_status("DEFAULT LAYOUT KEYBINDS CANNOT BE CLEARED")
            return

        if not isinstance(self.pending_cleared_slot_indexes, set):
            self.pending_cleared_slot_indexes = set()

        self.pending_cleared_slot_indexes.add(slot_index)

        if isinstance(self.pending_layout_key_bindings, dict):
            self.pending_layout_key_bindings.pop(str(slot_index), None)

        self.show_status(f"SLOT {slot_index + 1} KEYBIND CLEARED (SAVE LAYOUT TO APPLY)")

        self._refresh_slot_layout_preview()

    def _assign_key_to_preview_slot(self, slot_index):
        """Capture and assign a keyboard key to a preview slot in current custom layout."""
        selected_name = self.slot_layout_box.currentText() if hasattr(self, "slot_layout_box") else ""
        is_new_layout_mode = selected_name == NEW_LAYOUT_OPTION_LABEL

        if self.active_slot_layout_name == DEFAULT_SLOT_LAYOUT_NAME and not is_new_layout_mode:
            self.show_status("DEFAULT LAYOUT KEYS CANNOT BE CHANGED")
            return

        if is_new_layout_mode:
            rows = int(self.grid_picker_selected_rows)
            cols = int(self.grid_picker_selected_cols)
        else:
            layout_definition = self.slot_layouts.get(self.active_slot_layout_name)
            if not isinstance(layout_definition, dict) or layout_definition.get("type") != "grid":
                return
            rows = int(layout_definition.get("rows", 1))
            cols = int(layout_definition.get("cols", 1))

        slot_count = min(rows * cols, MAX_CUSTOM_LAYOUT_KEYS, len(CUSTOM_SLOT_SCAN_CODES))
        if slot_index < 0 or slot_index >= slot_count:
            return

        capture_dialog = KeyCaptureDialog(self)
        if capture_dialog.exec() != QDialog.DialogCode.Accepted:
            return

        scan_code = capture_dialog.captured_scan_code
        key_label = capture_dialog.captured_label
        if not scan_code:
            return

        key_bindings = dict(self.pending_layout_key_bindings) if isinstance(self.pending_layout_key_bindings, dict) else {}

        for existing_index in range(slot_count):
            if existing_index == slot_index:
                continue
            existing_binding = key_bindings.get(str(existing_index), {})
            if isinstance(existing_binding, dict) and str(existing_binding.get("scan_code", "")) == scan_code:
                QMessageBox.warning(
                    self,
                    "Assign Key",
                    f"Key '{key_label}' is already assigned to slot {existing_index + 1}.",
                )
                return

        key_bindings[str(slot_index)] = {
            "scan_code": str(scan_code),
            "label": str(key_label),
        }
        self.pending_layout_key_bindings = key_bindings
        if isinstance(self.pending_cleared_slot_indexes, set):
            self.pending_cleared_slot_indexes.discard(slot_index)
        self._refresh_slot_layout_preview()
        self.show_status(f"SLOT {slot_index + 1} KEY STAGED: {key_label} (SAVE LAYOUT TO APPLY)")

    def refresh_slot_layouts_select(self):
        """Refresh layout combo preserving active selection."""
        if not hasattr(self, "slot_layout_box"):
            return

        current_name = self.active_slot_layout_name
        self.slot_layout_box.blockSignals(True)
        self.slot_layout_box.clear()

        ordered_layouts = [DEFAULT_SLOT_LAYOUT_NAME] + sorted(
            [name for name in self.slot_layouts.keys() if name != DEFAULT_SLOT_LAYOUT_NAME]
        )
        for layout_name in ordered_layouts:
            self.slot_layout_box.addItem(layout_name)
            deletable = layout_name != DEFAULT_SLOT_LAYOUT_NAME
            self.slot_layout_box.setItemDeletable(self.slot_layout_box.count() - 1, deletable)

        self.slot_layout_box.addItem(NEW_LAYOUT_OPTION_LABEL)
        self.slot_layout_box.setItemDeletable(self.slot_layout_box.count() - 1, False)

        target_index = self.slot_layout_box.findText(current_name)
        if target_index < 0:
            target_index = self.slot_layout_box.findText(DEFAULT_SLOT_LAYOUT_NAME)
        if target_index >= 0:
            self.slot_layout_box.setCurrentIndex(target_index)

        self.slot_layout_box.blockSignals(False)
        self._sync_picker_from_active_layout()

    def _sync_picker_from_active_layout(self):
        """Update picker state from currently active layout definition."""
        active_definition = self.slot_layouts.get(self.active_slot_layout_name, {})
        if active_definition.get("type") == "grid":
            rows = int(active_definition.get("rows", 4))
            cols = int(active_definition.get("cols", 4))
            active_bindings = active_definition.get("key_bindings", {}) if isinstance(active_definition, dict) else {}
            self.pending_layout_key_bindings = dict(active_bindings) if isinstance(active_bindings, dict) else {}
            active_cleared_slots = active_definition.get("cleared_slots", []) if isinstance(active_definition, dict) else []
            if not isinstance(active_cleared_slots, list) and isinstance(active_definition, dict):
                active_cleared_slots = active_definition.get("hidden_slots", [])  # backward compatibility
            if isinstance(active_cleared_slots, list):
                self.pending_cleared_slot_indexes = {
                    int(index)
                    for index in active_cleared_slots
                    if isinstance(index, int) or (isinstance(index, str) and index.strip().isdigit())
                }
            else:
                self.pending_cleared_slot_indexes = set()
        else:
            default_preview = self._default_numpad_preview_template()
            rows = int(default_preview.get("rows", 5))
            cols = int(default_preview.get("cols", 4))
            self.pending_layout_key_bindings = dict(default_preview.get("key_bindings", {}))
            self.pending_cleared_slot_indexes = set(default_preview.get("cleared_slots", []))

        self.grid_picker_selected_rows, self.grid_picker_selected_cols = self._clamp_picker_size(rows, cols)

        self.grid_picker_preview_size = None
        self._refresh_grid_picker_highlight()
        self._update_grid_size_label()
        self._refresh_slot_layout_preview()

    def slot_layout_changed(self):
        """Apply selected layout from combo box."""
        if not hasattr(self, "slot_layout_box"):
            return

        selected_name = self._sanitize_layout_name(self.slot_layout_box.currentText())
        if not selected_name:
            return

        if selected_name == NEW_LAYOUT_OPTION_LABEL:
            self.pending_layout_key_bindings = {}
            slot_count = min(
                int(self.grid_picker_selected_rows) * int(self.grid_picker_selected_cols),
                MAX_CUSTOM_LAYOUT_KEYS,
                len(CUSTOM_SLOT_SCAN_CODES),
            )
            self.pending_cleared_slot_indexes = set(range(slot_count))
            self._refresh_slot_layout_preview()
            self.show_status("NEW LAYOUT MODE: SET GRID/KEYS THEN SAVE")
            return

        self.apply_slot_layout(selected_name)
        self._sync_picker_from_active_layout()

    def save_slot_layout_from_picker(self):
        """Save picker dimensions as a named custom layout."""
        rows = int(self.grid_picker_selected_rows)
        cols = int(self.grid_picker_selected_cols)
        key_count = rows * cols
        if key_count < 1 or key_count > MAX_CUSTOM_LAYOUT_KEYS:
            QMessageBox.warning(self, "Save Layout", f"Grid size must be between 1 and {MAX_CUSTOM_LAYOUT_KEYS} keys.")
            return

        selected_name = self._sanitize_layout_name(self.slot_layout_box.currentText()) if hasattr(self, "slot_layout_box") else ""
        creating_new_layout = selected_name == NEW_LAYOUT_OPTION_LABEL

        slot_count = min(rows * cols, MAX_CUSTOM_LAYOUT_KEYS, len(CUSTOM_SLOT_SCAN_CODES))
        staged_cleared_slots = []
        if isinstance(self.pending_cleared_slot_indexes, set):
            staged_cleared_slots = sorted(
                index
                for index in self.pending_cleared_slot_indexes
                if isinstance(index, int) and 0 <= index < slot_count
            )

        assigned_count = slot_count - len(staged_cleared_slots)
        if assigned_count < 1:
            QMessageBox.warning(
                self,
                "Save Layout",
                "Layout must have at least 1 assigned key before saving.",
            )
            return

        if creating_new_layout:
            name, ok = QInputDialog.getText(
                self,
                "Save Layout",
                "Layout name:",
                text="My Layout",
            )
            if not ok:
                return

            clean_name = self._sanitize_layout_name(name)
            if not clean_name:
                QMessageBox.warning(self, "Save Layout", "Layout name is required.")
                return
            if clean_name == DEFAULT_SLOT_LAYOUT_NAME:
                QMessageBox.warning(self, "Save Layout", "The default layout name is reserved.")
                return

            if clean_name in self.slot_layouts:
                overwrite = QMessageBox.question(
                    self,
                    "Overwrite Layout",
                    f"Layout '{clean_name}' already exists. Overwrite it?",
                    QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                    QMessageBox.StandardButton.No,
                )
                if overwrite != QMessageBox.StandardButton.Yes:
                    return
            target_layout_name = clean_name
        else:
            target_layout_name = selected_name
            if target_layout_name in ("", DEFAULT_SLOT_LAYOUT_NAME):
                QMessageBox.warning(
                    self,
                    "Save Layout",
                    "Default layout cannot be overwritten. Select 'New Layout...' to create one.",
                )
                return

        staged_bindings = {}
        if isinstance(self.pending_layout_key_bindings, dict):
            slot_count = min(rows * cols, MAX_CUSTOM_LAYOUT_KEYS, len(CUSTOM_SLOT_SCAN_CODES))
            for key, binding in self.pending_layout_key_bindings.items():
                try:
                    index = int(key)
                except (TypeError, ValueError):
                    continue
                if index < 0 or index >= slot_count:
                    continue
                if not isinstance(binding, dict):
                    continue
                scan_code = str(binding.get("scan_code", "")).strip()
                if not scan_code:
                    continue
                label = str(binding.get("label", "")).strip() or f"Key {index + 1}"
                staged_bindings[str(index)] = {
                    "scan_code": scan_code,
                    "label": label,
                }

        self.slot_layouts[target_layout_name] = {
            "type": "grid",
            "rows": rows,
            "cols": cols,
            "key_bindings": staged_bindings,
            "cleared_slots": staged_cleared_slots,
        }
        self.active_slot_layout_name = target_layout_name
        self._persist_slot_layout_settings()
        self.refresh_slot_layouts_select()
        self.apply_slot_layout(target_layout_name)
        self.show_status("SLOT LAYOUT SAVED")

    def delete_slot_layout_from_select(self, layout_name, _index=None, _user_data=None):
        """Delete a custom slot layout from selector after confirmation."""
        clean_name = self._sanitize_layout_name(layout_name)
        if not clean_name or clean_name in (DEFAULT_SLOT_LAYOUT_NAME, NEW_LAYOUT_OPTION_LABEL):
            return

        reply = QMessageBox.question(
            self,
            "Delete Layout",
            f"Delete layout '{clean_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        self.slot_layouts.pop(clean_name, None)
        if self.active_slot_layout_name == clean_name:
            self.active_slot_layout_name = DEFAULT_SLOT_LAYOUT_NAME

        self._persist_slot_layout_settings()
        self.refresh_slot_layouts_select()
        self.apply_slot_layout(self.active_slot_layout_name)
        self.show_status("SLOT LAYOUT DELETED")

    def apply_slot_layout(self, layout_name, show_status=True):
        """Apply a named slot layout to the main commander grid."""
        clean_name = self._sanitize_layout_name(layout_name)
        if clean_name not in self.slot_layouts:
            clean_name = DEFAULT_SLOT_LAYOUT_NAME

        previous_assignments = {
            code: slot.assigned_stratagem
            for code, slot in self.slots.items()
            if slot.assigned_stratagem
        }

        self.active_slot_layout_name = clean_name
        entries = self._build_slot_entries_for_layout(clean_name)
        self._rebuild_numpad_grid(entries)
        self._apply_commander_layout_mode()

        for code, stratagem in previous_assignments.items():
            if code in self.slots and not getattr(self.slots[code], "is_hidden", False):
                self.slots[code].assign(stratagem)

        self._persist_slot_layout_settings()
        self.on_change()
        if show_status:
            self.show_status(f"LAYOUT APPLIED: {clean_name.upper()}")

    def _rebuild_numpad_grid(self, slot_entries):
        """Rebuild the active slot grid widget from provided entries."""
        self.slots = {}

        if self.numpad_grid_widget is not None:
            self.grid_container_layout.removeWidget(self.numpad_grid_widget)
            self.numpad_grid_widget.deleteLater()

        grid_widget = QWidget()
        grid = QGridLayout(grid_widget)
        grid.setSpacing(12)

        max_row = 0
        max_col = 0
        for entry in slot_entries:
            if len(entry) >= 7:
                scan_code, label, row, col, rowspan, colspan, hidden = entry
            else:
                scan_code, label, row, col, rowspan, colspan = entry
                hidden = False
            slot = NumpadSlot(scan_code, label, self)
            slot.set_hidden(bool(hidden))
            grid.addWidget(slot, row, col, rowspan, colspan)
            self.slots[str(scan_code)] = slot
            max_row = max(max_row, row + rowspan)
            max_col = max(max_col, col + colspan)

        if self.active_slot_layout_name == DEFAULT_SLOT_LAYOUT_NAME:
            grid_widget.setFixedSize(NUMPAD_GRID_WIDTH, NUMPAD_GRID_HEIGHT)
            self.grid_container.setFixedSize(NUMPAD_GRID_WIDTH, NUMPAD_GRID_HEIGHT)
        else:
            cell_width = 82
            cell_height = 82
            spacing = grid.spacing()
            margins = grid.contentsMargins()
            width = (max_col * cell_width) + max(0, max_col - 1) * spacing + margins.left() + margins.right()
            height = (max_row * cell_height) + max(0, max_row - 1) * spacing + margins.top() + margins.bottom()
            grid_widget.setFixedSize(max(140, width), max(140, height))
            self.grid_container.setFixedSize(max(140, width), max(140, height))

        grid_widget.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.numpad_grid_widget = grid_widget
        self.grid_container_layout.addWidget(grid_widget)

    def _create_bottom_bar(self, main_layout):
        """Create bottom bar with macro toggle"""
        bottom_bar = QWidget()
        bottom_bar.setObjectName("bottom_bar")
        bottom_bar_layout = QHBoxLayout(bottom_bar)
        bottom_bar_layout.setContentsMargins(8, 6, 8, 12)
        bottom_bar_layout.setSpacing(8)
        
        self.status_text_label = QLabel("Status: Disabled")
        self.status_text_label.setObjectName("macros_status_label")
        self.status_text_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        bottom_bar_layout.addWidget(self.status_text_label, 1)
        
        self.macros_toggle = QCheckBox("")
        self.macros_toggle.setObjectName("macros_toggle")
        self.macros_toggle.toggled.connect(lambda checked: self.set_macros_enabled(checked))
        bottom_bar_layout.addWidget(self.macros_toggle)
        
        main_layout.addWidget(bottom_bar)

    # Event handlers
    def resizeEvent(self, event):
        """Handle window resize events"""
        super().resizeEvent(event)
        self.update_search_clear_position()
        self.update_search_width()
        self.update_header_widths()
        if hasattr(self, "grid_picker_popup") and self.grid_picker_popup.isVisible():
            self._position_grid_picker_popup()
        if hasattr(self, "content_stack") and self.content_stack.currentIndex() == 0:
            self._schedule_main_window_adjust()

    def eventFilter(self, source, event):
        """Filter events for search bar and icon list"""
        if hasattr(self, "preview_slot_cells") and source in self.preview_slot_cells:
            editable = bool(source.property("preview_slot_editable"))

            if not editable:
                return False

            if event.type() == QEvent.Type.Enter:
                clear_btn = getattr(source, "clear_btn", None)
                if clear_btn is not None:
                    clear_btn.show()
                return False

            if event.type() == QEvent.Type.Leave:
                clear_btn = getattr(source, "clear_btn", None)
                if clear_btn is not None:
                    clear_btn.hide()
                return False

            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                slot_index = source.property("preview_slot_index")
                try:
                    slot_index = int(slot_index)
                except (TypeError, ValueError):
                    return False
                self._assign_key_to_preview_slot(slot_index)
                return True

        if hasattr(self, "grid_picker_button") and source == self.grid_picker_button:
            if event.type() == QEvent.Type.Enter:
                self._cancel_grid_picker_close()
                self._position_grid_picker_popup()
                self.grid_picker_popup.show()
                self.grid_picker_popup.raise_()
                return False

            if event.type() == QEvent.Type.Leave:
                self._schedule_grid_picker_close()
                return False

        if hasattr(self, "grid_picker_popup") and source == self.grid_picker_popup:
            if event.type() == QEvent.Type.Enter:
                self._cancel_grid_picker_close()
                return False

            if event.type() == QEvent.Type.Leave:
                self._schedule_grid_picker_close()
                return False

        if hasattr(self, "grid_picker_cells") and source in self.grid_picker_cells:
            row = int(source.property("grid_picker_row"))
            col = int(source.property("grid_picker_col"))
            is_allowed_endpoint = ((row + 1) * (col + 1)) <= MAX_CUSTOM_LAYOUT_KEYS

            if event.type() == QEvent.Type.Enter:
                self._cancel_grid_picker_close()
                if is_allowed_endpoint:
                    self.grid_picker_preview_size = (row + 1, col + 1)
                    self._update_grid_size_label(row + 1, col + 1)
                    self._refresh_slot_layout_preview(row + 1, col + 1)
                else:
                    self.grid_picker_preview_size = None
                    self._update_grid_size_label()
                    self._refresh_slot_layout_preview()
                self._refresh_grid_picker_highlight()
                return False

            if event.type() == QEvent.Type.MouseButtonPress and event.button() == Qt.MouseButton.LeftButton:
                if not is_allowed_endpoint:
                    return True
                self.grid_picker_selected_rows = row + 1
                self.grid_picker_selected_cols = col + 1
                self.grid_picker_preview_size = None
                self._refresh_grid_picker_highlight()
                self._update_grid_size_label()
                self._refresh_slot_layout_preview()
                if hasattr(self, "grid_picker_popup"):
                    self.grid_picker_popup.hide()
                return True

        if hasattr(self, 'search') and source == self.search and event.type() == QEvent.Type.Resize:
            self.update_search_clear_position()
            if self.search.height() != 32:
                self.search.setFixedHeight(32)
        elif hasattr(self, 'icon_list') and source == self.icon_list and event.type() == QEvent.Type.Resize:
            self.update_header_widths()
        elif (
            hasattr(self, 'icon_list')
            and source == self.icon_list.viewport()
            and event.type() == QEvent.Type.Resize
        ):
            self.update_header_widths()
        return super().eventFilter(source, event)

    def closeEvent(self, event):
        """Handle window close event"""
        if self.has_unsaved_changes():
            reply = QMessageBox.question(
                self, "Unsaved Changes",
                "You have unsaved changes. Close anyway?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if reply != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        
        if self.global_settings.get("minimize_to_tray", False):
            self.hide()
            event.ignore()
        else:
            self.macro_engine.disable()
            event.accept()

    def _autoload_last_profile(self):
        """Autoload the last used profile if enabled"""
        if self.global_settings.get("autoload_profile", False):
            last_profile = self.global_settings.get("last_profile", None)
            if last_profile and last_profile != "Create new profile":
                idx = self.profile_box.findText(last_profile)
                if idx >= 0:
                    self.profile_box.setCurrentIndex(idx)

    # UI update methods
    def update_header_widths(self):
        """Update header item sizes to match the scroll list width"""
        if not hasattr(self, 'header_items') or not hasattr(self, 'icon_list'):
            return
        viewport_width = self.icon_list.viewport().width()
        for header_item, header_container, department in self.header_items:
            header_item.setSizeHint(QSize(max(0, viewport_width), 32))

    def update_search_clear_visibility(self, text):
        """Update search clear button visibility"""
        if not hasattr(self, "search_clear_btn"):
            return
        self.search_clear_btn.setVisible(bool(text))
        self.update_search_clear_position()

    def update_search_clear_position(self):
        """Update search clear button position"""
        if not hasattr(self, "search_clear_btn"):
            return
        from PyQt6.QtWidgets import QStyle
        frame_width = self.search.style().pixelMetric(QStyle.PixelMetric.PM_DefaultFrameWidth)
        btn_size = self.search_clear_btn.sizeHint()
        right_padding = btn_size.width() + 10
        self.search.setTextMargins(8, 0, right_padding, 0)
        x = self.search.rect().right() - frame_width - btn_size.width() - 4
        y = (self.search.rect().height() - btn_size.height()) // 2
        self.search_clear_btn.move(x, y)

    def update_search_width(self):
        """Update search bar width"""
        if not hasattr(self, "icon_list") or not hasattr(self, "search"):
            return
        placeholder_width = self.search.fontMetrics().horizontalAdvance(self.search.placeholderText())
        min_width = placeholder_width + 100
        if hasattr(self, "side_container"):
            self.side_container.setMinimumWidth(min_width)
        self.search.setMinimumWidth(min_width)
        self.search.setFixedHeight(32)

    def show_status(self, text, duration=2500):
        """Show status message"""
        self.status_label.setText(text.upper())
        self.status_label.show()
        self.status_label.raise_()
        QTimer.singleShot(duration, lambda: self.status_label.setText(""))

    def update_speed_label(self, value):
        """Update speed/latency label"""
        self.speed_btn.setText(f"Latency: {value}ms")

    def update_macro_toggle_ui(self):
        """Update macro toggle UI elements"""
        enabled = self.global_settings.get("macros_enabled", False)
        
        if hasattr(self, "macros_toggle"):
            self.macros_toggle.blockSignals(True)
            self.macros_toggle.setChecked(enabled)
            self.macros_toggle.blockSignals(False)
        
        if hasattr(self, "status_text_label"):
            self.status_text_label.setText("Status: Enabled" if enabled else "Status: Disabled")
            self.status_text_label.setProperty("state", "enabled" if enabled else "disabled")
            self.status_text_label.style().unpolish(self.status_text_label)
            self.status_text_label.style().polish(self.status_text_label)

    # Settings and theme methods
    def apply_theme(self, theme_name="Dark (Default)"):
        """Apply theme stylesheet"""
        qss = get_theme_stylesheet(theme_name, self.theme_files)
        if qss:
            self.setStyleSheet(qss)

    def get_available_themes(self):
        """Get all available theme names including plugin themes."""
        return list(self.theme_files.keys())

    def get_theme_source(self, theme_name):
        """Get plugin origin for a theme name, or None for built-in themes."""
        if not hasattr(self, "theme_sources"):
            return None
        return self.theme_sources.get(theme_name)

    def save_global_settings(self):
        """Save global settings"""
        save_settings(self.global_settings)

    def open_settings(self, initial_tab=0):
        """Open settings dialog"""
        if not self._prepare_leave_plugin_creator():
            return
        dlg = SettingsWindow(self, initial_tab=initial_tab)
        if dlg.exec():
            self.show_status("Settings applied.")

    # Profile management methods
    def refresh_profiles(self):
        """Refresh the profile list"""
        self.profile_box.blockSignals(True)
        self.profile_box.clear()
        files = [os.path.splitext(f)[0] for f in os.listdir(PROFILES_DIR) if f.endswith(".json")]
        if not files:
            self.profile_box.addItem("Create new profile")
            self.profile_box.setItemDeletable(0, False)
        else:
            for profile_name in sorted(files):
                self.profile_box.addItem(profile_name)
                self.profile_box.setItemDeletable(self.profile_box.count() - 1, True)
            self.profile_box.addItem("Create new profile")
            self.profile_box.setItemDeletable(self.profile_box.count() - 1, False)
        self.profile_box.blockSignals(False)
        self.profile_changed()

    def delete_profile_from_select(self, profile_name, _index=None, _user_data=None):
        """Delete a profile from profile selector after confirmation."""
        if not isinstance(profile_name, str) or profile_name == "Create new profile":
            return

        reply = QMessageBox.question(
            self,
            "Delete Profile",
            f"Delete profile '{profile_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        profile_path = os.path.join(PROFILES_DIR, f"{profile_name}.json")
        try:
            if os.path.exists(profile_path):
                os.remove(profile_path)
        except Exception as e:
            QMessageBox.warning(self, "Delete Profile", f"Failed to delete profile:\n{e}")
            return

        if self.global_settings.get("last_profile") == profile_name:
            self.global_settings["last_profile"] = ""
            self.save_global_settings()

        self.refresh_profiles()
        self.profile_box.setCurrentText("Create new profile")
        self.show_status("PROFILE DELETED")

    def profile_changed(self):
        """Handle profile change"""
        current = self.profile_box.currentText()
        if current == "Create new profile":
            for slot in self.slots.values():
                slot.clear_slot()
            self.sync_macro_hook_state()
            self.saved_state = None
            self.show_status("FRESH PROFILE READY")
        else:
            self.load_profile(os.path.join(PROFILES_DIR, f"{current}.json"))
            self.show_status(f"LOADED: {current.upper()}")
            # Track last loaded profile for autoload
            self.global_settings["last_profile"] = current
            self.save_global_settings()
        self.update_undo_state()

    def manual_save(self):
        """Manually save current profile"""
        current = self.profile_box.currentText()
        if current == "Create new profile":
            name, ok = QInputDialog.getText(self, "New Profile", "Enter name:")
            if ok and name:
                clean_name = os.path.splitext(name)[0]
                state = self.get_current_state()
                ProfileManager.save_profile(clean_name, state)
                self.refresh_profiles()
                self.profile_box.setCurrentText(clean_name)
                self.show_status("PROFILE SAVED")
            else:
                return
        else:
            state = self.get_current_state()
            ProfileManager.save_profile(current, state)
            self.show_status("PROFILE SAVED")
        self.save_current_state()
        self.update_undo_state()

    def import_profile(self):
        """Import a profile from a JSON file"""
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Import Profile",
            "",
            "Profile Files (*.json)"
        )
        if not file_path:
            return

        data = ProfileManager.load_profile_from_path(file_path)
        if not data:
            QMessageBox.warning(self, "Import Failed", "Invalid or unreadable profile file.")
            return

        suggested_name = os.path.splitext(os.path.basename(file_path))[0].strip()
        if not suggested_name:
            suggested_name = "Imported Profile"

        target_name = suggested_name
        if ProfileManager.profile_exists(target_name):
            reply = QMessageBox.question(
                self,
                "Profile Exists",
                f"A profile named '{target_name}' already exists. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )

            if reply == QMessageBox.StandardButton.Cancel:
                return
            if reply == QMessageBox.StandardButton.No:
                name, ok = QInputDialog.getText(
                    self,
                    "Rename Imported Profile",
                    "Enter a new profile name:",
                    text=target_name
                )
                if not ok or not name.strip():
                    return
                target_name = os.path.splitext(name.strip())[0]

        ProfileManager.save_profile(target_name, data)
        self.refresh_profiles()
        self.profile_box.setCurrentText(target_name)
        self.show_status("PROFILE IMPORTED")
        self.save_current_state()

    def export_profile(self):
        """Export the current profile to a JSON file"""
        current = self.profile_box.currentText()
        default_name = current if current != "Create new profile" else "profile"
        default_name = os.path.splitext(default_name)[0] + ".json"

        file_path, _ = QFileDialog.getSaveFileName(
            self,
            "Export Profile",
            default_name,
            "Profile Files (*.json)"
        )
        if not file_path:
            return

        if not file_path.lower().endswith(".json"):
            file_path += ".json"

        state = self.get_current_state()
        if not ProfileManager.save_profile_to_path(file_path, state):
            QMessageBox.warning(self, "Export Failed", "Could not write the profile file.")
            return

        self.show_status("PROFILE EXPORTED")

    def load_profile(self, path):
        """Load profile from file"""
        for slot in self.slots.values():
            slot.clear_slot()
        
        # Load profile using ProfileManager
        profile_name = os.path.splitext(os.path.basename(path))[0]
        data = ProfileManager.load_profile(profile_name)
        
        if data:
            self.speed_slider.blockSignals(True)
            self.speed_slider.setValue(data.get("speed", 20))
            self.speed_slider.blockSignals(False)
            
            mappings = data.get("mappings", {})
            for code, strat in mappings.items():
                if code in self.slots:
                    self.slots[code].assign(strat)
        
        self.sync_macro_hook_state()
        self.save_current_state()

    # State management methods  
    def get_current_state(self):
        """Get the current state of the profile"""
        return {
            "speed": self.speed_slider.value(),
            "mappings": {k: v.assigned_stratagem for k, v in self.slots.items() if v.assigned_stratagem}
        }

    def save_current_state(self):
        """Save the current state as the saved state"""
        self.saved_state = self.get_current_state()
        self.update_undo_state()

    def has_unsaved_changes(self):
        """Check if there are unsaved changes"""
        if self.saved_state is None:
            current = self.get_current_state()
            return current["speed"] != 20 or bool(current["mappings"])
        current = self.get_current_state()
        return current != self.saved_state

    def update_undo_state(self):
        """Enable/disable undo button based on unsaved changes"""
        if self.undo_btn:
            has_changes = self.has_unsaved_changes()
            self.undo_btn.setEnabled(has_changes)
            if has_changes:
                self.undo_btn.setStyleSheet("color: #fff; opacity: 1.0;")
            else:
                self.undo_btn.setStyleSheet("color: #555; opacity: 0.5; border: 1px solid #333;")
            
            if hasattr(self, "save_btn") and self.save_btn:
                border_color = "#ff4444" if has_changes else "#3ddc84"
                self.save_btn.setStyleSheet(
                    f"QPushButton {{ border: 2px solid {border_color}; border-radius: 6px; }}"
                )

    def on_change(self):
        """Called when any change is made"""
        self.update_undo_state()

    def undo_changes(self):
        """Undo changes to the last saved state"""
        if self.saved_state is None:
            # Fresh profile - clear everything
            for slot in self.slots.values():
                slot.clear_slot()
            self.speed_slider.blockSignals(True)
            self.speed_slider.setValue(20)
            self.speed_slider.blockSignals(False)
        else:
            # Restore to saved state
            for slot in self.slots.values():
                slot.clear_slot()
            speed = self.saved_state.get("speed", 20)
            mappings = self.saved_state.get("mappings", {})
            self.speed_slider.blockSignals(True)
            self.speed_slider.setValue(speed)
            self.speed_slider.blockSignals(False)
            for code, strat in mappings.items():
                if code in self.slots:
                    self.slots[code].assign(strat)
        self.show_status("Changes undone")
        self.update_undo_state()

    def filter_icons(self, text):
        """Filter stratagem icons based on search text"""
        text_lower = text.lower()
        visible_icons = {}
        
        for item, widget in self.icon_items:
            matches = text_lower in widget.name.lower() if text_lower else True
            visible_icons[id(item)] = matches
        
        # If searching, expand all departments automatically
        if text_lower:
            for department in self.department_expanded_state:
                self.department_expanded_state[department] = True
            
            # Update all headers to show expanded state
            for header_item, header_container, department in self.header_items:
                header_container.is_expanded = True
                header_container.update_header_display()
            
            self.toggle_all_collapsed = False
            self.update_toggle_all_button_state()
        
        # First pass: determine which headers have items matching the search
        headers_with_matches = {}
        for item, widget in self.icon_items:
            if hasattr(item, 'stratagem_department'):
                department = item.stratagem_department
                item_id = id(item)
                if item_id in visible_icons and visible_icons[item_id]:
                    if department not in headers_with_matches:
                        headers_with_matches[department] = False
                    headers_with_matches[department] = True
        
        # Second pass: show/hide items and headers
        for i in range(self.icon_list.count()):
            item = self.icon_list.item(i)
            widget = self.icon_list.itemWidget(item)
            
            # Check if this is a department header
            is_header = isinstance(widget, CollapsibleDepartmentHeader)
            
            if is_header:
                # Hide headers when searching, show them when search is empty
                item.setHidden(bool(text_lower))
                continue
            
            # This is an icon
            if hasattr(widget, 'name'):
                item_id = id(item)
                department = item.stratagem_department if hasattr(item, 'stratagem_department') else None
                
                # Check if should be visible based on search filter AND department collapse state
                should_show_by_search = item_id in visible_icons and visible_icons[item_id]
                is_department_expanded = self.department_expanded_state.get(department, True)
                should_show = should_show_by_search and is_department_expanded
                
                item.setHidden(not should_show)

    def update_department_visibility(self, department_name, is_expanded):
        """Update visibility of items in a department based on expanded state"""
        self.department_expanded_state[department_name] = is_expanded
        
        # Re-run filter to update visibility with new collapse state
        self.filter_icons(self.search.text())
        
        # Update button state based on whether all departments are now collapsed or expanded
        all_collapsed = all(not expanded for expanded in self.department_expanded_state.values())
        all_expanded = all(expanded for expanded in self.department_expanded_state.values())
        
        if all_collapsed:
            self.toggle_all_collapsed = True
        elif all_expanded:
            self.toggle_all_collapsed = False
        
        self.update_toggle_all_button_state()

    def toggle_all_departments(self):
        """Toggle all departments between collapsed and expanded"""
        # If all are collapsed, expand them. Otherwise, collapse them.
        new_state = self.toggle_all_collapsed  # If True, we're expanding. If False, we're collapsing.
        
        for department in self.department_expanded_state:
            self.department_expanded_state[department] = new_state
        
        # Update all headers to show the new state
        for header_item, header_container, department in self.header_items:
            header_container.is_expanded = new_state
            header_container.update_header_display()
        
        # Toggle the state tracker
        self.toggle_all_collapsed = not self.toggle_all_collapsed
        
        # Update button text
        self.update_toggle_all_button_state()
        
        # Re-filter to update visibility
        self.filter_icons(self.search.text())

    def update_toggle_all_button_state(self):
        """Update the toggle button text based on current state"""
        if hasattr(self, 'toggle_all_btn'):
            if self.toggle_all_collapsed:
                self.toggle_all_btn.setText("▼ Expand All")
            else:
                self.toggle_all_btn.setText("▶ Collapse All")

    def confirm_clear(self):
        """Confirm and clear all slots"""
        reply = QMessageBox.question(
            self, 'Reset', 'Clear Slots?',
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        if reply == QMessageBox.StandardButton.Yes:
            for slot in self.slots.values():
                slot.clear_slot()
            self.show_status("GRID CLEARED")

    # Macro functionality
    def set_macros_enabled(self, enabled, notify=True):
        """Enable or disable macros"""
        self.global_settings["macros_enabled"] = bool(enabled)
        self.save_global_settings()
        
        if enabled:
            self.macro_engine.enable()
            if notify:
                self.show_status("Macros enabled")
        else:
            self.macro_engine.disable()
            if notify:
                self.show_status("Macros disabled")
        
        self.update_macro_toggle_ui()
        
        # Update tray manager if it exists
        if hasattr(self, 'tray_manager'):
            self.tray_manager.update_state(enabled)

    def sync_macro_hook_state(self, notify=False):
        """Sync macro hook state with settings"""
        self.set_macros_enabled(self.global_settings.get("macros_enabled", False), notify=notify)
    
    def map_direction_to_key(self, direction):
        """Map stratagem direction to actual key based on user setting"""
        keybind_mode = self.global_settings.get("keybind_mode", "arrows")

        mapping = KEYBIND_MAPPINGS.get(keybind_mode, KEYBIND_MAPPINGS["arrows"])

        return mapping.get(direction, direction)
    
    def on_macro_triggered(self, scan_code):
        """Callback when a macro is triggered by the macro engine"""
        slot = self.slots.get(str(scan_code))
        if slot and slot.assigned_stratagem:
            stratagem_name = slot.assigned_stratagem
            seq = self.stratagems.get(stratagem_name)
            if seq:
                slot.run_macro(stratagem_name, seq, slot.label_text)
    
    def _show_window(self):
        """Show and activate the main window"""
        self.showNormal()
        self.activateWindow()
        self.raise_()

    def quit_application(self):
        """Quit the application"""
        self.macro_engine.disable()
        QApplication.quit()
    
    def check_for_updates_startup(self):
        """Check for updates on startup"""
        check_for_updates_startup(self, self.global_settings)


def main():
    """Main application entry point"""
    from src.config.config import is_admin, run_as_admin
    
    settings = load_settings()
    require_admin = settings.get("require_admin", False)
    
    if require_admin and not is_admin():
        reply = ctypes.windll.user32.MessageBoxW(
            None,
            "This application is configured to require administrator privileges.\nRestart with administrator privileges?",
            "Administrator Privileges Required",
            0x00000004 | 0x00000020,
        )
        if reply == 6:
            if run_as_admin():
                sys.exit(0)
            else:
                ctypes.windll.user32.MessageBoxW(
                    None,
                    "Failed to elevate privileges. Continuing without admin rights.",
                    "Error",
                    0x00000000 | 0x00000010,
                )
    
    app = QApplication(sys.argv)
    ex = StratagemApp()
    ex.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
