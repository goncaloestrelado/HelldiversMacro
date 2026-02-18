"""
Dialog windows for Helldivers Numpad Macros
"""

from PyQt6.QtWidgets import (QDialog, QVBoxLayout, QHBoxLayout, QLabel, QSlider,
                             QPushButton, QSpinBox, QListWidget, QStackedWidget,
                             QComboBox, QCheckBox, QMessageBox, QApplication, QWidget)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont

from ..config.constants import ARROW_ICONS
from ..config.config import is_admin, run_as_admin
from ..config.version import VERSION, GITHUB_REPO_OWNER, GITHUB_REPO_NAME
from ..managers import update_checker
from ..managers.update_manager import UpdateDialog, check_for_updates_startup
from ..config.config import get_install_type
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


class SettingsWindow(QDialog):
    """Comprehensive settings window with tabs"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_app = parent
        self.setWindowTitle("Settings")
        self.setFixedSize(600, 400)
        self.setObjectName("settings_window")
        
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
        
        content_layout.addWidget(self.content_stack)
        main_layout.addLayout(content_layout)
        
        # Bottom buttons
        self._create_bottom_buttons(main_layout)
    
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
        self.keybind_combo.addItem("Arrow Keys (Recommended)")
        self.keybind_combo.addItem("WASD Keys")
        
        if self.parent_app:
            keybind_mode = self.parent_app.global_settings.get("keybind_mode", "arrows")
            self.keybind_combo.setCurrentIndex(1 if keybind_mode == "wasd" else 0)
        
        controls_layout.addWidget(self.keybind_combo)
        
        controls_desc = QLabel(
            "Choose which keys to use for executing stratagems.\n"
            "Arrow Keys (Recommended): Uses ↑↓←→ for stratagem inputs.\n"
            "WASD: Uses W/A/S/D keys for stratagem inputs."
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
        
        self.theme_combo = QComboBox()
        self.theme_combo.setStyleSheet(
            "background: #1a1a1a; color: #ddd; border: 1px solid #333; padding: 4px;"
        )
        self.theme_combo.addItems(["Dark (Default)", "Dark with Blue Accent", "Dark with Red Accent"])
        
        if self.parent_app:
            theme = self.parent_app.global_settings.get("theme", "Dark (Default)")
            idx = self.theme_combo.findText(theme)
            if idx >= 0:
                self.theme_combo.setCurrentIndex(idx)
        
        appear_layout.addWidget(self.theme_combo)
        
        appear_desc = QLabel("Select the color theme for the application. Changes apply immediately.")
        appear_desc.setObjectName("settings_description")
        appear_desc.setWordWrap(True)
        appear_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        appear_layout.addWidget(appear_desc)
        
        appear_layout.addStretch(1)
        self.content_stack.addWidget(appear_widget)
    
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
        new_theme = self.theme_combo.currentText()
        old_require_admin = self.parent_app.global_settings.get("require_admin", False)
        new_require_admin = self.require_admin_check.isChecked()
        
        self.parent_app.speed_slider.setValue(latency_value)
        keybind_mode = "arrows" if self.keybind_combo.currentIndex() == 0 else "wasd"
        
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
