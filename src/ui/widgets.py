"""
Reusable widgets for Helldivers Numpad Macros
"""

import time
import winsound
from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QSizePolicy, QComboBox, QListView, QStyledItemDelegate
from PyQt6.QtCore import Qt, QObject, pyqtSignal, QEvent, QRect
from PyQt6.QtSvgWidgets import QSvgWidget
from PyQt6.QtGui import QDrag, QColor, QPen, QPainter
from PyQt6.QtCore import QMimeData

import keyboard
from ..config.config import find_svg_path


class Comm(QObject):
    update_test_display = pyqtSignal(str, list, str)


comm = Comm()


class DeletableComboDelegate(QStyledItemDelegate):
    """Draw an X affordance at the right side of deletable combo items."""

    def __init__(self, parent_combo):
        super().__init__(parent_combo)
        self.parent_combo = parent_combo

    def paint(self, painter, option, index):
        super().paint(painter, option, index)

        if not self.parent_combo.is_item_deletable(index.row()):
            return

        x_rect = self.parent_combo.get_delete_rect(option.rect)
        painter.save()
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)
        painter.setPen(QPen(QColor("#bbbbbb")))
        painter.drawText(x_rect, Qt.AlignmentFlag.AlignCenter, "🗑")
        painter.restore()


class DeletableComboBox(QComboBox):
    """QComboBox with per-item delete affordance in popup list."""

    deleteRequested = pyqtSignal(str, int, object)

    DELETE_FLAG_ROLE = int(Qt.ItemDataRole.UserRole) + 1
    DELETE_SIZE = 18
    DELETE_MARGIN_RIGHT = 6

    def __init__(self, parent=None):
        super().__init__(parent)
        popup_view = QListView(self)
        popup_view.setMouseTracking(True)
        popup_view.viewport().installEventFilter(self)
        self.setView(popup_view)
        self.setItemDelegate(DeletableComboDelegate(self))

    def addItem(self, text, userData=None, deletable=False):
        super().addItem(text, userData)
        index = self.count() - 1
        self.setItemData(index, bool(deletable), self.DELETE_FLAG_ROLE)

    def addItems(self, texts):
        for text in texts:
            self.addItem(text, deletable=False)

    def setItemDeletable(self, index, deletable):
        if 0 <= index < self.count():
            self.setItemData(index, bool(deletable), self.DELETE_FLAG_ROLE)
            model_index = self.model().index(index, 0)
            self.view().update(model_index)

    def is_item_deletable(self, index):
        if not (0 <= index < self.count()):
            return False
        return bool(self.itemData(index, self.DELETE_FLAG_ROLE))

    def get_delete_rect(self, item_rect):
        return QRect(
            item_rect.right() - self.DELETE_MARGIN_RIGHT - self.DELETE_SIZE,
            item_rect.center().y() - (self.DELETE_SIZE // 2),
            self.DELETE_SIZE,
            self.DELETE_SIZE,
        )

    def eventFilter(self, obj, event):
        if obj is self.view().viewport():
            if event.type() == QEvent.Type.MouseMove:
                index = self.view().indexAt(event.pos())
                if index.isValid() and self.is_item_deletable(index.row()):
                    item_rect = self.view().visualRect(index)
                    on_delete = self.get_delete_rect(item_rect).contains(event.pos())
                    self.view().viewport().setCursor(
                        Qt.CursorShape.PointingHandCursor if on_delete else Qt.CursorShape.ArrowCursor
                    )
                else:
                    self.view().viewport().setCursor(Qt.CursorShape.ArrowCursor)

            if event.type() == QEvent.Type.MouseButtonPress:
                index = self.view().indexAt(event.pos())
                if (
                    index.isValid()
                    and self.is_item_deletable(index.row())
                    and hasattr(event, "button")
                    and event.button() == Qt.MouseButton.LeftButton
                ):
                    item_rect = self.view().visualRect(index)
                    if self.get_delete_rect(item_rect).contains(event.pos()):
                        row = index.row()
                        self.deleteRequested.emit(self.itemText(row), row, self.itemData(row))
                        return True

        return super().eventFilter(obj, event)


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
        self.scan_code = str(scan_code)
        self.label_text = label_text
        self.parent_app = parent_app
        self.assigned_stratagem = None
        self.is_hidden = False
        
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

    def set_hidden(self, hidden):
        """Hide/show slot contents while preserving its grid space."""
        self.is_hidden = bool(hidden)
        if self.is_hidden:
            self.assigned_stratagem = None
            self.svg_display.hide()
            self.label.setText("")
            self.label.hide()
            self.setAcceptDrops(False)
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setStyleSheet(self.build_slot_stylesheet(False))
            return

        self.setAcceptDrops(True)
        self.label.setText(self.label_text)
        self.label.show()
        self.update_style(bool(self.assigned_stratagem))

    def update_style(self, assigned):
        """Update visual style based on whether slot is assigned"""
        if self.is_hidden:
            self.setCursor(Qt.CursorShape.ArrowCursor)
            self.setStyleSheet(self.build_slot_stylesheet(False))
            return

        self.setCursor(
            Qt.CursorShape.PointingHandCursor if assigned else Qt.CursorShape.ArrowCursor
        )
        self.setStyleSheet(self.build_slot_stylesheet(assigned))

    @staticmethod
    def build_slot_stylesheet(assigned):
        """Return the exact stylesheet used by numpad slots."""
        if assigned:
            border_style, color, bg = "solid", "#ffcc00", "#151515"
            hover_border, hover_bg = "#ff4444", "#201010"
        else:
            border_style, color, bg = "dashed", "#444", "#0a0a0a"
            hover_border, hover_bg = "#ffcc00", "#151515"

        return (
            f"QWidget {{ border: 2px {border_style} {color}; background: {bg}; "
            f"color: #888; border-radius: 8px; font-weight: bold; }} "
            f"QWidget:hover {{ border: 2px solid {hover_border}; background: {hover_bg}; }}"
        )

    def mousePressEvent(self, event):
        """Handle mouse press for clearing or dragging"""
        if self.is_hidden:
            return

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
        if self.is_hidden:
            event.ignore()
            return
        event.accept()

    def dropEvent(self, event):
        """Handle drop events for swapping or assigning stratagems"""
        if self.is_hidden:
            event.ignore()
            return

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
        if self.is_hidden:
            return
        self.assigned_stratagem = None
        self.svg_display.hide()
        self.label.show()
        self.update_style(False)
        self.parent_app.on_change()

    def assign(self, strat_name):
        """Assign a stratagem to this slot"""
        if self.is_hidden:
            return
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
        if self.is_hidden:
            return
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


class CollapsibleDepartmentHeader(QWidget):
    """Clickable department header that can be collapsed/expanded"""
    
    def __init__(self, department_name, parent_app=None):
        super().__init__()
        self.department_name = department_name
        self.parent_app = parent_app
        self.is_expanded = True
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        self.header_label = QLabel()
        self.header_label.setObjectName("department_header")
        self.header_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        self.header_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.update_header_display()
        
        layout.addWidget(self.header_label)
        self.setLayout(layout)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
    
    def update_header_display(self):
        """Update the header display with expand/collapse arrow"""
        arrow = "▼" if self.is_expanded else "▶"
        self.header_label.setText(f"{arrow} {self.department_name}")
    
    def mousePressEvent(self, event):
        """Handle click to toggle collapse/expand"""
        if event.button() == Qt.MouseButton.LeftButton:
            self.toggle_collapse()
            event.accept()
    
    def toggle_collapse(self):
        """Toggle the collapse/expand state"""
        self.is_expanded = not self.is_expanded
        self.update_header_display()
        
        # Notify parent app to update visibility
        if self.parent_app and hasattr(self.parent_app, 'update_department_visibility'):
            self.parent_app.update_department_visibility(self.department_name, self.is_expanded)
