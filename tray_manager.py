"""
Tray manager for Helldivers Numpad Macros
Handles system tray icon and menu
"""

from PyQt6.QtWidgets import QSystemTrayIcon, QMenu
from PyQt6.QtCore import QObject, pyqtSignal


class TrayManager(QObject):
    """Manages system tray icon and menu"""
    
    toggle_macros = pyqtSignal(bool)  # Emitted when user toggles macros from tray
    show_window = pyqtSignal()  # Emitted when user wants to show window
    quit_app = pyqtSignal()  # Emitted when user wants to quit
    
    def __init__(self, app_icon=None, parent=None):
        super().__init__(parent)
        self.app_icon = app_icon
        self.tray_icon = None
        self.tray_toggle_action = None
    
    def setup(self):
        """Setup system tray icon and menu"""
        self.tray_icon = QSystemTrayIcon(self.parent())
        
        # Set icon
        if self.app_icon:
            self.tray_icon.setIcon(self.app_icon)
        
        # Create menu
        tray_menu = QMenu()
        
        self.tray_toggle_action = tray_menu.addAction("Enable Macros")
        self.tray_toggle_action.setCheckable(True)
        self.tray_toggle_action.toggled.connect(self._on_toggle_clicked)
        
        show_action = tray_menu.addAction("Show")
        show_action.triggered.connect(self._on_show_clicked)
        
        tray_menu.addSeparator()
        
        quit_action = tray_menu.addAction("Quit")
        quit_action.triggered.connect(self._on_quit_clicked)
        
        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
    
    def update_state(self, enabled):
        """
        Update tray icon state
        
        Args:
            enabled: Whether macros are enabled
        """
        if not self.tray_icon:
            return
        
        if self.tray_toggle_action:
            self.tray_toggle_action.blockSignals(True)
            self.tray_toggle_action.setChecked(enabled)
            self.tray_toggle_action.setText("Disable Macros" if enabled else "Enable Macros")
            self.tray_toggle_action.blockSignals(False)
        
        state = "ON" if enabled else "OFF"
        self.tray_icon.setToolTip(f"Helldivers Numpad Macros ({state})")
    
    def _on_toggle_clicked(self, checked):
        """Handle toggle action clicked"""
        self.toggle_macros.emit(checked)
    
    def _on_show_clicked(self):
        """Handle show action clicked"""
        self.show_window.emit()
    
    def _on_quit_clicked(self):
        """Handle quit action clicked"""
        self.quit_app.emit()
    
    def _on_tray_activated(self, reason):
        """Handle tray icon activation"""
        if reason == QSystemTrayIcon.ActivationReason.DoubleClick:
            self.show_window.emit()
