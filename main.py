import sys
import os
import ctypes
import json

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, QLabel,
                             QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, QComboBox,
                             QMessageBox, QListWidget, QToolButton, QCheckBox,
                             QSizePolicy, QListWidgetItem, QSlider, QInputDialog,
                             QFileDialog, QStackedWidget, QFormLayout, QDialog,
                             QPlainTextEdit, QStyle, QColorDialog)
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize, pyqtSignal, QByteArray
from PyQt6.QtGui import QIcon, QPixmap, QPainter, QColor
from PyQt6.QtSvg import QSvgRenderer

from src.config import (PROFILES_DIR, ASSETS_DIR, get_theme_stylesheet, load_settings, 
                       save_settings, get_asset_path, set_icon_overrides)
from src.config.constants import NUMPAD_LAYOUT, THEME_FILES
from src.core.stratagem_data import STRATAGEMS_BY_DEPARTMENT as BASE_STRATAGEMS_BY_DEPARTMENT
from src.config.version import VERSION, APP_NAME
from src.ui.dialogs import TestEnvironment, SettingsWindow
from src.ui.widgets import DraggableIcon, NumpadSlot, comm, CollapsibleDepartmentHeader
from src.managers.profile_manager import ProfileManager
from src.managers.plugin_manager import PluginManager
from src.core.macro_engine import MacroEngine
from src.ui.tray_manager import TrayManager
from src.managers.update_manager import check_for_updates_startup


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

        instruction_label = QLabel("Press Arrow Keys or WASD to record input")
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
        """Capture arrow and WASD keys as sequence input."""
        key_map = {
            Qt.Key.Key_Up: "up",
            Qt.Key.Key_Down: "down",
            Qt.Key.Key_Left: "left",
            Qt.Key.Key_Right: "right",
            Qt.Key.Key_W: "up",
            Qt.Key.Key_S: "down",
            Qt.Key.Key_A: "left",
            Qt.Key.Key_D: "right",
        }

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

    def _load_runtime_plugin_data(self):
        """Load merged runtime plugin data into app state."""
        runtime_data = PluginManager.build_runtime_data(BASE_STRATAGEMS_BY_DEPARTMENT, THEME_FILES)
        self.stratagems_by_department = runtime_data["stratagems_by_department"]
        self.stratagems = runtime_data["stratagems"]
        self.theme_files = runtime_data["theme_files"]
        self.theme_sources = runtime_data.get("theme_sources", {})
        self.loaded_plugins = runtime_data["loaded_plugins"]
        set_icon_overrides(runtime_data["icon_overrides"])

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
        self.show_status("Plugins applied and reloaded", 2200)

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
        nav_widget.setFixedWidth(160)
        self.nav_widget = nav_widget
        self.nav_expanded = True

        nav_layout = QVBoxLayout(nav_widget)
        nav_layout.setContentsMargins(8, 8, 8, 8)
        nav_layout.setSpacing(8)

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

        self.nav_plugins_btn = QPushButton()
        self.nav_plugins_btn.setObjectName("nav_icon_btn")
        self.nav_plugins_btn.setToolTip("Plugins")
        self.nav_plugins_btn.clicked.connect(self.show_plugins_section)
        nav_layout.addWidget(self.nav_plugins_btn)

        nav_layout.addStretch(1)

        self.nav_settings_btn = QPushButton()
        self.nav_settings_btn.setObjectName("nav_settings_btn")
        self.nav_settings_btn.setToolTip("Settings")
        self.nav_settings_btn.clicked.connect(self.open_settings)
        nav_layout.addWidget(self.nav_settings_btn)

        root_layout.addWidget(nav_widget)
        self._update_left_nav_labels()

    def _update_left_nav_labels(self):
        """Update nav button labels based on expanded/collapsed state."""
        if self.nav_expanded:
            self.nav_toggle_btn.setText("☰  Menu")
            self.nav_home_btn.setText("☠  Helldivers")
            self.nav_plugins_btn.setText("🔌  Plugins")
            self.nav_settings_btn.setText("⚙  Settings")
        else:
            self.nav_toggle_btn.setText("☰")
            self.nav_home_btn.setText("☠")
            self.nav_plugins_btn.setText("🔌")
            self.nav_settings_btn.setText("⚙")

    def toggle_left_nav_bar(self):
        """Collapse or expand left navigation bar."""
        self.nav_expanded = not self.nav_expanded
        target_width = 160 if self.nav_expanded else 46
        if hasattr(self, "nav_widget"):
            self.nav_widget.setFixedWidth(target_width)
        self._update_left_nav_labels()
        QTimer.singleShot(0, self.update_header_widths)

    def show_main_section(self):
        """Show default commander section."""
        if not self._prepare_leave_plugin_creator():
            return

        if self._macro_forced_by_plugins:
            previous_enabled = bool(self._macro_state_before_plugins)
            self.set_macros_enabled(previous_enabled, notify=False)
            self._macro_forced_by_plugins = False
            self._macro_state_before_plugins = None

        if hasattr(self, "macros_toggle"):
            self.macros_toggle.setEnabled(True)

        if hasattr(self, "content_stack"):
            self.content_stack.setCurrentIndex(0)
        if hasattr(self, "top_bar_widget"):
            self.top_bar_widget.show()
        if hasattr(self, "status_label"):
            self.status_label.show()
        if hasattr(self, "status_spacer"):
            self.status_spacer.show()

    def show_plugins_section(self):
        """Show in-app plugins section and refresh its list."""
        if not self.show_plugins_list_view(confirm_unsaved=True, reset_form=False):
            return

        if not self._macro_forced_by_plugins:
            self._macro_state_before_plugins = self.global_settings.get("macros_enabled", False)

        self.set_macros_enabled(False, notify=False)
        self._macro_forced_by_plugins = True

        if hasattr(self, "macros_toggle"):
            self.macros_toggle.setEnabled(False)

        if hasattr(self, "content_stack"):
            self.content_stack.setCurrentIndex(1)
        if hasattr(self, "top_bar_widget"):
            self.top_bar_widget.hide()
        if hasattr(self, "status_label"):
            self.status_label.hide()
        if hasattr(self, "status_spacer"):
            self.status_spacer.hide()
        self.refresh_main_plugins_page()

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

        self.profile_box = QComboBox()
        self.profile_box.setObjectName("profile_box_styled")
        self.profile_box.currentIndexChanged.connect(self.profile_changed)

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
        """Create switchable main content sections (commander/plugins)."""
        self.content_stack = QStackedWidget()

        commander_widget = QWidget()
        commander_layout = QHBoxLayout(commander_widget)
        commander_layout.setContentsMargins(0, 0, 0, 0)
        commander_layout.setSpacing(0)
        self._create_sidebar(commander_layout)
        self._create_numpad_grid(commander_layout)
        self.content_stack.addWidget(commander_widget)

        plugins_widget = self._create_plugins_main_section()
        self.content_stack.addWidget(plugins_widget)

        main_layout.addWidget(self.content_stack)

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
        grid = QGridLayout()
        grid.setSpacing(12)
        
        for scan_code, label, row, col, rowspan, colspan in NUMPAD_LAYOUT:
            slot = NumpadSlot(scan_code, label, self)
            grid.addWidget(slot, row, col, rowspan, colspan)
            self.slots[scan_code] = slot
        
        grid_container = QWidget()
        grid_container.setLayout(grid)
        grid_container.setFixedSize(396, 498)
        grid_container.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        
        content_layout.addWidget(grid_container)

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

    def eventFilter(self, source, event):
        """Filter events for search bar and icon list"""
        if hasattr(self, 'search') and source == self.search and event.type() == QEvent.Type.Resize:
            self.update_search_clear_position()
            if self.search.height() != 32:
                self.search.setFixedHeight(32)
        elif hasattr(self, 'icon_list') and source == self.icon_list and event.type() == QEvent.Type.Resize:
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
        else:
            self.profile_box.addItems(files)
            self.profile_box.addItem("Create new profile")
        self.profile_box.blockSignals(False)
        self.profile_changed()

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
        
        if keybind_mode == "wasd":
            mapping = {"up": "w", "down": "s", "left": "a", "right": "d"}
        else:
            mapping = {"up": "up", "down": "down", "left": "left", "right": "right"}
        
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
