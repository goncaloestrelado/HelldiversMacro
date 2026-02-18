import sys
import os
import ctypes

from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QGridLayout, QLabel,
                             QHBoxLayout, QVBoxLayout, QLineEdit, QPushButton, QComboBox,
                             QMessageBox, QListWidget, QToolButton, QCheckBox,
                             QSizePolicy, QListWidgetItem, QSlider, QInputDialog)
from PyQt6.QtCore import Qt, QTimer, QEvent, QSize
from PyQt6.QtGui import QIcon

from src.config import (PROFILES_DIR, ASSETS_DIR, get_theme_stylesheet, load_settings, 
                       save_settings)
from src.config.constants import NUMPAD_LAYOUT
from src.core.stratagem_data import STRATAGEMS, STRATAGEMS_BY_DEPARTMENT
from src.config.version import VERSION, APP_NAME
from src.ui.dialogs import TestEnvironment, SettingsWindow
from src.ui.widgets import DraggableIcon, NumpadSlot, comm
from src.managers.profile_manager import ProfileManager
from src.core.macro_engine import MacroEngine
from src.ui.tray_manager import TrayManager
from src.managers.update_manager import check_for_updates_startup


class StratagemApp(QMainWindow):
    """Main application window for Helldivers 2 Numpad Commander"""
    
    def __init__(self):
        super().__init__()
        self.slots = {}
        self.setWindowTitle(f"{APP_NAME} - Numpad Commander")
        self.global_settings = load_settings()
        self.saved_state = None
        self.undo_btn = None
        self.save_btn = None
        
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

    def initUI(self):
        """Initialize the user interface"""
        self.setObjectName("main_window")
        self.setWindowTitle(f"{APP_NAME} {VERSION}")
        
        # Apply theme
        theme_name = self.global_settings.get("theme", "Dark (Default)")
        self.apply_theme(theme_name)
        
        self._load_app_icon()
        
        central_widget = QWidget()
        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)
        self.setCentralWidget(central_widget)
        
        self._create_top_bar(main_vbox)
        self._create_status_label(main_vbox)
        self._create_main_content(main_vbox)
        self._create_bottom_bar(main_vbox)
        
        self.setMinimumWidth(900)

    def _load_app_icon(self):
        """Load application icon"""
        try:
            icon_path = os.path.join(os.path.dirname(__file__), ASSETS_DIR, "icon.ico")
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
        top_bar.setObjectName("top_bar")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(8, 6, 8, 6)
        top_bar_layout.setSpacing(8)
        
        left_sidebar = QVBoxLayout()
        left_sidebar.setContentsMargins(8, 8, 0, 8)
        
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("menu_button")
        settings_btn.setMaximumWidth(100)
        settings_btn.clicked.connect(self.open_settings)
        left_sidebar.addWidget(settings_btn)
        
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
        
        self.profile_box = QComboBox()
        self.profile_box.setObjectName("profile_box_styled")
        self.profile_box.currentIndexChanged.connect(self.profile_changed)
        right_sidebar.addWidget(self.profile_box)
        
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        
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
        main_layout.addSpacing(6)

    def _create_main_content(self, main_layout):
        """Create main content area with sidebar and numpad grid"""
        content = QHBoxLayout()
        
        # Left sidebar with search and stratagem list
        self._create_sidebar(content)
        
        # Right numpad grid
        self._create_numpad_grid(content)
        
        main_layout.addLayout(content)

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
        for department, stratagems in STRATAGEMS_BY_DEPARTMENT.items():
            header_item = QListWidgetItem()
            header_container = QWidget()
            header_layout = QVBoxLayout(header_container)
            header_layout.setContentsMargins(0, 0, 0, 0)
            header_layout.setSpacing(0)
            
            header_label = QLabel(department)
            header_label.setObjectName("department_header")
            header_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
            header_layout.addWidget(header_label)
            header_container.setLayout(header_layout)
            
            header_item.setSizeHint(QSize(800, 32))
            self.icon_list.addItem(header_item)
            self.icon_list.setItemWidget(header_item, header_container)
            self.header_items.append(header_item)
            
            for name in sorted(stratagems.keys()):
                w = DraggableIcon(name)
                item = QListWidgetItem()
                item.setSizeHint(QSize(80, 80))
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
        for header_item in self.header_items:
            header_item.setSizeHint(QSize(viewport_width - 4, 32))

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
        qss = get_theme_stylesheet(theme_name)
        if qss:
            self.setStyleSheet(qss)

    def save_global_settings(self):
        """Save global settings"""
        save_settings(self.global_settings)

    def open_settings(self):
        """Open settings dialog"""
        dlg = SettingsWindow(self)
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
        
        current_department_index = None
        header_has_visible_items = False
        
        for i in range(self.icon_list.count()):
            item = self.icon_list.item(i)
            widget = self.icon_list.itemWidget(item)
            
            # Check if this is a department header
            is_header = (isinstance(widget, QWidget) and
                        hasattr(widget, 'layout') and
                        widget.layout() is not None and
                        not hasattr(widget, 'stratagem_name'))
            
            if is_header:
                try:
                    if widget.layout().count() > 0:
                        child = widget.layout().itemAt(0).widget()
                        if isinstance(child, QLabel) and not hasattr(child, 'name'):
                            if current_department_index is not None and not header_has_visible_items:
                                self.icon_list.item(current_department_index).setHidden(True)
                            current_department_index = i
                            header_has_visible_items = False
                            item.setHidden(True)
                            continue
                except:
                    pass
            
            # This is an icon
            if hasattr(widget, 'name'):
                item_id = id(item)
                if item_id in visible_icons:
                    should_show = visible_icons[item_id]
                    item.setHidden(not should_show)
                    if should_show and current_department_index is not None:
                        self.icon_list.item(current_department_index).setHidden(False)
                        header_has_visible_items = True
        
        # Handle last header
        if current_department_index is not None and not header_has_visible_items:
            self.icon_list.item(current_department_index).setHidden(True)

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
            seq = STRATAGEMS.get(stratagem_name)
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
