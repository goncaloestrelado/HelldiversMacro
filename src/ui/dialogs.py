"""
Dialog windows for Helldivers Numpad Macros
"""

import json
import os

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                             QPushButton, QSpinBox, QListWidget, QStackedWidget,
                             QComboBox, QCheckBox, QMessageBox, QApplication, QWidget,
                             QInputDialog, QListWidgetItem, QLineEdit, QColorDialog)
from PyQt6.QtCore import Qt, QUrl
from PyQt6.QtGui import QFont, QDesktopServices

from ..config.constants import ARROW_ICONS
from ..config.config import is_admin, run_as_admin
from ..config.version import VERSION, GITHUB_REPO_OWNER, GITHUB_REPO_NAME
from ..managers import update_checker
from ..managers.plugin_manager import PluginManager
from ..managers.update_manager import UpdateDialog, check_for_updates_startup
from ..config.config import get_install_type
from .widgets import DeletableComboBox
from .widgets import comm


class TestEnvironment(QDialog):
    """Test environment dialog for testing macros visually"""
    
    def __init__(self):
        super().__init__()
        self.setObjectName("test_env")
        self.setWindowTitle("Super Earth Training Simulator")
        
        layout = QVBoxLayout(self)
        
        self.key_label = QLabel("SYSTEM ACTIVE - TEST MACROS")
        self.key_label.setObjectName("test_key")
        self.key_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.name_label = QLabel("Waiting for input...")
        self.name_label.setFont(QFont("Arial", 16, QFont.Weight.Bold))
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.arrow_display = QLabel("")
        self.arrow_display.setFont(QFont("Arial", 35))
        self.arrow_display.setObjectName("test_arrow")
        self.arrow_display.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        layout.addWidget(self.key_label)
        layout.addWidget(self.name_label)
        layout.addWidget(self.arrow_display)
        
        comm.update_test_display.connect(self.display_macro)

    def display_macro(self, name, sequence, key_label):
        """Display macro execution in test environment"""
        self.key_label.setText(f"HOTKEY TRIGGERED: [ {key_label} ]")
        self.name_label.setText(f"EXECUTING: {name.upper()}")
        visual_seq = " ".join([ARROW_ICONS.get(m, m) for m in sequence])
        self.arrow_display.setText(visual_seq)


class SettingsDialog(QDialog):
    """Simple latency settings dialog"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("settings_dialog")
        self.parent_app = parent
        self.setWindowTitle("Latency Settings")
        
        layout = QVBoxLayout(self)
        
        label = QLabel("Latency (ms)")
        label.setObjectName("settings_label")
        layout.addWidget(label)
        
        row = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("settings_slider")
        self.slider.setRange(1, 200)
        self.spin = QSpinBox()
        self.spin.setRange(1, 200)
        
        val = self.parent_app.speed_slider.value() if self.parent_app else 20
        self.slider.setValue(val)
        self.spin.setValue(val)
        
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        
        row.addWidget(self.slider)
        row.addWidget(self.spin)
        layout.addLayout(row)
        
        btn_row = QHBoxLayout()
        apply_btn = QPushButton("Apply")
        apply_btn.setObjectName("settings_apply")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("settings_cancel")
        apply_btn.clicked.connect(self.apply_and_close)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addStretch(1)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn)
        layout.addLayout(btn_row)

    def apply_and_close(self):
        """Apply settings and close dialog"""
        if self.parent_app:
            self.parent_app.speed_slider.setValue(self.spin.value())
            self.parent_app.update_speed_label(self.spin.value())
        self.accept()


class PluginGuideDialog(QDialog):
    """Simple customization pack creation guide dialog."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Customization Pack Guide")
        self.setObjectName("plugin_guide_dialog")
        self.setFixedSize(520, 320)

        layout = QVBoxLayout(self)

        title = QLabel("Basic Customization Pack Guide")
        title.setObjectName("settings_label")
        layout.addWidget(title)

        guide = QLabel(
            "1) Open the created JSON file and edit fields like id/name.\n"
            "2) Add stratagems under stratagems_by_department.\n"
            "3) Use only up/down/left/right for sequence directions.\n"
            "4) Add icon_overrides with SVG paths if needed.\n"
            "5) Add themes with colors.background_color/border_color/accent_color.\n"
            "6) Save file and restart app to reload customizations."
        )
        guide.setWordWrap(True)
        guide.setStyleSheet("color: #bbb; font-size: 12px; padding: 8px;")
        layout.addWidget(guide)

        layout.addStretch(1)

        btn_row = QHBoxLayout()
        btn_row.addStretch(1)
        close_btn = QPushButton("Close")
        close_btn.setObjectName("settings_apply")
        close_btn.clicked.connect(self.accept)
        btn_row.addWidget(close_btn)
        layout.addLayout(btn_row)


class PluginListItemWidget(QWidget):
    """Customization list row with checkbox and hover trash button."""

    def __init__(self, display_text, manifest_path, checked, on_delete_callback, parent=None):
        super().__init__(parent)
        self.manifest_path = manifest_path

        layout = QHBoxLayout(self)
        layout.setContentsMargins(4, 2, 4, 2)
        layout.setSpacing(6)

        self.checkbox = QCheckBox(display_text)
        self.checkbox.setChecked(checked)
        self.checkbox.setStyleSheet("color: #ddd;")
        layout.addWidget(self.checkbox, 1)

        self.delete_btn = QPushButton("🗑")
        self.delete_btn.setObjectName("plugin_delete_btn")
        self.delete_btn.setToolTip("Remove customization pack")
        self.delete_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.delete_btn.setFixedSize(24, 24)
        self.delete_btn.setStyleSheet(
            "QPushButton#plugin_delete_btn {"
            " background: transparent; border: 1px solid #444; border-radius: 4px; color: #ddd; }"
            "QPushButton#plugin_delete_btn:hover { border: 1px solid #ff4444; color: #ff4444; }"
        )
        self.delete_btn.hide()
        self.delete_btn.clicked.connect(lambda: on_delete_callback(self.manifest_path, display_text))
        layout.addWidget(self.delete_btn, 0)

    def enterEvent(self, event):
        self.delete_btn.show()
        super().enterEvent(event)

    def leaveEvent(self, event):
        self.delete_btn.hide()
        super().leaveEvent(event)


class SettingsWindow(QDialog):
    """Comprehensive settings window with tabs"""
    
    def __init__(self, parent=None, initial_tab=0):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle("Settings")
        self.setFixedSize(600, 400)
        self.setObjectName("settings_window")
        self.custom_theme_option = "Custom Theme"
        self.initial_settings_state = {}
        
        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        
        content_layout = QHBoxLayout()
        content_layout.setContentsMargins(0, 0, 0, 0)
        content_layout.setSpacing(0)
        
        # Left sidebar with tabs
        self.tab_list = QListWidget()
        self.tab_list.setObjectName("settings_tab_list")
        self.tab_list.setFixedWidth(120)
        self.tab_list.setStyleSheet("background: #0a0a0a; border-right: 1px solid #333;")
        self.tab_list.addItem("Latency")
        self.tab_list.addItem("Controls")
        self.tab_list.addItem("Autoload")
        self.tab_list.addItem("Notifications")
        self.tab_list.addItem("Appearance")
        self.tab_list.addItem("Windows")
        self.tab_list.addItem("Customizations")
        self.tab_list.itemClicked.connect(self.switch_tab)
        content_layout.addWidget(self.tab_list)
        
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("settings_content")
        
        self._create_latency_tab()
        self._create_controls_tab()
        self._create_autoload_tab()
        self._create_notifications_tab()
        self._create_appearance_tab()
        self._create_windows_tab()
        self._create_plugins_tab()
        
        content_layout.addWidget(self.content_stack)
        main_layout.addLayout(content_layout)
        
        # Bottom buttons
        self._create_bottom_buttons(main_layout)

        if self.tab_list.count() > 0:
            initial_index = 0
            if isinstance(initial_tab, int):
                initial_index = max(0, min(initial_tab, self.tab_list.count() - 1))
            self.tab_list.setCurrentRow(initial_index)
            self.content_stack.setCurrentIndex(initial_index)

        self._connect_change_tracking()
        self._set_initial_settings_state()
    
    def _create_latency_tab(self):
        """Create latency settings tab"""
        latency_widget = QWidget()
        latency_layout = QVBoxLayout(latency_widget)
        
        label = QLabel("Latency (ms)")
        label.setObjectName("settings_label")
        latency_layout.addWidget(label)
        
        row = QHBoxLayout()
        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setObjectName("settings_slider")
        self.slider.setRange(1, 200)
        self.spin = QSpinBox()
        self.spin.setRange(1, 200)
        
        val = self.parent_app.global_settings.get("latency", 20) if self.parent_app else 20
        self.slider.setValue(val)
        self.spin.setValue(val)
        
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        
        row.addWidget(self.slider)
        row.addWidget(self.spin)
        latency_layout.addLayout(row)
        
        desc_label = QLabel(
            "Latency controls the delay (in milliseconds) between each keypress\n"
            "when executing stratagems. Lower values = faster execution, higher values = "
            "more reliable on high-ping servers.\nRecommended between 20ms and 30ms."
        )
        desc_label.setObjectName("settings_description")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        latency_layout.addWidget(desc_label)
        
        latency_layout.addStretch(1)
        self.content_stack.addWidget(latency_widget)
    
    def _create_controls_tab(self):
        """Create controls settings tab"""
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        controls_label = QLabel("Stratagem Controls")
        controls_label.setObjectName("settings_label")
        controls_layout.addWidget(controls_label)
        
        keys_label = QLabel("Key Binding:")
        keys_label.setStyleSheet("color: #ddd; padding-top: 8px;")
        controls_layout.addWidget(keys_label)
        
        self.keybind_combo = QComboBox()
        self.keybind_combo.setStyleSheet(
            "background: #1a1a1a; color: #ddd; border: 1px solid #333; padding: 4px;"
        )
        self.keybind_combo.addItem("Arrow Keys (Recommended)", "arrows")
        self.keybind_combo.addItem("WASD Keys", "wasd")
        self.keybind_combo.addItem("ESDF Keys", "esdf")
        
        if self.parent_app:
            keybind_mode = self.parent_app.global_settings.get("keybind_mode", "arrows")
            index = self.keybind_combo.findData(keybind_mode)
            self.keybind_combo.setCurrentIndex(index if index >= 0 else 0)
        
        controls_layout.addWidget(self.keybind_combo)
        
        controls_desc = QLabel(
            "Choose which keys to use for executing stratagems.\n"
            "Arrow Keys (Recommended): Uses ↑↓←→ for stratagem inputs.\n"
            "WASD: Uses W/A/S/D keys for stratagem inputs.\n"
            "ESDF: Uses E/S/D/F keys for stratagem inputs."
        )
        controls_desc.setObjectName("settings_description")
        controls_desc.setWordWrap(True)
        controls_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        controls_layout.addWidget(controls_desc)
        
        controls_layout.addStretch(1)
        self.content_stack.addWidget(controls_widget)
    
    def _create_autoload_tab(self):
        """Create autoload settings tab"""
        autoload_widget = QWidget()
        autoload_layout = QVBoxLayout(autoload_widget)
        
        autoload_label = QLabel("Profile Autoload")
        autoload_label.setObjectName("settings_label")
        autoload_layout.addWidget(autoload_label)
        
        self.autoload_check = QCheckBox("Auto-load last profile on startup")
        self.autoload_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.autoload_check.setChecked(
                self.parent_app.global_settings.get("autoload_profile", False)
            )
        autoload_layout.addWidget(self.autoload_check)
        
        autoload_desc = QLabel(
            "When enabled, the application will automatically load the last profile "
            "you were using when it starts up."
        )
        autoload_desc.setObjectName("settings_description")
        autoload_desc.setWordWrap(True)
        autoload_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        autoload_layout.addWidget(autoload_desc)
        
        autoload_layout.addStretch(1)
        self.content_stack.addWidget(autoload_widget)
    
    def _create_notifications_tab(self):
        """Create notifications settings tab"""
        notif_widget = QWidget()
        notif_layout = QVBoxLayout(notif_widget)
        
        notif_label = QLabel("Notifications")
        notif_label.setObjectName("settings_label")
        notif_layout.addWidget(notif_label)
        
        self.sound_check = QCheckBox("Enable sound notifications")
        self.sound_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.sound_check.setChecked(self.parent_app.global_settings.get("sound_enabled", False))
        notif_layout.addWidget(self.sound_check)
        
        self.visual_check = QCheckBox("Enable visual notifications")
        self.visual_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.visual_check.setChecked(self.parent_app.global_settings.get("visual_enabled", True))
        notif_layout.addWidget(self.visual_check)
        
        notif_desc = QLabel(
            "Show notifications when macro execution completes successfully.\n"
            "Sound notifications play a beep when enabled."
        )
        notif_desc.setObjectName("settings_description")
        notif_desc.setWordWrap(True)
        notif_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        notif_layout.addWidget(notif_desc)
        
        notif_layout.addStretch(1)
        self.content_stack.addWidget(notif_widget)
    
    def _create_appearance_tab(self):
        """Create appearance settings tab"""
        appear_widget = QWidget()
        appear_layout = QVBoxLayout(appear_widget)
        
        appear_label = QLabel("Appearance")
        appear_label.setObjectName("settings_label")
        appear_layout.addWidget(appear_label)
        
        theme_label = QLabel("Theme:")
        theme_label.setStyleSheet("color: #ddd; padding-top: 8px;")
        appear_layout.addWidget(theme_label)
        
        self.theme_combo = DeletableComboBox()
        self.theme_combo.setStyleSheet(
            "background: #1a1a1a; color: #ddd; border: 1px solid #333; padding: 4px;"
        )
        themes = []
        if self.parent_app and hasattr(self.parent_app, "get_available_themes"):
            themes = list(self.parent_app.get_available_themes())
        else:
            themes = ["Dark (Default)", "Dark with Blue Accent", "Dark with Red Accent"]

        for theme_name in themes:
            source_name = self.parent_app.get_theme_source(theme_name) if self.parent_app and hasattr(self.parent_app, "get_theme_source") else None
            is_custom_user_theme = source_name == "User custom"
            self.theme_combo.addItem(theme_name, deletable=is_custom_user_theme)

        if self.custom_theme_option not in themes:
            self.theme_combo.addItem(self.custom_theme_option, deletable=False)
        
        if self.parent_app:
            theme = self.parent_app.global_settings.get("theme", "Dark (Default)")
            idx = self.theme_combo.findText(theme)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
        
        appear_layout.addWidget(self.theme_combo)

        self.theme_source_label = QLabel("")
        self.theme_source_label.setObjectName("theme_source_label")
        self.theme_source_label.setStyleSheet("color: #888; font-size: 10px; padding-top: 2px;")
        appear_layout.addWidget(self.theme_source_label)

        self.custom_theme_widget = QWidget()
        custom_theme_layout = QVBoxLayout(self.custom_theme_widget)
        custom_theme_layout.setContentsMargins(0, 8, 0, 0)
        custom_theme_layout.setSpacing(6)

        custom_theme_label = QLabel("Custom Theme Colors")
        custom_theme_label.setStyleSheet("color: #ddd; font-weight: bold;")
        custom_theme_layout.addWidget(custom_theme_label)

        self.custom_bg_input = QLineEdit("#151a18")
        self.custom_border_input = QLineEdit("#2f7a5d")
        self.custom_accent_input = QLineEdit("#4bbf8a")

        for input_field in (self.custom_bg_input, self.custom_border_input, self.custom_accent_input):
            input_field.setStyleSheet("background: #1a1a1a; color: #ddd; border: 1px solid #333; padding: 4px;")

        custom_theme_layout.addLayout(self._build_color_row("Background", self.custom_bg_input))
        custom_theme_layout.addLayout(self._build_color_row("Border", self.custom_border_input))
        custom_theme_layout.addLayout(self._build_color_row("Accent", self.custom_accent_input))

        custom_theme_hint = QLabel("Choose colors and click Save Custom Theme, then select it from the list.")
        custom_theme_hint.setWordWrap(True)
        custom_theme_hint.setStyleSheet("color: #999; font-size: 10px;")
        custom_theme_layout.addWidget(custom_theme_hint)

        self.save_custom_theme_btn = QPushButton("Save Custom Theme")
        self.save_custom_theme_btn.setObjectName("settings_apply")
        self.save_custom_theme_btn.clicked.connect(self.save_custom_theme_from_ui)
        custom_theme_layout.addWidget(self.save_custom_theme_btn)

        self.custom_theme_widget.hide()
        appear_layout.addWidget(self.custom_theme_widget)

        self.theme_combo.currentTextChanged.connect(self.update_theme_source_label)
        self.theme_combo.currentTextChanged.connect(self.on_theme_changed)
        self.theme_combo.deleteRequested.connect(self.delete_theme_from_select)
        self.update_theme_source_label(self.theme_combo.currentText())
        self.on_theme_changed(self.theme_combo.currentText())
        
        appear_desc = QLabel("Select the color theme for the application. Changes apply immediately.")
        appear_desc.setObjectName("settings_description")
        appear_desc.setWordWrap(True)
        appear_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        appear_layout.addWidget(appear_desc)
        
        appear_layout.addStretch(1)
        self.content_stack.addWidget(appear_widget)

    def update_theme_source_label(self, theme_name):
        """Show origin below theme name for customization-provided themes."""
        if not hasattr(self, "theme_source_label"):
            return

        if theme_name == self.custom_theme_option:
            self.theme_source_label.setText("Create a new custom theme")
            return

        source_name = None
        if self.parent_app and hasattr(self.parent_app, "get_theme_source"):
            source_name = self.parent_app.get_theme_source(theme_name)

        if source_name:
            self.theme_source_label.setText(f"From customization pack: {source_name}")
        else:
            self.theme_source_label.setText("")

    def on_theme_changed(self, theme_name):
        """Toggle custom theme color controls based on selected theme option."""
        if hasattr(self, "custom_theme_widget"):
            self.custom_theme_widget.setVisible(theme_name == self.custom_theme_option)

    def _connect_change_tracking(self):
        """Connect settings controls to Apply button dirty-state tracking."""
        controls = [
            getattr(self, "slider", None),
            getattr(self, "spin", None),
            getattr(self, "keybind_combo", None),
            getattr(self, "autoload_check", None),
            getattr(self, "sound_check", None),
            getattr(self, "visual_check", None),
            getattr(self, "theme_combo", None),
            getattr(self, "minimize_tray_check", None),
            getattr(self, "require_admin_check", None),
            getattr(self, "auto_update_check", None),
            getattr(self, "custom_bg_input", None),
            getattr(self, "custom_border_input", None),
            getattr(self, "custom_accent_input", None),
        ]

        for control in controls:
            if control is None:
                continue
            if isinstance(control, (QSlider, QSpinBox)):
                control.valueChanged.connect(self._mark_settings_changed)
            elif isinstance(control, QComboBox):
                control.currentTextChanged.connect(self._mark_settings_changed)
            elif isinstance(control, QCheckBox):
                control.toggled.connect(self._mark_settings_changed)
            elif isinstance(control, QLineEdit):
                control.textChanged.connect(self._mark_settings_changed)

    def _capture_settings_state(self):
        """Capture current settings form state for dirty checking."""
        return {
            "latency": self.spin.value() if hasattr(self, "spin") else None,
            "keybind_mode": self.keybind_combo.currentData() if hasattr(self, "keybind_combo") else None,
            "autoload_profile": self.autoload_check.isChecked() if hasattr(self, "autoload_check") else None,
            "sound_enabled": self.sound_check.isChecked() if hasattr(self, "sound_check") else None,
            "visual_enabled": self.visual_check.isChecked() if hasattr(self, "visual_check") else None,
            "theme": self.theme_combo.currentText() if hasattr(self, "theme_combo") else None,
            "minimize_to_tray": self.minimize_tray_check.isChecked() if hasattr(self, "minimize_tray_check") else None,
            "require_admin": self.require_admin_check.isChecked() if hasattr(self, "require_admin_check") else None,
            "auto_check_updates": self.auto_update_check.isChecked() if hasattr(self, "auto_update_check") else None,
            "custom_bg": self.custom_bg_input.text().strip() if hasattr(self, "custom_bg_input") else None,
            "custom_border": self.custom_border_input.text().strip() if hasattr(self, "custom_border_input") else None,
            "custom_accent": self.custom_accent_input.text().strip() if hasattr(self, "custom_accent_input") else None,
            "enabled_plugins": sorted(self.get_checked_plugin_manifest_paths()),
        }

    def _set_initial_settings_state(self):
        """Store initial state snapshot and refresh Apply button state."""
        self.initial_settings_state = self._capture_settings_state()
        self._update_apply_button_state()

    def _mark_settings_changed(self, *_args):
        """Handle settings field changes and refresh Apply button state."""
        self._update_apply_button_state()

    def _update_apply_button_state(self):
        """Enable Apply only when current state differs from initial state."""
        if not hasattr(self, "apply_btn"):
            return

        current_state = self._capture_settings_state()
        self.apply_btn.setEnabled(current_state != self.initial_settings_state)

    def save_custom_theme_from_ui(self):
        """Save current custom theme colors using a dedicated button."""
        if self.theme_combo.currentText() != self.custom_theme_option:
            QMessageBox.information(self, "Custom Theme", "Select 'Custom Theme' first.")
            return

        custom_name, ok = QInputDialog.getText(
            self,
            "Save Custom Theme",
            "Theme name:"
        )
        if not ok:
            return

        custom_name = custom_name.strip()
        if not custom_name:
            QMessageBox.warning(self, "Invalid Name", "Please provide a valid custom theme name.")
            return

        existing_themes = []
        if self.parent_app and hasattr(self.parent_app, "get_available_themes"):
            existing_themes = list(self.parent_app.get_available_themes())

        if custom_name in existing_themes:
            overwrite = QMessageBox.question(
                self,
                "Theme Exists",
                f"A theme named '{custom_name}' already exists. Overwrite it?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if overwrite != QMessageBox.StandardButton.Yes:
                return

        custom_colors = {
            "background_color": self.custom_bg_input.text().strip() or "#151a18",
            "border_color": self.custom_border_input.text().strip() or "#2f7a5d",
            "accent_color": self.custom_accent_input.text().strip() or "#4bbf8a",
        }

        if not hasattr(self.parent_app, "save_custom_theme") or not self.parent_app.save_custom_theme(custom_name, custom_colors):
            QMessageBox.warning(self, "Theme Save Failed", "Could not save custom theme.")
            return

        existing_index = self.theme_combo.findText(custom_name)
        if existing_index < 0:
            custom_option_index = self.theme_combo.findText(self.custom_theme_option)
            if custom_option_index >= 0:
                self.theme_combo.insertItem(custom_option_index, custom_name)
                self.theme_combo.setItemDeletable(custom_option_index, True)
            else:
                self.theme_combo.addItem(custom_name, deletable=True)
        else:
            self.theme_combo.setItemDeletable(existing_index, True)

        selected_index = self.theme_combo.findText(custom_name)
        if selected_index >= 0:
            self.theme_combo.setCurrentIndex(selected_index)

        QMessageBox.information(self, "Theme Saved", f"Custom theme '{custom_name}' saved.")
        self._mark_settings_changed()

    def _build_color_row(self, label_text, input_field):
        """Create one color input row with a picker button."""
        row = QHBoxLayout()
        label = QLabel(f"{label_text}:")
        label.setStyleSheet("color: #ddd;")
        row.addWidget(label)
        row.addWidget(input_field, 1)

        pick_button = QPushButton("Pick")
        pick_button.setObjectName("settings_cancel")
        pick_button.clicked.connect(lambda _checked=False, field=input_field: self._pick_color(field))
        row.addWidget(pick_button)
        return row

    def _pick_color(self, target_field):
        """Open color picker and write selected color hex into target field."""
        initial_value = target_field.text().strip() if target_field else ""
        color = QColorDialog.getColor(parent=self)
        if color.isValid():
            target_field.setText(color.name())

    def delete_theme_from_select(self, theme_name, _index=None, _user_data=None):
        """Delete custom theme from theme selector after confirmation."""
        if not isinstance(theme_name, str) or not theme_name.strip():
            return
        if theme_name == self.custom_theme_option:
            return

        source_name = self.parent_app.get_theme_source(theme_name) if self.parent_app and hasattr(self.parent_app, "get_theme_source") else None
        if source_name != "User custom":
            QMessageBox.information(self, "Theme Delete", "Only user custom themes can be deleted here.")
            return

        reply = QMessageBox.question(
            self,
            "Delete Theme",
            f"Delete custom theme '{theme_name}'?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        if not self.parent_app or not hasattr(self.parent_app, "delete_custom_theme"):
            QMessageBox.warning(self, "Theme Delete", "Theme delete is not available.")
            return

        if not self.parent_app.delete_custom_theme(theme_name):
            QMessageBox.warning(self, "Theme Delete", "Could not delete theme.")
            return

        idx = self.theme_combo.findText(theme_name)
        if idx >= 0:
            self.theme_combo.removeItem(idx)

        fallback_idx = self.theme_combo.findText("Dark (Default)")
        if fallback_idx >= 0:
            self.theme_combo.setCurrentIndex(fallback_idx)
        self._mark_settings_changed()
    
    def _create_windows_tab(self):
        """Create windows settings tab"""
        windows_widget = QWidget()
        windows_layout = QVBoxLayout(windows_widget)
        
        windows_label = QLabel("Window Settings")
        windows_label.setObjectName("settings_label")
        windows_layout.addWidget(windows_label)
        
        # Update checking section
        updates_section = QLabel("Updates")
        updates_section.setStyleSheet("color: #ddd; font-weight: bold; padding-top: 15px;")
        windows_layout.addWidget(updates_section)
        
        self.auto_update_check = QCheckBox("Check for updates on startup")
        self.auto_update_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.auto_update_check.setChecked(
                self.parent_app.global_settings.get("auto_check_updates", True)
            )
        windows_layout.addWidget(self.auto_update_check)
        
        check_now_btn = QPushButton("Check for Updates Now")
        check_now_btn.setStyleSheet(
            "background: #2a2a2a; color: #3ddc84; border: 1px solid #3ddc84; "
            "padding: 8px 16px; border-radius: 4px; font-weight: bold;"
        )
        check_now_btn.clicked.connect(self.check_for_updates)
        windows_layout.addWidget(check_now_btn)
        
        version_label = QLabel(f"Current Version: {VERSION}")
        version_label.setStyleSheet("color: #888; font-size: 10px; padding: 5px;")
        windows_layout.addWidget(version_label)
        
        update_desc = QLabel("Automatically check for new versions when the application starts.")
        update_desc.setObjectName("settings_description")
        update_desc.setWordWrap(True)
        update_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        windows_layout.addWidget(update_desc)
        
        windows_layout.addSpacing(15)
        
        self.minimize_tray_check = QCheckBox("Minimize to system tray on close")
        self.minimize_tray_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.minimize_tray_check.setChecked(
                self.parent_app.global_settings.get("minimize_to_tray", False)
            )
        windows_layout.addWidget(self.minimize_tray_check)
        
        windows_desc = QLabel(
            "When enabled, closing the window minimizes the application to the system tray.\n"
            "When disabled, closing the window exits the application."
        )
        windows_desc.setObjectName("settings_description")
        windows_desc.setWordWrap(True)
        windows_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        windows_layout.addWidget(windows_desc)
        
        # Admin privileges checkbox
        self.require_admin_check = QCheckBox("Require administrator privileges")
        self.require_admin_check.setStyleSheet("color: #ddd; padding: 8px; margin-top: 15px;")
        if self.parent_app:
            self.require_admin_check.setChecked(
                self.parent_app.global_settings.get("require_admin", False)
            )
        windows_layout.addWidget(self.require_admin_check)
        
        admin_desc = QLabel(
            "When enabled, the application will request administrator privileges on startup.\n"
            "This is required if Helldivers 2 runs with admin rights. "
            "Application will restart to apply changes."
        )
        admin_desc.setObjectName("settings_description")
        admin_desc.setWordWrap(True)
        admin_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        windows_layout.addWidget(admin_desc)
        
        windows_layout.addStretch(1)
        self.content_stack.addWidget(windows_widget)

    def _create_plugins_tab(self):
        """Create customizations settings tab with list and create action."""
        plugins_widget = QWidget()
        plugins_layout = QHBoxLayout(plugins_widget)
        plugins_layout.setContentsMargins(12, 12, 12, 12)
        plugins_layout.setSpacing(12)

        left_panel = QVBoxLayout()

        create_btn = QPushButton("Create Customization Pack")
        create_btn.setObjectName("settings_apply")
        create_btn.clicked.connect(self.create_plugin_template)
        left_panel.addWidget(create_btn)

        self.plugins_list = QListWidget()
        self.plugins_list.setObjectName("plugins_list")
        self.plugins_list.setMinimumWidth(260)
        left_panel.addWidget(self.plugins_list, 1)

        refresh_btn = QPushButton("Refresh")
        refresh_btn.setObjectName("settings_cancel")
        refresh_btn.clicked.connect(self.refresh_plugin_list)
        left_panel.addWidget(refresh_btn)

        info_label = QLabel(
            "Installed/created customization packs are listed above.\n"
            "Use Create Customization Pack to generate a JSON template file."
        )
        info_label.setWordWrap(True)
        info_label.setStyleSheet("color: #aaa; font-size: 12px;")
        left_panel.addWidget(info_label)

        left_panel.addStretch(1)

        plugins_layout.addLayout(left_panel, 1)

        self.content_stack.addWidget(plugins_widget)
        self.refresh_plugin_list()

    def refresh_plugin_list(self):
        """Refresh list of discovered plugins."""
        if not hasattr(self, "plugins_list"):
            return

        previously_checked = set(getattr(self, "selected_plugin_manifest_paths", []))
        self.selected_plugin_manifest_paths = []
        self.plugins_list.clear()
        plugins = PluginManager.list_plugins()
        if not plugins:
            self.plugins_list.addItem("No customization packs found")
            return

        checked_paths = []
        for plugin in plugins:
            name = plugin.get("name", "Unknown")
            plugin_id = plugin.get("id", "unknown")
            is_enabled = bool(plugin.get("enabled", True))
            manifest_path = plugin.get("manifest_path", "")

            display_text = f"{name} ({plugin_id})"
            item = QListWidgetItem()
            item.setData(Qt.ItemDataRole.UserRole, manifest_path)

            should_check = manifest_path in previously_checked or (not previously_checked and is_enabled)
            self.plugins_list.addItem(item)

            row_widget = PluginListItemWidget(
                display_text=display_text,
                manifest_path=manifest_path,
                checked=should_check,
                on_delete_callback=self.delete_plugin_by_manifest,
                parent=self.plugins_list,
            )
            row_widget.checkbox.toggled.connect(self._mark_settings_changed)
            item.setSizeHint(row_widget.sizeHint())
            self.plugins_list.setItemWidget(item, row_widget)

            if should_check and manifest_path:
                checked_paths.append(manifest_path)

        self.selected_plugin_manifest_paths = checked_paths

    def get_checked_plugin_manifest_paths(self):
        """Collect checked plugin manifests from plugin list."""
        checked_paths = []
        if not hasattr(self, "plugins_list"):
            return checked_paths

        for index in range(self.plugins_list.count()):
            item = self.plugins_list.item(index)
            manifest_path = item.data(Qt.ItemDataRole.UserRole)
            if not manifest_path:
                continue

            row_widget = self.plugins_list.itemWidget(item)
            if isinstance(row_widget, PluginListItemWidget) and row_widget.checkbox.isChecked():
                checked_paths.append(manifest_path)

        self.selected_plugin_manifest_paths = checked_paths
        return checked_paths

    def _sanitize_plugin_filename(self, value):
        """Create safe filename stem from user input."""
        if not isinstance(value, str):
            return ""

        sanitized = "".join(ch for ch in value.strip() if ch.isalnum() or ch in ("-", "_", " "))
        return sanitized.replace(" ", "_")

    def create_plugin_template(self):
        """Prompt for customization template name and create JSON template file."""
        template_name, ok = QInputDialog.getText(self, "Create Customization Pack", "Template name:")
        if not ok:
            return

        file_stem = self._sanitize_plugin_filename(template_name)
        if not file_stem:
            QMessageBox.warning(self, "Invalid Name", "Please enter a valid customization name.")
            return

        plugin_roots = PluginManager.get_plugin_roots()
        target_dir = plugin_roots[0] if plugin_roots else os.path.abspath("plugins")
        os.makedirs(target_dir, exist_ok=True)

        target_file = os.path.join(target_dir, f"{file_stem}.json")
        if os.path.exists(target_file):
            overwrite = QMessageBox.question(
                self,
                "File Exists",
                f"{os.path.basename(target_file)} already exists. Overwrite?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            )
            if overwrite != QMessageBox.StandardButton.Yes:
                return

        template = {
            "id": file_stem.lower(),
            "name": template_name.strip() or file_stem,
            "enabled": True,
            "stratagems_by_department": {
                "Custom Stratagems": {
                    "My Stratagem": ["down", "left", "up", "right"]
                }
            },
            "icon_overrides": {
                "My Stratagem": "icons/my_stratagem.svg"
            },
            "themes": [
                {
                    "name": "My Custom Theme",
                    "colors": {
                        "background_color": "#151a18",
                        "border_color": "#2f7a5d",
                        "accent_color": "#4bbf8a"
                    }
                }
            ]
        }

        try:
            with open(target_file, "w", encoding="utf-8") as f:
                json.dump(template, f, indent=2)
        except Exception as e:
            QMessageBox.warning(self, "Create Failed", f"Could not create plugin template:\n{e}")
            return

        self.refresh_plugin_list()

        open_dir_reply = QMessageBox.question(
            self,
            "Open Directory",
            "Customization template created. Open customization folder directory now?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.Yes,
        )

        if open_dir_reply == QMessageBox.StandardButton.Yes:
            QDesktopServices.openUrl(QUrl.fromLocalFile(target_dir))

        guide = PluginGuideDialog(self)
        guide.exec()

    def delete_plugin_by_manifest(self, manifest_path, plugin_name):
        """Delete a customization pack by manifest path with confirmation."""
        if not manifest_path:
            QMessageBox.information(self, "Delete Customization", "Select a valid customization entry to delete.")
            return

        reply = QMessageBox.question(
            self,
            "Confirm Delete",
            f"Remove customization pack '{plugin_name}'?\nThis will remove its files.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
            QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return

        success, message = PluginManager.uninstall_plugin_by_manifest(manifest_path)
        if not success:
            QMessageBox.warning(self, "Delete Failed", message)
            return

        self.refresh_plugin_list()
        QMessageBox.information(self, "Customization Removed", message)
    
    def _create_bottom_buttons(self, main_layout):
        """Create bottom buttons layout"""
        btn_row = QHBoxLayout()
        
        # Version label on the left (clickable link to releases)
        version_label = QLabel(
            f'<a href="https://github.com/{GITHUB_REPO_OWNER}/{GITHUB_REPO_NAME}/releases" '
            f'style="color: #666; text-decoration: none;">{VERSION}</a>'
        )
        version_label.setStyleSheet("color: #666; font-size: 10px; padding: 0 10px;")
        version_label.setOpenExternalLinks(True)
        version_label.setTextFormat(Qt.TextFormat.RichText)
        version_label.setToolTip("View releases on GitHub")
        btn_row.addWidget(version_label)
        
        btn_row.addStretch(1)
        
        apply_btn = QPushButton("Apply")
        self.apply_btn = apply_btn
        apply_btn.setObjectName("settings_apply")
        cancel_btn = QPushButton("Cancel")
        cancel_btn.setObjectName("settings_cancel")
        apply_btn.clicked.connect(self.apply_and_close)
        cancel_btn.clicked.connect(self.reject)
        btn_row.addWidget(cancel_btn)
        btn_row.addWidget(apply_btn)
        
        main_layout.addLayout(btn_row)
    
    def switch_tab(self, item):
        """Switch between settings tabs"""
        self.content_stack.setCurrentIndex(self.tab_list.row(item))
    
    def check_for_updates(self):
        """Check for updates manually"""
        # Show checking message
        self.sender().setEnabled(False)
        self.sender().setText("Checking...")
        QApplication.processEvents()
        
        result = update_checker.check_for_updates(
            VERSION, GITHUB_REPO_OWNER, GITHUB_REPO_NAME,
            install_type=get_install_type()
        )
        
        self.sender().setEnabled(True)
        self.sender().setText("Check for Updates Now")
        
        if not result['success']:
            QMessageBox.warning(
                self, "Update Check Failed",
                f"Could not check for updates:\n{result['error']}"
            )
            return
        
        if result['has_update']:
            dlg = UpdateDialog(result, self.parent_app)
            dlg.exec()
        else:
            QMessageBox.information(
                self, "No Updates",
                f"You are running the latest version ({VERSION})."
            )
    
    def apply_and_close(self):
        """Apply all settings and close dialog"""
        if not self.parent_app:
            self.accept()
            return
        
        # Save all settings
        latency_value = self.spin.value()
        old_theme = self.parent_app.global_settings.get("theme", "Dark (Default)")
        selected_theme = self.theme_combo.currentText()
        new_theme = selected_theme
        old_require_admin = self.parent_app.global_settings.get("require_admin", False)
        new_require_admin = self.require_admin_check.isChecked()

        if selected_theme == self.custom_theme_option:
            QMessageBox.information(
                self,
                "Save Custom Theme",
                "Use 'Save Custom Theme' to create a named theme, then select it before applying settings."
            )
            return
        
        self.parent_app.speed_slider.setValue(latency_value)
        keybind_mode = self.keybind_combo.currentData() or "arrows"
        
        self.parent_app.global_settings["latency"] = latency_value
        self.parent_app.global_settings["keybind_mode"] = keybind_mode
        self.parent_app.global_settings["autoload_profile"] = self.autoload_check.isChecked()
        self.parent_app.global_settings["sound_enabled"] = self.sound_check.isChecked()
        self.parent_app.global_settings["visual_enabled"] = self.visual_check.isChecked()
        self.parent_app.global_settings["theme"] = new_theme
        self.parent_app.global_settings["minimize_to_tray"] = self.minimize_tray_check.isChecked()
        self.parent_app.global_settings["require_admin"] = new_require_admin
        self.parent_app.global_settings["auto_check_updates"] = self.auto_update_check.isChecked()
        self.parent_app.save_global_settings()
        self.parent_app.update_speed_label(latency_value)
        
        # Apply theme immediately if changed
        if old_theme != new_theme:
            self.parent_app.apply_theme(new_theme)
        
        # Handle admin privilege change
        if old_require_admin != new_require_admin:
            self._handle_admin_privilege_change(new_require_admin)

        checked_manifest_paths = self.get_checked_plugin_manifest_paths()
        if hasattr(self.parent_app, "apply_plugin_manifest_selection"):
            self.parent_app.apply_plugin_manifest_selection(checked_manifest_paths)
        
        self.accept()
    
    def _handle_admin_privilege_change(self, new_require_admin):
        """Handle changes to admin privilege requirement"""
        if new_require_admin and not is_admin():
            # Need admin but not running as admin - restart with admin
            reply = QMessageBox.question(
                self, "Restart Required",
                "Application needs to restart with administrator privileges.\nRestart now?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                if run_as_admin():
                    QApplication.quit()
                else:
                    QMessageBox.warning(
                        self, "Error",
                        "Failed to elevate privileges. Please run as administrator manually."
                    )
        elif not new_require_admin and is_admin():
            # No longer need admin but running as admin - inform user
            QMessageBox.information(
                self, "Restart Recommended",
                "To run without administrator privileges, please restart the application normally."
            )
