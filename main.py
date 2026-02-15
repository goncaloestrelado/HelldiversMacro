import sys, json, keyboard, time, os, winsound, re, ctypes
from PyQt6.QtWidgets import (QApplication, QWidget, QGridLayout, QLabel, 
                             QHBoxLayout, QVBoxLayout, QScrollArea, QLineEdit, 
                             QPushButton, QFileDialog, QMessageBox, QDialog,
                             QComboBox, QInputDialog, QSlider, QMenuBar, QSpinBox, QMainWindow, QMenu, QListWidget, QStackedWidget, QListWidgetItem, QCheckBox, QSystemTrayIcon, QToolButton, QStyle, QSizePolicy)
from PyQt6.QtCore import Qt, QMimeData, pyqtSignal, QObject, QTimer, QRect, QEvent
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtGui import QDrag, QFont, QPixmap, QAction, QIcon
from stratagem_data import STRATAGEMS

PROFILES_DIR = "profiles"
ASSETS_DIR = "assets"

if not os.path.exists(PROFILES_DIR):
    os.makedirs(PROFILES_DIR)

# Theme file mappings
THEME_FILES = {
    "Dark (Default)": "theme_dark_default.qss",
    "Dark with Blue Accent": "theme_dark_blue.qss",
    "Dark with Red Accent": "theme_dark_red.qss",
}

class Comm(QObject):
    update_test_display = pyqtSignal(str, list, str)

comm = Comm()

def normalize(name):
    return name.lower().replace(" ", "").replace("_", "").replace("-", "").replace("/", "").replace('"', "")

def is_admin():
    """Check if the current process has administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def run_as_admin():
    """Relaunch the current script with administrator privileges"""
    try:
        if getattr(sys, 'frozen', False):
            # Running as compiled executable
            script = sys.executable
        else:
            # Running as Python script
            script = os.path.abspath(sys.argv[0])
        
        params = ' '.join(sys.argv[1:])
        ctypes.windll.shell32.ShellExecuteW(None, "runas", script, params, None, 1)
        return True
    except:
        return False

def find_svg_path(name):
    """Find SVG file for stratagem, with simplified lookup since files now match official names"""
    base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
    assets_lookup = os.path.join(base_path, ASSETS_DIR)
    target = normalize(name)
    for root, dirs, files in os.walk(assets_lookup):
        for f in files:
            if f.endswith(".svg"):
                if normalize(os.path.splitext(f)[0]) == target:
                    return os.path.join(root, f)
    return None

def get_stratagem_name(old_name):
    """Convert old stratagem names to new official names for backward compatibility"""
    name_map = {
        "Machine Gun": "MG-43 Machine Gun",
        "Anti-Materiel Rifle": "APW-1 Anti-Materiel Rifle",
        "Stalwart": "M-105 Stalwart",
        "Expendable Anti-Tank": "EAT-17 Expendable Anti-Tank",
        "Recoilless Rifle": "GR-8 Recoilless Rifle",
        "Flamethrower": "FLAM-40 Flamethrower",
        "Autocannon": "AC-8 Autocannon",
        "Heavy Machine Gun": "MG-206 Heavy Machine Gun",
        "Airburst Rocket Launcher": "RL-77 Airburst Rocket Launcher",
        "Commando": "MLS-4X Commando",
        "Railgun": "RS-422 Railgun",
        "Spear": "FAF-14 Spear",
        "Jump Pack": "LIFT-850 Jump Pack",
        "Eagle 500KG Bomb": "Eagle 500kg Bomb",
        "Fast Recon Vehicle": "M-102 Fast Recon Vehicle",
        "Bastion": "TD-220 Bastion",
        "Bastion MK XVI": "TD-220 Bastion",
        "HMG Emplacement": "E/MG-101 HMG Emplacement",
        "Shield Generator Relay": "FX-12 Shield Generator Relay",
        "Tesla Tower": "A/ARC-3 Tesla Tower",
        "Grenadier Battlement": "E/GL-21 Grenadier Battlement",
        "Anti-Personnel Minefield": "MD-6 Anti-Personnel Minefield",
        "Supply Pack": "B-1 Supply Pack",
        "Grenade Launcher": "GL-21 Grenade Launcher",
        "Laser Cannon": "LAS-98 Laser Cannon",
        "Incendiary Mines": "MD-I4 Incendiary Mines",
        "Guard Dog Rover": "AX/LAS-5 \"Guard Dog\" Rover",
        "Ballistic Shield Backpack": "SH-20 Ballistic Shield Backpack",
        "Arc Thrower": "ARC-3 Arc Thrower",
        "Anti-Tank Mines": "MD-17 Anti-Tank Mines",
        "Quasar Cannon": "LAS-99 Quasar Cannon",
        "Shield Generator Pack": "SH-32 Shield Generator Pack",
        "Gas Mine": "MD-8 Gas Mines",
        "Gas Mines": "MD-8 Gas Mines",
        "Machine Gun Sentry": "A/MG-43 Machine Gun Sentry",
        "Gatling Sentry": "A/G-16 Gatling Sentry",
        "Mortar Sentry": "A/M-12 Mortar Sentry",
        "Guard Dog": "AX/AR-23 \"Guard Dog\"",
        "Autocannon Sentry": "A/AC-8 Autocannon Sentry",
        "Rocket Sentry": "A/MLS-4X Rocket Sentry",
        "EMS Mortar Sentry": "A/M-23 EMS Mortar Sentry",
        "Patriot Exosuit": "EXO-45 Patriot Exosuit",
        "Emancipator Exosuit": "EXO-49 Emancipator Exosuit",
        "Sterilizer": "TX-41 Sterilizer",
        "Guard Dog Breath": "AX/TX-13 \"Guard Dog\" Dog Breath",
        "Guard Dog Dog Breath": "AX/TX-13 \"Guard Dog\" Dog Breath",
        "Directional Shield": "SH-51 Directional Shield",
        "Anti-Tank Emplacement": "E/AT-12 Anti-Tank Emplacement",
        "Flame Sentry": "A/FLAM-40 Flame Sentry",
        "Portable Hellbomb": "B-100 Portable Hellbomb",
        "Hellbomb Portable": "B-100 Portable Hellbomb",
        "Hover Pack": "LIFT-860 Hover Pack",
        "One True Flag": "CQC-1 One True Flag",
        "De-Escalator": "GL-52 De-Escalator",
        "Guard Dog K-9": "AX/ARC-3 \"Guard Dog\" K-9",
        "Epoch": "PLAS-45 Epoch",
        "Laser Sentry": "A/LAS-98 Laser Sentry",
        "Warp Pack": "LIFT-182 Warp Pack",
        "Speargun": "S-11 Speargun",
        "Expendable Napalm": "EAT-700 Expendable Napalm",
        "Solo Silo": "MS-11 Solo Silo",
        "Maxigun": "M-1000 Maxigun",
        "Defoliation Tool": "CQC-9 Defoliation Tool",
        "Guard Dog Hot Dog": "AX/FLAM-75 \"Guard Dog\" Hot Dog",
        "C4 Pack": "B/MD C4 Pack",
        "Breaching Hammer": "CQC-20 Breaching Hammer",
        "CQC-20": "CQC-20 Breaching Hammer",
        "EAT-411": "EAT-411 Leveller",
        "GL-28": "GL-28 Belt-Fed Grenade Launcher",
        "Illumination Flare": "Orbital Illumination Flare",
    }
    return name_map.get(old_name, old_name)

class TestEnvironment(QDialog):
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
        self.key_label.setText(f"HOTKEY TRIGGERED: [ {key_label} ]")
        self.name_label.setText(f"EXECUTING: {name.upper()}")
        icons = {"up": "↑", "down": "↓", "left": "←", "right": "→"}
        visual_seq = " ".join([icons.get(m, m) for m in sequence])
        self.arrow_display.setText(visual_seq)


class SettingsDialog(QDialog):
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

        # initialize from parent if available
        if self.parent_app:
            val = self.parent_app.speed_slider.value()
        else:
            val = 20
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
        if self.parent_app:
            self.parent_app.speed_slider.setValue(self.spin.value())
            self.parent_app.update_speed_label(self.spin.value())
        self.accept()


class SettingsWindow(QDialog):
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
        
        # Right content area
        self.content_stack = QStackedWidget()
        self.content_stack.setObjectName("settings_content")
        
        # ===== LATENCY TAB =====
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
        
        if self.parent_app:
            val = self.parent_app.global_settings.get("latency", 20)
        else:
            val = 20
        self.slider.setValue(val)
        self.spin.setValue(val)
        
        self.slider.valueChanged.connect(self.spin.setValue)
        self.spin.valueChanged.connect(self.slider.setValue)
        
        row.addWidget(self.slider)
        row.addWidget(self.spin)
        latency_layout.addLayout(row)
        
        # Add description
        desc_label = QLabel("Latency controls the delay (in milliseconds) between each keypress\nwhen executing stratagems. Lower values = faster execution, higher values = more reliable on high-ping servers.\nRecommended between 20ms and 30ms.")
        desc_label.setObjectName("settings_description")
        desc_label.setWordWrap(True)
        desc_label.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        latency_layout.addWidget(desc_label)
        
        latency_layout.addStretch(1)
        self.content_stack.addWidget(latency_widget)
        
        # ===== CONTROLS TAB =====
        controls_widget = QWidget()
        controls_layout = QVBoxLayout(controls_widget)
        
        controls_label = QLabel("Stratagem Controls")
        controls_label.setObjectName("settings_label")
        controls_layout.addWidget(controls_label)
        
        keys_label = QLabel("Key Binding:")
        keys_label.setStyleSheet("color: #ddd; padding-top: 8px;")
        controls_layout.addWidget(keys_label)
        
        self.keybind_combo = QComboBox()
        self.keybind_combo.setStyleSheet("background: #1a1a1a; color: #ddd; border: 1px solid #333; padding: 4px;")
        self.keybind_combo.addItem("Arrow Keys (Recommended)")
        self.keybind_combo.addItem("WASD Keys")
        if self.parent_app:
            keybind_mode = self.parent_app.global_settings.get("keybind_mode", "arrows")
            if keybind_mode == "wasd":
                self.keybind_combo.setCurrentIndex(1)
            else:
                self.keybind_combo.setCurrentIndex(0)
        controls_layout.addWidget(self.keybind_combo)
        
        controls_desc = QLabel("Choose which keys to use for executing stratagems.\nArrow Keys (Recommended): Uses ↑↓←→ for stratagem inputs.\nWASD: Uses W/A/S/D keys for stratagem inputs.")
        controls_desc.setObjectName("settings_description")
        controls_desc.setWordWrap(True)
        controls_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        controls_layout.addWidget(controls_desc)
        
        controls_layout.addStretch(1)
        self.content_stack.addWidget(controls_widget)
        
        # ===== AUTOLOAD TAB =====
        autoload_widget = QWidget()
        autoload_layout = QVBoxLayout(autoload_widget)
        
        autoload_label = QLabel("Profile Autoload")
        autoload_label.setObjectName("settings_label")
        autoload_layout.addWidget(autoload_label)
        
        self.autoload_check = QCheckBox("Auto-load last profile on startup")
        self.autoload_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.autoload_check.setChecked(self.parent_app.global_settings.get("autoload_profile", False))
        autoload_layout.addWidget(self.autoload_check)
        
        autoload_desc = QLabel("When enabled, the application will automatically load the last profile you were using when it starts up.")
        autoload_desc.setObjectName("settings_description")
        autoload_desc.setWordWrap(True)
        autoload_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        autoload_layout.addWidget(autoload_desc)
        
        autoload_layout.addStretch(1)
        self.content_stack.addWidget(autoload_widget)
        
        # ===== NOTIFICATIONS TAB =====
        notif_widget = QWidget()
        notif_layout = QVBoxLayout(notif_widget)
        
        notif_label = QLabel("Notifications")
        notif_label.setObjectName("settings_label")
        notif_layout.addWidget(notif_label)
        
        self.sound_check = QCheckBox("Enable sound notifications")
        self.sound_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.sound_check.setChecked(self.parent_app.global_settings.get("sound_enabled", True))
        notif_layout.addWidget(self.sound_check)
        
        self.visual_check = QCheckBox("Enable visual notifications")
        self.visual_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.visual_check.setChecked(self.parent_app.global_settings.get("visual_enabled", True))
        notif_layout.addWidget(self.visual_check)
        
        notif_desc = QLabel("Show notifications when macro execution completes successfully.\nSound notifications play a beep when enabled.")
        notif_desc.setObjectName("settings_description")
        notif_desc.setWordWrap(True)
        notif_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        notif_layout.addWidget(notif_desc)
        
        notif_layout.addStretch(1)
        self.content_stack.addWidget(notif_widget)
        
        # ===== APPEARANCE TAB =====
        appear_widget = QWidget()
        appear_layout = QVBoxLayout(appear_widget)
        
        appear_label = QLabel("Appearance")
        appear_label.setObjectName("settings_label")
        appear_layout.addWidget(appear_label)
        
        theme_label = QLabel("Theme:")
        theme_label.setStyleSheet("color: #ddd; padding-top: 8px;")
        appear_layout.addWidget(theme_label)
        
        self.theme_combo = QComboBox()
        self.theme_combo.setStyleSheet("background: #1a1a1a; color: #ddd; border: 1px solid #333; padding: 4px;")
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
        
        # ===== WINDOWS TAB =====
        windows_widget = QWidget()
        windows_layout = QVBoxLayout(windows_widget)
        
        windows_label = QLabel("Window Settings")
        windows_label.setObjectName("settings_label")
        windows_layout.addWidget(windows_label)
        
        self.minimize_tray_check = QCheckBox("Minimize to system tray on close")
        self.minimize_tray_check.setStyleSheet("color: #ddd; padding: 8px;")
        if self.parent_app:
            self.minimize_tray_check.setChecked(self.parent_app.global_settings.get("minimize_to_tray", True))
        windows_layout.addWidget(self.minimize_tray_check)
        
        windows_desc = QLabel("When enabled, closing the window minimizes the application to the system tray.\nWhen disabled, closing the window exits the application.")
        windows_desc.setObjectName("settings_description")
        windows_desc.setWordWrap(True)
        windows_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        windows_layout.addWidget(windows_desc)
        
        # Admin privileges checkbox
        self.require_admin_check = QCheckBox("Require administrator privileges")
        self.require_admin_check.setStyleSheet("color: #ddd; padding: 8px; margin-top: 15px;")
        if self.parent_app:
            self.require_admin_check.setChecked(self.parent_app.global_settings.get("require_admin", False))
        windows_layout.addWidget(self.require_admin_check)
        
        admin_desc = QLabel("When enabled, the application will request administrator privileges on startup.\nThis is required if Helldivers 2 runs with admin rights. Application will restart to apply changes.")
        admin_desc.setObjectName("settings_description")
        admin_desc.setWordWrap(True)
        admin_desc.setStyleSheet("color: #aaa; font-size: 11px; margin-top: 10px;")
        windows_layout.addWidget(admin_desc)
        
        windows_layout.addStretch(1)
        self.content_stack.addWidget(windows_widget)
        
        content_layout.addWidget(self.content_stack)
        
        main_layout.addLayout(content_layout)
        
        # Bottom buttons
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
        
        main_layout.addLayout(btn_row)
    
    def switch_tab(self, item):
        self.content_stack.setCurrentIndex(self.tab_list.row(item))
    
    def apply_and_close(self):
        if self.parent_app:
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
            self.parent_app.save_global_settings()
            self.parent_app.update_speed_label(latency_value)
            
            # Apply theme immediately if changed
            if old_theme != new_theme:
                self.parent_app.apply_theme(new_theme)
            
            # Handle admin privilege change
            if old_require_admin != new_require_admin:
                if new_require_admin and not is_admin():
                    # Need admin but not running as admin - restart with admin
                    reply = QMessageBox.question(self, "Restart Required",
                        "Application needs to restart with administrator privileges.\nRestart now?",
                        QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
                    if reply == QMessageBox.StandardButton.Yes:
                        self.accept()
                        if run_as_admin():
                            QApplication.quit()
                        else:
                            QMessageBox.warning(self, "Error", "Failed to elevate privileges. Please run as administrator manually.")
                        return
                elif not new_require_admin and is_admin():
                    # No longer need admin but running as admin - inform user
                    QMessageBox.information(self, "Restart Recommended",
                        "To run without administrator privileges, please restart the application normally.")
        self.accept()


class DraggableIcon(QWidget):
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.setProperty("role", "icon")
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        self.svg_view = QSvgWidget()
        path = find_svg_path(name)
        if path: self.svg_view.load(path)
        layout.addWidget(self.svg_view)
        self.setToolTip(name)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.name)
            mime.setData("source", b"sidebar")
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.exec(Qt.DropAction.MoveAction)

class NumpadSlot(QWidget):
    def __init__(self, scan_code, label_text, parent_app):
        super().__init__()
        self.scan_code = int(scan_code)
        self.label_text = label_text
        self.parent_app = parent_app
        self.assigned_stratagem = None
        self.setProperty("role", "numpad-slot")
        self.setAcceptDrops(True)
        self.layout = QVBoxLayout(self)
        self.label = QLabel(label_text)
        self.label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.layout.addWidget(self.label)
        self.svg_display = QSvgWidget()
        self.layout.addWidget(self.svg_display, alignment=Qt.AlignmentFlag.AlignCenter)
        self.svg_display.hide()
        self.update_style(False)

    def update_style(self, assigned):
        border_style, color, bg = ("solid", "#ffcc00", "#151515") if assigned else ("dashed", "#444", "#0a0a0a")
        self.setCursor(Qt.CursorShape.PointingHandCursor if assigned else Qt.CursorShape.ArrowCursor)
        self.setStyleSheet(f"QWidget {{ border: 2px {border_style} {color}; background: {bg}; color: #888; border-radius: 8px; font-weight: bold; }} QWidget:hover {{ border: 2px solid {'#ff4444' if assigned else '#ffcc00'}; background: {'#201010' if assigned else '#151515'}; }}")

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.RightButton:
            if self.assigned_stratagem:
                self.clear_slot()
            return

        if event.button() == Qt.MouseButton.LeftButton:
            if self.assigned_stratagem:
                drag = QDrag(self)
                mime = QMimeData()
                mime.setText(self.assigned_stratagem)
                mime.setData("source_slot", str(self.scan_code).encode())
                drag.setMimeData(mime)
                drag.setPixmap(self.grab())
                drag.exec(Qt.DropAction.MoveAction)
            
    def mouseDoubleClickEvent(self, event):
        event.ignore()

    def dragEnterEvent(self, event):
        event.accept()

    def dropEvent(self, event):
        incoming_strat = event.mimeData().text()
        source_slot_code = event.mimeData().data("source_slot").data().decode()

        if source_slot_code:
            source_slot = self.parent_app.slots.get(source_slot_code)
            if source_slot and source_slot != self:
                # SWAP LOGIC: Move destination content to source slot
                existing_strat = self.assigned_stratagem
                if existing_strat:
                    source_slot.assign(existing_strat)
                else:
                    source_slot.clear_slot()
                
                # Assign incoming to this slot
                self.assign(incoming_strat)
        else:
            # Dropping from sidebar (overwrite)
            self.assign(incoming_strat)
            
        event.accept()

    def clear_slot(self):
        self.assigned_stratagem = None
        self.svg_display.hide()
        self.label.show()
        self.update_style(False)
        self.parent_app.on_change()  # Trigger change detection

    def assign(self, strat_name):
        self.assigned_stratagem = strat_name
        path = find_svg_path(strat_name)
        if path:
            self.label.hide()
            self.svg_display.load(path)
            self.svg_display.show()
            self.update_style(True)
        self.parent_app.on_change()  # Trigger change detection

    def run_macro(self, name, sequence, key_label):
        comm.update_test_display.emit(name, sequence, key_label)
        delay = self.parent_app.speed_slider.value() / 1000.0
        for move in sequence:
            actual_key = self.parent_app.map_direction_to_key(move)
            keyboard.press(actual_key)
            time.sleep(delay) 
            keyboard.release(actual_key)
            time.sleep(delay)
        
        # Add notifications after macro executes
        if self.parent_app.global_settings.get("sound_enabled", True):
            try:
                winsound.Beep(1000, 200)  # 1000Hz for 200ms
            except:
                pass
        
        if self.parent_app.global_settings.get("visual_enabled", True):
            self.parent_app.show_status(f"✓ {name} executed", 1500)

class StratagemApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.slots = {}
        self.setWindowTitle("Helldivers 2 - Numpad Commander")
        self.global_settings = {}
        self.saved_state = None  # Track the last saved state
        self.undo_btn = None  # Will be set in initUI
        self.load_global_settings()
        self.initUI()
        self.refresh_profiles()
        self.setup_tray()
        # Autoload profile if enabled
        if self.global_settings.get("autoload_profile", False):
            last_profile = self.global_settings.get("last_profile", None)
            if last_profile and last_profile != "Create new profile":
                idx = self.profile_box.findText(last_profile)
                if idx >= 0:
                    self.profile_box.setCurrentIndex(idx)

    def initUI(self):
        self.setObjectName("main_window")
        # Apply theme-based stylesheet
        theme_name = self.global_settings.get("theme", "Dark (Default)")
        self.apply_theme(theme_name)

        # Load icon from assets
        try:
            icon_path = os.path.join(os.path.dirname(__file__), "assets", "icon.ico")
            if os.path.exists(icon_path):
                app_icon = QIcon(icon_path)
                self.setWindowIcon(app_icon)
                self.app_icon = app_icon
            else:
                self.app_icon = None
        except Exception:
            self.app_icon = None

        # Central widget with main layout
        central_widget = QWidget()
        main_vbox = QVBoxLayout(central_widget)
        main_vbox.setContentsMargins(0, 0, 0, 0)
        main_vbox.setSpacing(0)
        self.setCentralWidget(central_widget)

        # Top bar with menu and controls
        top_bar = QWidget()
        top_bar.setObjectName("top_bar")
        top_bar_layout = QHBoxLayout(top_bar)
        top_bar_layout.setContentsMargins(8, 6, 8, 6)
        top_bar_layout.setSpacing(8)
        
        # Left sidebar: Settings and Latency (vertical)
        left_sidebar = QVBoxLayout()
        left_sidebar.setContentsMargins(8, 8, 0, 8)
        
        # Settings button
        settings_btn = QPushButton("⚙ Settings")
        settings_btn.setObjectName("menu_button")
        settings_btn.setMaximumWidth(100)
        settings_btn.clicked.connect(self.open_settings)
        left_sidebar.addWidget(settings_btn)
        
        # Latency info
        self.speed_btn = QPushButton("Latency:")
        self.speed_btn.setText(f"Latency: {self.global_settings.get('latency', 20)}ms")
        self.speed_btn.setObjectName("speed_btn")
        self.speed_btn.clicked.connect(self.open_settings)
        self.speed_slider = QSlider(Qt.Orientation.Horizontal)
        self.speed_slider.setObjectName("speed_slider")
        self.speed_slider.setRange(1, 200)
        self.speed_slider.setValue(self.global_settings.get("latency", 20))
        self.speed_slider.valueChanged.connect(self.update_speed_label)
        self.speed_slider.valueChanged.connect(self.on_change)  # Track changes
        # keep the slider around for logic but hide it from the toolbar; settings dialog will control it
        self.speed_slider.setVisible(False)
        left_sidebar.addWidget(self.speed_btn)

        top_bar_layout.addLayout(left_sidebar)


        # Right sidebar: Profile Select and Action Buttons (vertical)
        right_sidebar = QVBoxLayout()
        right_sidebar.setContentsMargins(0, 8, 8, 8)
        
        # Profile select
        self.profile_box = QComboBox()
        self.profile_box.setObjectName("profile_box_styled")
        self.profile_box.currentIndexChanged.connect(self.profile_changed)
        right_sidebar.addWidget(self.profile_box)
        
        # Action buttons
        btn_layout = QHBoxLayout()
        btn_layout.setSpacing(6)
        self.undo_btn = QPushButton("↶")  # Undo button
        btn_save, btn_test, btn_clear = QPushButton("💾"), QPushButton("🧪"), QPushButton("🗑️")
        self.save_btn = btn_save
        for btn, tip in zip([self.undo_btn, btn_save, btn_test, btn_clear], ["Undo Changes", "Save Profile", "Test Mode", "Clear"]):
            btn.setToolTip(tip)
            btn.setProperty("role", "action")
            btn.setStyleSheet(btn.styleSheet())  # Ensure styling is applied
            btn_layout.addWidget(btn)

        self.undo_btn.clicked.connect(self.undo_changes)
        btn_save.clicked.connect(self.manual_save)
        btn_test.clicked.connect(lambda: TestEnvironment().exec())
        btn_clear.clicked.connect(self.confirm_clear)
        self.update_undo_state()  # Initialize undo button state
        right_sidebar.addLayout(btn_layout)
        
        top_bar_layout.addLayout(right_sidebar)
        main_vbox.addWidget(top_bar)

        # Status messages between top bar and content
        self.status_label = QLabel("")
        self.status_label.setObjectName("status_label")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        main_vbox.addWidget(self.status_label)
        main_vbox.addSpacing(6)

        content = QHBoxLayout()
        
        # Create a container for search and scroll area
        side_container = QWidget()
        side_container.setObjectName("search_scroll_container")
        self.side_container = side_container
        side = QVBoxLayout(side_container)
        side.setSpacing(0)  # Remove gap between search and list
        side.setContentsMargins(0, 0, 0, 0)  # Remove margins
        
        self.search = QLineEdit()
        self.search.setObjectName("search_input")
        self.search.setPlaceholderText("Search...")
        self.search.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)
        self.search.setMinimumHeight(32)
        self.search.setMaximumHeight(32)
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

        self.icon_scroll = QScrollArea()
        self.icon_scroll.setObjectName("icon_scroll")
        self.scroll_widget = QWidget()
        self.scroll_layout = QVBoxLayout(self.scroll_widget)
        self.scroll_layout.setContentsMargins(0, 0, 0, 0)
        self.scroll_layout.setAlignment(Qt.AlignmentFlag.AlignHCenter)
        self.icon_widgets = []
        for name in sorted(STRATAGEMS.keys()):
            w = DraggableIcon(name); self.icon_widgets.append(w); self.scroll_layout.addWidget(w)
        self.icon_scroll.setWidget(self.scroll_widget); self.icon_scroll.setWidgetResizable(True)
        self.icon_scroll.viewport().installEventFilter(self)
        side.addWidget(self.icon_scroll)
        QTimer.singleShot(0, self.update_search_width)

        grid = QGridLayout()
        grid.setSpacing(12)
        
        slot = NumpadSlot('53', '/', self)
        grid.addWidget(slot, 0, 1)
        self.slots['53'] = slot
        
        slot = NumpadSlot('55', '*', self)
        grid.addWidget(slot, 0, 2)
        self.slots['55'] = slot
        
        slot = NumpadSlot('74', '-', self)
        grid.addWidget(slot, 0, 3)
        self.slots['74'] = slot
        
        slot = NumpadSlot('71', '7', self)
        grid.addWidget(slot, 1, 0)
        self.slots['71'] = slot
        
        slot = NumpadSlot('72', '8', self)
        grid.addWidget(slot, 1, 1)
        self.slots['72'] = slot
        
        slot = NumpadSlot('73', '9', self)
        grid.addWidget(slot, 1, 2)
        self.slots['73'] = slot
        
        slot = NumpadSlot('78', '+', self)
        grid.addWidget(slot, 1, 3, 2, 1)
        self.slots['78'] = slot
        
        slot = NumpadSlot('75', '4', self)
        grid.addWidget(slot, 2, 0)
        self.slots['75'] = slot
        
        slot = NumpadSlot('76', '5', self)
        grid.addWidget(slot, 2, 1)
        self.slots['76'] = slot
        
        slot = NumpadSlot('77', '6', self)
        grid.addWidget(slot, 2, 2)
        self.slots['77'] = slot
        
        slot = NumpadSlot('79', '1', self)
        grid.addWidget(slot, 3, 0)
        self.slots['79'] = slot
        
        slot = NumpadSlot('80', '2', self)
        grid.addWidget(slot, 3, 1)
        self.slots['80'] = slot
        
        slot = NumpadSlot('81', '3', self)
        grid.addWidget(slot, 3, 2)
        self.slots['81'] = slot
        
        slot = NumpadSlot('28', 'Enter', self)
        grid.addWidget(slot, 3, 3, 2, 1)
        self.slots['28'] = slot
        
        slot = NumpadSlot('82', '0', self)
        grid.addWidget(slot, 4, 0, 1, 2)
        self.slots['82'] = slot
        
        slot = NumpadSlot('83', '.', self)
        grid.addWidget(slot, 4, 2)
        self.slots['83'] = slot

        content.addWidget(side_container); content.addLayout(grid); main_vbox.addLayout(content)

        # Bottom bar with macro toggle
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
        main_vbox.addWidget(bottom_bar)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.update_search_clear_position()
        self.update_search_width()

    def eventFilter(self, source, event):
        if source == self.search and event.type() == QEvent.Type.Resize:
            self.update_search_clear_position()
            if self.search.height() != 32:
                self.search.setFixedHeight(32)
        return super().eventFilter(source, event)

    def update_search_clear_visibility(self, text):
        if not hasattr(self, "search_clear_btn"):
            return
        has_text = bool(text)
        self.search_clear_btn.setVisible(has_text)
        self.update_search_clear_position()

    def update_search_clear_position(self):
        if not hasattr(self, "search_clear_btn"):
            return
        frame_width = self.search.style().pixelMetric(QStyle.PixelMetric.PM_DefaultFrameWidth)
        btn_size = self.search_clear_btn.sizeHint()
        right_padding = btn_size.width() + 10
        self.search.setTextMargins(8, 0, right_padding, 0)
        x = self.search.rect().right() - frame_width - btn_size.width() - 4
        y = (self.search.rect().height() - btn_size.height()) // 2
        self.search_clear_btn.move(x, y)

    def update_search_width(self):
        if not hasattr(self, "icon_scroll") or not hasattr(self, "search"):
            return
        scroll_width = self.icon_scroll.width()
        if scroll_width <= 0:
            return
        placeholder_width = self.search.fontMetrics().horizontalAdvance(self.search.placeholderText())
        min_width = placeholder_width + 100
        target_width = max(scroll_width, min_width)
        if hasattr(self, "side_container"):
            self.side_container.setMinimumWidth(target_width)
        self.search.setFixedWidth(target_width)
        self.search.setFixedHeight(32)
        self.icon_scroll.setFixedWidth(target_width)

    def show_status(self, text, duration=2500):
        self.status_label.setText(text.upper())
        self.status_label.show()
        self.status_label.raise_()
        QTimer.singleShot(duration, lambda: self.status_label.setText(""))

    def update_macro_toggle_ui(self):
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
        if hasattr(self, "tray_toggle_action"):
            self.tray_toggle_action.blockSignals(True)
            self.tray_toggle_action.setChecked(enabled)
            self.tray_toggle_action.setText("Disable Macros" if enabled else "Enable Macros")
            self.tray_toggle_action.blockSignals(False)
        if hasattr(self, "tray_icon"):
            state = "ON" if enabled else "OFF"
            self.tray_icon.setToolTip(f"Helldivers Numpad Macros ({state})")

    def set_macros_enabled(self, enabled, notify=True):
        self.global_settings["macros_enabled"] = bool(enabled)
        self.save_global_settings()
        if enabled:
            self.inject_all()
            if notify:
                self.show_status("Macros enabled")
        else:
            try:
                keyboard.unhook_all()
            except:
                pass
            if notify:
                self.show_status("Macros disabled")
        self.update_macro_toggle_ui()

    def sync_macro_hook_state(self, notify=False):
        self.set_macros_enabled(self.global_settings.get("macros_enabled", False), notify=notify)

    def map_direction_to_key(self, direction):
        """Map stratagem direction to actual key based on user setting"""
        keybind_mode = self.global_settings.get("keybind_mode", "arrows")
        
        if keybind_mode == "wasd":
            mapping = {
                "up": "w",
                "down": "s",
                "left": "a",
                "right": "d"
            }
        else:  # arrows (default)
            mapping = {
                "up": "up",
                "down": "down",
                "left": "left",
                "right": "right"
            }
        
        return mapping.get(direction, direction)
    
    def load_global_settings(self):
        """Load global settings from general.json"""
        try:
            if os.path.exists("general.json"):
                with open("general.json", "r") as f:
                    self.global_settings = json.load(f)
            else:
                self.global_settings = {"latency": 20, "macros_enabled": False, "keybind_mode": "arrows"}
                self.save_global_settings()
        except Exception:
            self.global_settings = {"latency": 20, "macros_enabled": False, "keybind_mode": "arrows"}

        if "macros_enabled" not in self.global_settings:
            self.global_settings["macros_enabled"] = False
            self.save_global_settings()
        
        if "keybind_mode" not in self.global_settings:
            self.global_settings["keybind_mode"] = "arrows"
            self.save_global_settings()

    def save_global_settings(self):
        """Save global settings to general.json"""
        try:
            with open("general.json", "w") as f:
                json.dump(self.global_settings, f, indent=2)
        except Exception:
            pass

    def apply_theme(self, theme_name="Dark (Default)"):
        try:
            theme_file = THEME_FILES.get(theme_name, THEME_FILES["Dark (Default)"])
            # Use the same logic as find_svg_path to locate the theme inside the EXE
            base_path = getattr(sys, '_MEIPASS', os.path.abspath("."))
            qss_path = os.path.join(base_path, theme_file)
            
            if os.path.exists(qss_path):
                with open(qss_path, 'r', encoding='utf-8') as f:
                    qss = f.read()
                assets_root = os.path.join(base_path, ASSETS_DIR)
                qss = re.sub(
                    r"url\((['\"]?)assets/([^'\")]+)\1\)",
                    lambda m: f"url(\"{os.path.join(assets_root, m.group(2)).replace('\\', '/')}\")",
                    qss,
                )
                self.setStyleSheet(qss)
        except Exception as e:
            print(f"Theme Error: {e}")

    def update_speed_label(self, value):
        self.speed_btn.setText(f"Latency: {value}ms")

    def open_settings(self):
        dlg = SettingsWindow(self)
        if dlg.exec():
            self.show_status(f"Settings applied.")

    def setup_tray(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self)
        # Set the tray icon
        if hasattr(self, 'app_icon') and self.app_icon:
            self.tray_icon.setIcon(self.app_icon)
        tray_menu = QMenu()
        self.tray_toggle_action = tray_menu.addAction("Enable Macros")
        self.tray_toggle_action.setCheckable(True)
        self.tray_toggle_action.toggled.connect(lambda checked: self.set_macros_enabled(checked))
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self.showNormal)
        tray_menu.addSeparator()
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_application)
        self.tray_icon.setContextMenu(tray_menu)
        # Click on tray icon to toggle window visibility
        self.tray_icon.activated.connect(self.toggle_window_visibility)
        self.tray_icon.show()
        self.update_macro_toggle_ui()

    def toggle_window_visibility(self, reason):
        """Toggle window visibility when tray icon is clicked"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            if self.isVisible():
                self.hide()
            else:
                self.showNormal()

    def quit_application(self):
        """Quit the application"""
        try:
            keyboard.unhook_all()
        except:
            pass
        QApplication.quit()

    def edit_latency_manually(self):
        val, ok = QInputDialog.getInt(self, "Manual Latency", "Set delay (ms):", self.speed_slider.value(), 1, 200, 1)
        if ok: self.speed_slider.setValue(val)

    def refresh_profiles(self):
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
        current = self.profile_box.currentText()
        if current == "Create new profile":
            for slot in self.slots.values(): slot.clear_slot()
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
        current = self.profile_box.currentText()
        if current == "Create new profile":
            name, ok = QInputDialog.getText(self, "New Profile", "Enter name:")
            if ok and name:
                clean_name = os.path.splitext(name)[0]
                self.save_to_file(os.path.join(PROFILES_DIR, f"{clean_name}.json"))
                self.refresh_profiles()
                self.profile_box.setCurrentText(clean_name)
                self.show_status("PROFILE SAVED")
            else: return
        else: 
            self.save_to_file(os.path.join(PROFILES_DIR, f"{current}.json"))
            self.show_status("PROFILE SAVED")
        self.save_current_state()  # Update saved state after saving
        self.update_undo_state()

    def save_to_file(self, path):
        data = {"speed": self.speed_slider.value(), "mappings": {k: v.assigned_stratagem for k, v in self.slots.items() if v.assigned_stratagem}}
        with open(path, "w") as f: json.dump(data, f)

    def load_profile(self, path):
        for slot in self.slots.values(): slot.clear_slot()
        if os.path.exists(path):
            with open(path, "r") as f:
                data = json.load(f)
                self.speed_slider.blockSignals(True)  # Block signals to prevent triggering on_change
                self.speed_slider.setValue(data.get("speed", 20))
                self.speed_slider.blockSignals(False)
                mappings = data.get("mappings", {})
                for code, strat in mappings.items():
                    if code in self.slots: self.slots[code].assign(strat)
            self.sync_macro_hook_state()
            self.save_current_state()  # Save the loaded state

    def inject_all(self):
        try: keyboard.unhook_all()
        except: pass
        keyboard.hook(self.universal_suppressor)

    def universal_suppressor(self, event):
        if event.event_type == keyboard.KEY_DOWN:
            slot = self.slots.get(str(event.scan_code))
            if slot and slot.assigned_stratagem:
                if getattr(event, 'is_keypad', True):
                    stratagem_name = get_stratagem_name(slot.assigned_stratagem)
                    seq = STRATAGEMS.get(stratagem_name)
                    if seq:
                        slot.run_macro(stratagem_name, seq, slot.label_text)
                    return False
        return True

    def closeEvent(self, event):
        """Minimize to tray when closed if setting enabled, otherwise quit"""
        if self.has_unsaved_changes():
            prompt = "You have unsaved changes. Close anyway?"
            if QMessageBox.question(
                self,
                "Unsaved Changes",
                prompt,
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
                QMessageBox.StandardButton.No,
            ) != QMessageBox.StandardButton.Yes:
                event.ignore()
                return
        if self.global_settings.get("minimize_to_tray", True):
            self.hide()
            event.ignore()
        else:
            try:
                keyboard.unhook_all()
            except:
                pass
            event.accept()

    def confirm_clear(self):
        if QMessageBox.question(self, 'Reset', 'Clear Slots?', QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No) == QMessageBox.StandardButton.Yes:
            for slot in self.slots.values(): slot.clear_slot()
            self.show_status("GRID CLEARED")

    def filter_icons(self, text):
        for w in self.icon_widgets: w.setVisible(text.lower() in w.name.lower())

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
            # Fresh profile has no saved state
            current = self.get_current_state()
            return current["speed"] != 20 or bool(current["mappings"])
        
        current = self.get_current_state()
        return current != self.saved_state

    def update_undo_state(self):
        """Enable/disable undo button based on unsaved changes"""
        if self.undo_btn:
            has_changes = self.has_unsaved_changes()
            self.undo_btn.setEnabled(has_changes)
            # Add visual indication when disabled
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

if __name__ == '__main__':
    # Check if admin privileges are required
    temp_app = QApplication(sys.argv)
    
    # Load settings to check admin requirement
    require_admin = False
    try:
        if os.path.exists("general.json"):
            with open("general.json", "r") as f:
                settings = json.load(f)
                require_admin = settings.get("require_admin", False)
    except:
        pass
    
    # If admin is required but not running as admin, request elevation
    if require_admin and not is_admin():
        reply = QMessageBox.question(None, "Administrator Privileges Required",
            "This application is configured to require administrator privileges.\nRestart with administrator privileges?",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
        if reply == QMessageBox.StandardButton.Yes:
            if run_as_admin():
                sys.exit(0)
            else:
                QMessageBox.warning(None, "Error", "Failed to elevate privileges. Continuing without admin rights.")
    
    # Continue with normal startup
    ex = StratagemApp()
    ex.show()
    sys.exit(temp_app.exec())