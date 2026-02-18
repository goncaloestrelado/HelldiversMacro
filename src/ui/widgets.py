"""
Reusable widgets for Helldivers Numpad Macros
"""

import time
import winsound
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PyQt6.QtCore import Qt, QObject, pyqtSignal
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtGui import QDrag
from PyQt6.QtCore import QMimeData

import keyboard
from ..config.config import find_svg_path


class Comm(QObject):
    update_test_display = pyqtSignal(str, list, str)


comm = Comm()


class DraggableIcon(QWidget):
    """Draggable stratagem icon widget for sidebar"""
    
    def __init__(self, name):
        super().__init__()
        self.name = name
        self.setProperty("role", "icon")
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        
        self.svg_view = QSvgWidget()
        path = find_svg_path(name)
        if path:
            self.svg_view.load(path)
        
        layout.addWidget(self.svg_view)
        self.setToolTip(name)

    def mousePressEvent(self, event):
        """Handle mouse press for drag operation"""
        if event.button() == Qt.MouseButton.LeftButton:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.name)
            mime.setData("source", b"sidebar")
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.exec(Qt.DropAction.MoveAction)


class NumpadSlot(QWidget):
    """Numpad slot widget for assigning stratagems"""
    
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
        """Update visual style based on whether slot is assigned"""
        if assigned:
            border_style, color, bg = "solid", "#ffcc00", "#151515"
            cursor = Qt.CursorShape.PointingHandCursor
            hover_border, hover_bg = "#ff4444", "#201010"
        else:
            border_style, color, bg = "dashed", "#444", "#0a0a0a"
            cursor = Qt.CursorShape.ArrowCursor
            hover_border, hover_bg = "#ffcc00", "#151515"
        
        self.setCursor(cursor)
        self.setStyleSheet(
            f"QWidget {{ border: 2px {border_style} {color}; background: {bg}; "
            f"color: #888; border-radius: 8px; font-weight: bold; }} "
            f"QWidget:hover {{ border: 2px solid {hover_border}; background: {hover_bg}; }}"
        )

    def mousePressEvent(self, event):
        """Handle mouse press for clearing or dragging"""
        if event.button() == Qt.MouseButton.RightButton:
            if self.assigned_stratagem:
                self.clear_slot()
            return

        if event.button() == Qt.MouseButton.LeftButton and self.assigned_stratagem:
            drag = QDrag(self)
            mime = QMimeData()
            mime.setText(self.assigned_stratagem)
            mime.setData("source_slot", str(self.scan_code).encode())
            drag.setMimeData(mime)
            drag.setPixmap(self.grab())
            drag.exec(Qt.DropAction.MoveAction)
    
    def mouseDoubleClickEvent(self, event):
        """Ignore double-click events"""
        event.ignore()

    def dragEnterEvent(self, event):
        """Accept drag enter events"""
        event.accept()

    def dropEvent(self, event):
        """Handle drop events for swapping or assigning stratagems"""
        incoming_strat = event.mimeData().text()
        source_slot_code = event.mimeData().data("source_slot").data().decode()

        if source_slot_code:
            source_slot = self.parent_app.slots.get(source_slot_code)
            if source_slot and source_slot != self:
                existing_strat = self.assigned_stratagem
                if existing_strat:
                    source_slot.assign(existing_strat)
                else:
                    source_slot.clear_slot()
                self.assign(incoming_strat)
        else:
            self.assign(incoming_strat)
        
        event.accept()

    def clear_slot(self):
        """Clear the slot assignment"""
        self.assigned_stratagem = None
        self.svg_display.hide()
        self.label.show()
        self.update_style(False)
        self.parent_app.on_change()

    def assign(self, strat_name):
        """Assign a stratagem to this slot"""
        self.assigned_stratagem = strat_name
        path = find_svg_path(strat_name)
        if path:
            self.label.hide()
            self.svg_display.load(path)
            self.svg_display.show()
            self.update_style(True)
        self.parent_app.on_change()

    def run_macro(self, name, sequence, key_label):
        """Execute the macro for this slot"""
        comm.update_test_display.emit(name, sequence, key_label)
        delay = self.parent_app.speed_slider.value() / 1000.0
        
        for move in sequence:
            actual_key = self.parent_app.map_direction_to_key(move)
            keyboard.press(actual_key)
            time.sleep(delay)
            keyboard.release(actual_key)
            time.sleep(delay)
        
        if self.parent_app.global_settings.get("sound_enabled", True):
            try:
                winsound.Beep(1000, 200)
            except:
                pass
        
        if self.parent_app.global_settings.get("visual_enabled", True):
            self.parent_app.show_status(f"✓ {name} executed", 1500)
