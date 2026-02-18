"""
Tray manager for Helldivers Numpad Macros
Handles system tray icon and menu
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import QObject, pyqtSignal


class TrayManager(QObject):
    """Manages system tray icon and menu"""
    
    toggle_macros = pyqtSignal(bool)
    show_window = pyqtSignal()
    quit_app = pyqtSignal()
    
    def __init__(self, app_icon=None, parent=None):
        super().__init__(parent)
        self.app_icon = app_icon
        self.tray_icon = None
        self.tray_toggle_action = None
    
    def setup(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self.parent())
        
        if self.app_icon:
            self.tray_icon.setIcon(self.app_icon)
        
        tray_menu = QMenu()
        
        show_action = tray_menu.addAction("Show Window")
        show_action.triggered.connect(self.show_window.emit)
        
        tray_menu.addSeparator()
        
        self.tray_toggle_action = tray_menu.addAction("Enable Macros")
        self.tray_toggle_action.setCheckable(True)
        self.tray_toggle_action.toggled.connect(lambda checked: self.toggle_macros.emit(checked))
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self.quit_app.emit)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()
    
    def update_state(self, enabled):
        """Update tray icon state based on macro enabled status"""
        if self.tray_toggle_action:
            self.tray_toggle_action.blockSignals(True)
            self.tray_toggle_action.setChecked(enabled)
            self.tray_toggle_action.blockSignals(False)
