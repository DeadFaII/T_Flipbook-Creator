import os
import sys

from PIL import Image
from PySide6.QtCore import QSize, Qt, QMimeData, QPoint, QTimer
from PySide6.QtGui import QIcon, QPixmap, QImage, QPainter, QDrag, QAction, QKeySequence, QColor
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QPushButton, QFrame, QFileDialog, QSlider, QLabel,
    QSpacerItem, QSizePolicy, QGridLayout, QScrollArea, QToolButton,
    QSpinBox, QComboBox, QColorDialog
)

# supported image formats
IMAGE_EXTENSIONS = ('.png', '.jpg', '.jpeg', '.webp', '.bmp', '.tga')

# --- STYLES (QSS) ---
STYLESHEET = """
QWidget {
    background-color: #1a1a1a;
    color: #f0f0f0;
    font-size: 11pt;
}
#LeftFrame { background-color: #242424; }
QPushButton {
    background-color: #3f51b5; color: white; border: none;
    padding: 8px 16px; border-radius: 4px;
}
QPushButton:hover { background-color: #303f9f; }
QToolButton {
    background-color: #3f51b5; color: white; border: none;
    padding: 8px; border-radius: 4px;
    font-size: 16pt;
}
QToolButton:hover { background-color: #303f9f; }
QToolButton:disabled {
    background-color: #2a2a2a;
    color: #666666;
}
QScrollBar:vertical {
    border: none; background: #1a1a1a;
    width: 10px; margin: 0px 0px 0px 0px;
}
QScrollBar::handle:vertical {
    background: #4a4a4a; min-height: 20px; border-radius: 5px;
}
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0px; }
QSlider::groove:horizontal {
    border: 1px solid #3a3a3a; height: 4px; 
    background: #3a3a3a; margin: 2px 0; border-radius: 2px;
}
QSlider::handle:horizontal {
    background: #3f51b5; border: 1px solid #3f51b5;
    width: 14px; height: 14px;
    margin: -5px 0; border-radius: 7px;
}
QLabel {
    selection-background-color: transparent;
}
QComboBox {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    border-radius: 3px;
    padding: 5px;
    color: #f0f0f0;
}
QComboBox::drop-down {
    border: none;
}
QComboBox::down-arrow {
    image: none;
    border-left: 5px solid transparent;
    border-right: 5px solid transparent;
    border-top: 5px solid #f0f0f0;
    margin-right: 5px;
}
QComboBox QAbstractItemView {
    background-color: #2a2a2a;
    border: 1px solid #3a3a3a;
    selection-background-color: #3f51b5;
    color: #f0f0f0;
}
"""


class ImageThumbnail(QWidget):
    """A single image thumbnail widget with drag-and-drop support."""

    def __init__(self, pixmap, filename, full_path, index, parent=None):
        super().__init__(parent)
        self.original_pixmap = pixmap
        self.filename = filename
        self.full_path = full_path
        self.index = index
        self.thumbnail_size = 100
        self.is_selected = False
        self.is_dragging = False
        self.background_color = QColor(42, 42, 42)  # default dark bg

        self.drag_start_position = None
        self.drag_threshold = 5  # pixels

        layout = QVBoxLayout(self)
        layout.setContentsMargins(5, 5, 5, 5)
        layout.setSpacing(5)

        self.image_label = QLabel()
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.update_background_style()
        layout.addWidget(self.image_label)

        self.name_label = QLabel(filename)
        self.name_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.name_label.setWordWrap(True)
        self.name_label.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.name_label.setStyleSheet("""
            QLabel {
                color: #d0d0d0;
                font-size: 9pt;
                background-color: transparent;
            }
        """)
        layout.addWidget(self.name_label)

        self.setAttribute(Qt.WidgetAttribute.WA_Hover, True)
        self.update_style()
        self.update_thumbnail()

    def set_background_color(self, color):
        """Sets the background color."""
        self.background_color = color
        self.update_background_style()
        self.update_thumbnail()

    def update_background_style(self):
        """Updates the background stylesheet for the image_label."""
        self.image_label.setStyleSheet(f"""
            QLabel {{
                background-color: rgba({self.background_color.red()}, {self.background_color.green()}, 
                                       {self.background_color.blue()}, {self.background_color.alpha()});
                border-radius: 4px;
                padding: 5px;
            }}
        """)

    def set_selected(self, selected):
        """Sets the selection state."""
        self.is_selected = selected
        self.update_style()

    def update_style(self):
        """Updates the widget's style based on its state (selected, dragging)."""
        if self.is_selected or self.is_dragging:
            self.setStyleSheet("""
                QWidget {
                    background-color: #4a4a5a;
                    border: 2px solid #3f51b5;
                    border-radius: 6px;
                }
                QWidget:hover {
                    background-color: #4a4a5a;
                    border: 2px solid #5f71d5;
                    border-radius: 6px;
                }
            """)
        else:
            self.setStyleSheet("""
                QWidget {
                    background-color: transparent;
                    border: 2px solid transparent;
                    border-radius: 6px;
                }
                QWidget:hover {
                    background-color: #3a3a3a;
                    border: 2px solid #555555;
                    border-radius: 6px;
                }
            """)

    def update_thumbnail(self):
        """Renders the thumbnail pixmap, scaling it and drawing it on the background color."""
        size = self.thumbnail_size + 10
        thumbnail_with_bg = QPixmap(size, size)
        thumbnail_with_bg.fill(self.background_color)

        painter = QPainter(thumbnail_with_bg)
        scaled = self.original_pixmap.scaled(
            self.thumbnail_size, self.thumbnail_size,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation
        )
        # center the image
        x = (size - scaled.width()) // 2
        y = (size - scaled.height()) // 2
        painter.drawPixmap(x, y, scaled)
        painter.end()

        self.image_label.setPixmap(thumbnail_with_bg)
        self.image_label.setFixedSize(size, size)
        self.name_label.setFixedWidth(size)

    def set_thumbnail_size(self, size):
        """Sets the thumbnail size and triggers a rerender."""
        self.thumbnail_size = size
        self.update_thumbnail()

    def mousePressEvent(self, event):
        """Handle mouse press for selection and drag initiation."""
        if event.button() == Qt.MouseButton.LeftButton:
            modifiers = QApplication.keyboardModifiers()
            grid_widget = self.parent()

            self.drag_start_position = event.position().toPoint()

            if modifiers == Qt.KeyboardModifier.ControlModifier:
                # ctrl+click: toggle selection
                grid_widget.toggle_selection(self.index)
                self.drag_start_position = None  # don't start drag
            elif modifiers == Qt.KeyboardModifier.ShiftModifier:
                # shift+click: range selection
                grid_widget.select_range(self.index)
                self.drag_start_position = None  # don't start drag
            else:
                # simple click: select single, or prepare for drag
                if not self.is_selected:
                    grid_widget.clear_selection()
                    grid_widget.select_single(self.index)

    def mouseMoveEvent(self, event):
        """Handles mouse move. Initiates drag only after a minimum threshold."""
        if not (event.buttons() & Qt.MouseButton.LeftButton):
            return

        if self.drag_start_position is None:
            return

        distance = (event.position().toPoint() - self.drag_start_position).manhattanLength()
        if distance < self.drag_threshold:
            return

        # threshold passed, start drag
        self.start_drag(event)
        self.drag_start_position = None

    def mouseReleaseEvent(self, event):
        """Handle mouse release to reset the drag state."""
        self.drag_start_position = None
        super().mouseReleaseEvent(event)

    def start_drag(self, event):
        """Starts the drag operation for all selected thumbnails."""
        grid_widget = self.parent()
        selected_indices = grid_widget.get_selected_indices()

        if not selected_indices:
            return

        # mark all selected items as "dragging" for styling
        for idx in selected_indices:
            thumbnails = grid_widget.get_all_thumbnails()
            if idx < len(thumbnails):
                thumbnails[idx].is_dragging = True
                thumbnails[idx].update_style()

        drag = QDrag(self.window())  # <--- ОСЬ ЦЯ ЗМІНА
        mime_data = QMimeData()
        mime_data.setText(','.join(map(str, selected_indices)))
        drag.setMimeData(mime_data)

        # create a custom pixmap for the drag preview
        if len(selected_indices) == 1:
            pixmap = self.image_label.pixmap().copy()
        else:
            # show a count for multi-drag
            pixmap = self.image_label.pixmap().copy()
            painter = QPainter(pixmap)
            painter.setPen(Qt.GlobalColor.white)
            painter.setBrush(Qt.GlobalColor.blue)
            painter.drawEllipse(pixmap.width() - 30, 0, 30, 30)
            painter.drawText(pixmap.width() - 30, 0, 30, 30,
                             Qt.AlignmentFlag.AlignCenter, str(len(selected_indices)))
            painter.end()

        # make the drag pixmap semi-transparent
        transparent_pixmap = QPixmap(pixmap.size())
        transparent_pixmap.fill(Qt.GlobalColor.transparent)

        painter = QPainter(transparent_pixmap)
        painter.setOpacity(0.2)
        painter.drawPixmap(0, 0, pixmap)
        painter.end()

        drag.setPixmap(transparent_pixmap)

        # Ми залишаємо виправлення hotspot з минулого разу, про всяк випадок
        hotspot = event.position().toPoint() - QPoint(5, 5)
        hotspot.setX(max(0, min(hotspot.x(), transparent_pixmap.width() - 1)))
        hotspot.setY(max(0, min(hotspot.y(), transparent_pixmap.height() - 1)))
        drag.setHotSpot(hotspot)

        # Execute the drag
        drag.exec(Qt.DropAction.MoveAction)

        # cleanup styles after drag completed
        grid_widget.hide_end_drop_zone()
        for idx in selected_indices:
            thumbnails = grid_widget.get_all_thumbnails()
            if idx < len(thumbnails):
                thumbnails[idx].is_dragging = False
                thumbnails[idx].update_style()


class DropZone(QLabel):
    """A drop target widget ('>') placed between thumbnails for reordering."""

    def __init__(self, index, parent=None):
        super().__init__(">", parent)
        self.index = index
        self.setAlignment(Qt.AlignmentFlag.AlignCenter | Qt.AlignmentFlag.AlignTop)
        self.setFixedSize(30, 100)
        self.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)
        self.setStyleSheet("""
            QLabel {
                color: #666666;
                font-size: 24pt;
                font-weight: bold;
                background-color: transparent;
                padding-top: 15px;
            }
        """)
        self.setAcceptDrops(True)
        self.is_drag_over = False

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()
            self.is_drag_over = True
            self.update_style()

    def dragLeaveEvent(self, event):
        self.is_drag_over = False
        self.update_style()

    def dropEvent(self, event):
        if event.mimeData().hasText():
            indices_str = event.mimeData().text()
            self.parent().handle_drop(indices_str, self.index)
            event.acceptProposedAction()
            self.is_drag_over = False
            self.update_style()

    def update_style(self):
        """Updates style to show visual feedback on drag over."""
        if self.is_drag_over:
            current_text = self.text()
            # special styling for the "end drop zone" (which shows '+')
            if current_text == "+":
                self.setStyleSheet("""
                    QLabel {
                        color: #4caf50;
                        font-size: 24pt;
                        font-weight: bold;
                        background-color: #2a3a2a;
                        border: 2px dashed #4caf50;
                        padding-top: 15px;
                    }
                """)
            else:
                self.setStyleSheet("""
                    QLabel {
                        color: #3f51b5;
                        font-size: 24pt;
                        font-weight: bold;
                        background-color: #2a2a3a;
                        border: 2px dashed #3f51b5;
                        padding-top: 15px;
                    }
                """)
        else:
            # Default style
            self.setStyleSheet("""
                QLabel {
                    color: #666666;
                    font-size: 24pt;
                    font-weight: bold;
                    background-color: transparent;
                    padding-top: 15px;
                }
            """)

    def set_height(self, height):
        self.setFixedSize(30, height)


class ImageGridWidget(QWidget):
    """The main widget that holds and manages the grid of thumbnails."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.images = []  # list of (pixmap, filename, full_path)
        self.thumbnail_size = 100
        self.selected_indices = set()
        self.last_selected_index = None  # for shift-click range selection
        self.background_color = QColor(42, 42, 42)

        self.history = []
        self.redo_stack = []
        self.max_history = 50

        self.end_drop_zone = None  # the final '+' drop zone
        self.is_dragging_active = False

        self.layout = QGridLayout(self)
        self.layout.setContentsMargins(10, 10, 10, 10)
        self.layout.setSpacing(5)
        self.layout.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop)

        # timer to debounce grid rebuilds on resize
        self.resize_timer = QTimer()
        self.resize_timer.setSingleShot(True)
        self.resize_timer.timeout.connect(self.rebuild_grid)

        self.setAcceptDrops(True)
        self.setMouseTracking(True)

    def set_background_color(self, color):
        """Sets the background color for all child thumbnails."""
        self.background_color = color
        for thumbnail in self.get_all_thumbnails():
            thumbnail.set_background_color(color)

    def mousePressEvent(self, event):
        """Handles clicks on the grid's empty background to clear the selection."""
        if event.button() == Qt.MouseButton.LeftButton:
            child_at_pos = self.childAt(event.position().toPoint())

            if child_at_pos is None:
                # clicked on the empty space
                self.clear_selection()
            else:
                # check if the click was on a child of a thumbnail/dropzone
                parent_widget = child_at_pos
                is_thumbnail_or_dropzone = False

                while parent_widget is not None:
                    if isinstance(parent_widget, (ImageThumbnail, DropZone)):
                        is_thumbnail_or_dropzone = True
                        break
                    parent_widget = parent_widget.parent()

                if not is_thumbnail_or_dropzone:
                    # clicked on a grid background, but not a widget
                    self.clear_selection()

        super().mousePressEvent(event)

    def save_state(self):
        """Saves the current image order to the undo history."""
        state = [img for img in self.images]
        self.history.append(state)
        self.redo_stack.clear()
        if len(self.history) > self.max_history:
            self.history.pop(0)

    def undo(self):
        """Restores the previous state from history."""
        if len(self.history) > 0:
            current_state = [img for img in self.images]
            self.redo_stack.append(current_state)
            self.images = self.history.pop()
            self.selected_indices.clear()
            self.last_selected_index = None
            self.rebuild_grid()
            self.update_toolbar_state()
        else:
            print("Nothing to undo")

    def redo(self):
        """Restores a state from the redo stack."""
        if len(self.redo_stack) > 0:
            current_state = [img for img in self.images]
            self.history.append(current_state)
            self.images = self.redo_stack.pop()
            self.selected_indices.clear()
            self.last_selected_index = None
            self.rebuild_grid()
            self.update_toolbar_state()
        else:
            print("Nothing to redo")

    def update_toolbar_state(self):
        """Notifies the main window to update button states (e.g., delete)."""
        main_window = self.window()
        if hasattr(main_window, 'update_delete_button_state'):
            main_window.update_delete_button_state()

    def add_images(self, image_paths_and_pixmaps):
        """Replaces all images with a new set."""
        self.images = image_paths_and_pixmaps
        self.selected_indices.clear()
        self.last_selected_index = None
        self.history.clear()
        self.redo_stack.clear()
        self.rebuild_grid()
        self.update_toolbar_state()

    def append_images(self, image_paths_and_pixmaps):
        """Appends new images to the end of the list."""
        if image_paths_and_pixmaps:
            self.save_state()
            self.images.extend(image_paths_and_pixmaps)
            self.rebuild_grid()

    def calculate_columns(self):
        """Calculates the optimal number of columns based on viewport width."""
        if not self.images:
            return 1

        # item_width = thumbnail + padding + dropzone + spacing
        item_width = self.thumbnail_size + 10 + 30 + 10

        # find the parent QScrollArea to get the viewport width
        parent_scroll = self.parent()
        while parent_scroll and not isinstance(parent_scroll, QScrollArea):
            parent_scroll = parent_scroll.parent()

        if parent_scroll and hasattr(parent_scroll, 'viewport'):
            available_width = parent_scroll.viewport().width() - 40  # allow for margins/scrollbar
        else:
            available_width = self.width() - 40

        columns = max(1, available_width // item_width)
        return columns

    def rebuild_grid(self):
        """Clears and rebuilds the entire thumbnail grid layout."""
        # clear the existing layout
        while self.layout.count():
            item = self.layout.takeAt(0)
            if item.widget():
                item.widget().deleteLater()

        if not self.images:
            return

        columns = self.calculate_columns()

        for i, (pixmap, filename, full_path) in enumerate(self.images):
            row = i // columns
            col_pair = (i % columns) * 2  # each item takes 2 cols (thumbnail + dropzone)

            thumbnail = ImageThumbnail(pixmap, filename, full_path, i, self)
            thumbnail.set_thumbnail_size(self.thumbnail_size)
            thumbnail.set_background_color(self.background_color)
            thumbnail.set_selected(i in self.selected_indices)
            self.layout.addWidget(thumbnail, row, col_pair)

            # add a drop zone after each item, except the last one
            if i < len(self.images) - 1:
                drop_zone = DropZone(i + 1, self)
                drop_zone.set_height(self.thumbnail_size + 50)
                self.layout.addWidget(drop_zone, row, col_pair + 1)

        # create the final '+' drop zone
        if self.images:
            last_index = len(self.images) - 1
            last_row = last_index // columns
            last_col_pair = (last_index % columns) * 2

            self.end_drop_zone = DropZone(len(self.images), self)
            self.end_drop_zone.setText("+")
            self.end_drop_zone.set_height(self.thumbnail_size + 50)
            self.end_drop_zone.setStyleSheet("""
                QLabel {
                    color: #666666;
                    font-size: 24pt;
                    font-weight: bold;
                    background-color: transparent;
                }
            """)

            if self.is_dragging_active:
                self.layout.addWidget(self.end_drop_zone, last_row, last_col_pair + 1)

    def show_end_drop_zone(self):
        """Shows the final '+' drop zone during a drag operation."""
        if self.end_drop_zone and not self.is_dragging_active:
            self.is_dragging_active = True
            if self.images:
                columns = self.calculate_columns()
                last_index = len(self.images) - 1
                last_row = last_index // columns
                last_col_pair = (last_index % columns) * 2
                self.layout.addWidget(self.end_drop_zone, last_row, last_col_pair + 1)

                # make it a visual-only target
                self.end_drop_zone.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, True)
                self.end_drop_zone.is_drag_over = True
                self.end_drop_zone.update_style()

    def hide_end_drop_zone(self):
        """Hides the final '+' drop zone when drag ends."""
        if self.end_drop_zone and self.is_dragging_active:
            self.is_dragging_active = False
            self.end_drop_zone.is_drag_over = False
            self.end_drop_zone.update_style()
            self.end_drop_zone.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents, False)
            self.layout.removeWidget(self.end_drop_zone)
            self.end_drop_zone.setParent(None)

    def dragEnterEvent(self, event):
        if event.mimeData().hasText():
            event.acceptProposedAction()

    def dragLeaveEvent(self, event):
        """Hide the end drop zone if the drag leaves the widget area."""
        self.hide_end_drop_zone()

    def dragMoveEvent(self, event):
        """Shows the end drop zone when dragging over the widget's empty space."""
        if event.mimeData().hasText():
            event.acceptProposedAction()

            pos = event.position().toPoint()
            widget_at_pos = self.childAt(pos)

            if widget_at_pos is None:
                # dragging over empty grid space, show the end zone
                if not self.is_dragging_active:
                    self.show_end_drop_zone()
            else:
                # dragging over a thumbnail or dropzone, hide the end zone
                if self.is_dragging_active:
                    self.hide_end_drop_zone()

    def dropEvent(self, event):
        """Handles a drop on the widget's empty space (acts as drop-to-end)."""
        if event.mimeData().hasText():
            indices_str = event.mimeData().text()
            self.handle_drop(indices_str, len(self.images))
            event.acceptProposedAction()
        self.hide_end_drop_zone()

    def get_all_thumbnails(self):
        """Utility function to get all ImageThumbnail widgets from the layout."""
        thumbnails = []
        for i in range(self.layout.count()):
            widget = self.layout.itemAt(i).widget()
            if isinstance(widget, ImageThumbnail):
                thumbnails.append(widget)
        return thumbnails

    def clear_selection(self):
        """Clears the current selection."""
        self.selected_indices.clear()
        for thumbnail in self.get_all_thumbnails():
            thumbnail.set_selected(False)
        self.update_toolbar_state()

    def select_single(self, index):
        """Selects only one item."""
        self.selected_indices = {index}
        self.last_selected_index = index
        thumbnails = self.get_all_thumbnails()
        if index < len(thumbnails):
            thumbnails[index].set_selected(True)
        self.update_toolbar_state()

    def toggle_selection(self, index):
        """Toggles the selection state of one item (for Ctrl+Click)."""
        thumbnails = self.get_all_thumbnails()
        if index in self.selected_indices:
            self.selected_indices.remove(index)
            if index < len(thumbnails):
                thumbnails[index].set_selected(False)
        else:
            self.selected_indices.add(index)
            if index < len(thumbnails):
                thumbnails[index].set_selected(True)
        self.last_selected_index = index
        self.update_toolbar_state()

    def select_range(self, index):
        """Selects a range of items (for Shift+Click)."""
        if self.last_selected_index is None:
            self.select_single(index)
            return

        start = min(self.last_selected_index, index)
        end = max(self.last_selected_index, index)

        thumbnails = self.get_all_thumbnails()
        for i in range(start, end + 1):
            self.selected_indices.add(i)
            if i < len(thumbnails):
                thumbnails[i].set_selected(True)
        self.update_toolbar_state()

    def get_selected_indices(self):
        """Returns a sorted list of selected indices."""
        return sorted(list(self.selected_indices))

    def delete_selected(self):
        """Deletes all selected items."""
        if not self.selected_indices:
            return

        self.save_state()
        indices_to_delete = sorted(self.selected_indices, reverse=True)

        for idx in indices_to_delete:
            if 0 <= idx < len(self.images):
                self.images.pop(idx)

        self.selected_indices.clear()
        self.last_selected_index = None
        self.rebuild_grid()
        self.update_toolbar_state()

    def handle_drop(self, indices_str, target_index):
        """Moves items from source_indices to the target_index."""
        try:
            self.save_state()
            source_indices = sorted([int(idx) for idx in indices_str.split(',')], reverse=True)

            # get items to move
            images_to_move = []
            for idx in source_indices:
                if 0 <= idx < len(self.images):
                    images_to_move.append(self.images[idx])

            # remove items from old positions
            for idx in source_indices:
                if 0 <= idx < len(self.images):
                    self.images.pop(idx)
                    # adjust target_index if we removed an item from before it
                    if idx < target_index:
                        target_index -= 1

            # insert items at a new position
            for i, image_data in enumerate(reversed(images_to_move)):
                self.images.insert(target_index, image_data)

            # select the newly dropped items
            self.selected_indices.clear()
            for i in range(len(images_to_move)):
                self.selected_indices.add(target_index + i)

            self.hide_end_drop_zone()
            self.rebuild_grid()

        except Exception as e:
            print(f"Error handling drop: {e}")
            self.hide_end_drop_zone()

    def set_thumbnail_size(self, size):
        """Public method to change thumbnail size and rebuild grid."""
        self.thumbnail_size = size
        self.rebuild_grid()

    def resizeEvent(self, event):
        """Debounce grid rebuild on widget resize."""
        super().resizeEvent(event)
        self.resize_timer.start(100)


class FlipbookApp(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flipbook Creator")
        self.setGeometry(100, 100, 900, 600)

        self.current_icon_size = 100
        self.setWindowIcon(QIcon("icons/icon.png"))
        self.current_bg_color = QColor(42, 42, 42)  # default bg

        main_widget = QWidget()
        main_layout = QHBoxLayout(main_widget)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.setSpacing(0)
        self.setCentralWidget(main_widget)

        # install event filter to catch clicks on the background
        main_widget.installEventFilter(self)

        left_frame = QFrame()
        left_frame.setObjectName("LeftFrame")
        left_frame.setFixedWidth(250)
        left_frame_layout = QVBoxLayout(left_frame)
        left_frame_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        left_frame_layout.setSpacing(15)
        left_frame_layout.setContentsMargins(10, 10, 10, 10)

        self.folder_button = QPushButton("Select Folder")
        self.folder_button.clicked.connect(self.select_folder)
        left_frame_layout.addWidget(self.folder_button)

        grid_label = QLabel("Grid Layout:")
        grid_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        left_frame_layout.addWidget(grid_label)

        grid_layout = QHBoxLayout()
        self.columns_input = QSpinBox()
        self.columns_input.setRange(1, 100)
        self.columns_input.setValue(4)
        self.columns_input.valueChanged.connect(self.on_grid_changed)

        self.rows_input = QSpinBox()
        self.rows_input.setRange(1, 100)
        self.rows_input.setValue(4)
        self.rows_input.valueChanged.connect(self.on_grid_changed)

        grid_layout.addWidget(QLabel("Columns:"))
        grid_layout.addWidget(self.columns_input)
        grid_layout.addWidget(QLabel("Rows:"))
        grid_layout.addWidget(self.rows_input)
        left_frame_layout.addLayout(grid_layout)

        bg_label = QLabel("Add Background:")
        bg_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        left_frame_layout.addWidget(bg_label)

        bg_layout = QHBoxLayout()
        self.bg_combo = QComboBox()
        self.bg_combo.addItems(["Transparency", "Solid Color"])
        self.bg_combo.currentTextChanged.connect(self.on_background_changed)
        bg_layout.addWidget(self.bg_combo)

        self.color_picker_btn = QPushButton()
        self.color_picker_btn.setFixedSize(30, 30)
        self.color_picker_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: rgb({self.current_bg_color.red()}, {self.current_bg_color.green()}, {self.current_bg_color.blue()});
                border: 2px solid #3a3a3a;
                border-radius: 4px;
            }}
            QPushButton:hover {{
                border: 2px solid #3f51b5;
            }}
        """)
        self.color_picker_btn.clicked.connect(self.pick_background_color)
        self.color_picker_btn.setVisible(False)  # initially hidden
        bg_layout.addWidget(self.color_picker_btn)

        left_frame_layout.addLayout(bg_layout)

        scale_label = QLabel("Output Scale:")
        scale_label.setStyleSheet("font-weight: bold; margin-top: 10px;")
        left_frame_layout.addWidget(scale_label)

        scale_container = QVBoxLayout()

        scale_slider_layout = QHBoxLayout()
        self.scale_slider = QSlider(Qt.Orientation.Horizontal)
        self.scale_slider.setRange(1, 100)
        self.scale_slider.setValue(100)
        self.scale_slider.valueChanged.connect(self.on_scale_changed)

        self.scale_label = QLabel("100%")
        self.scale_label.setStyleSheet("font-weight: bold; min-width: 45px;")

        scale_slider_layout.addWidget(self.scale_slider)
        scale_slider_layout.addWidget(self.scale_label)
        scale_container.addLayout(scale_slider_layout)

        self.scale_resolution_label = QLabel("Output: 0 x 0")
        self.scale_resolution_label.setStyleSheet("color: #888888; font-size: 9pt;")
        scale_container.addWidget(self.scale_resolution_label)

        left_frame_layout.addLayout(scale_container)

        self.export_button = QPushButton("Export Flipbook")
        self.export_button.setStyleSheet("""
            QPushButton {
                background-color: #4caf50;
                font-weight: bold;
                padding: 12px;
                margin-top: 20px;
            }
            QPushButton:hover {
                background-color: #45a049;
            }
            QPushButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
        """)
        self.export_button.clicked.connect(self.export_flipbook)
        self.export_button.setEnabled(False)
        left_frame_layout.addWidget(self.export_button)

        shortcuts_label = QLabel(
            "<b>Shortcuts:</b><br>"
            "Ctrl+Z - Undo<br>"
            "Ctrl+Y / Ctrl+Shift+Z - Redo<br>"
            "Delete - Remove selected<br>"
            "Ctrl+Click - Multi-select<br>"
            "Shift+Click - Range select"
        )
        shortcuts_label.setStyleSheet("color: #888888; font-size: 9pt; margin-top: 10px;")
        shortcuts_label.setWordWrap(True)
        left_frame_layout.addWidget(shortcuts_label)

        left_frame_layout.addStretch()
        main_layout.addWidget(left_frame)

        right_zone_widget = QWidget()
        right_zone_layout = QVBoxLayout(right_zone_widget)
        right_zone_layout.setContentsMargins(10, 10, 10, 10)
        right_zone_layout.setSpacing(5)
        main_layout.addWidget(right_zone_widget, stretch=1)

        # custom QScrollArea to notify the grid widget on resize
        class CustomScrollArea(QScrollArea):
            def __init__(self, parent=None):
                super().__init__(parent)
                self.grid_widget = None

            def resizeEvent(self, event):
                super().resizeEvent(event)
                # pass resize event to grid to trigger debounced rebuild
                if self.grid_widget and hasattr(self.grid_widget, 'resize_timer'):
                    self.grid_widget.resize_timer.start(150)

        scroll_area = CustomScrollArea()
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        scroll_area.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAsNeeded)
        scroll_area.setStyleSheet("QScrollArea { border: none; background-color: #1a1a1a; }")

        self.image_grid = ImageGridWidget()
        scroll_area.setWidget(self.image_grid)
        scroll_area.grid_widget = self.image_grid  # give scroll area a reference

        self.scroll_area = scroll_area

        right_zone_layout.addWidget(scroll_area, stretch=1)

        self.add_button = QToolButton(scroll_area)
        self.add_button.setFixedSize(50, 50)
        self.add_button.setToolTip("Add images")
        self.add_button.clicked.connect(self.add_images)

        add_icon = QIcon("icons/add.png")
        if not add_icon.isNull():
            self.add_button.setIcon(add_icon)
            self.add_button.setIconSize(QSize(45, 45))
        else:
            self.add_button.setText("+")  # fallback if icon not found

        self.add_button.setStyleSheet("""
            QToolButton {
                background-color: #3f51b5;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 25px;
                font-size: 24pt;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #303f9f;
            }
        """)

        self.delete_button = QToolButton(scroll_area)
        self.delete_button.setFixedSize(50, 50)
        self.delete_button.setToolTip("Delete selected images")
        self.delete_button.setEnabled(False)
        self.delete_button.clicked.connect(self.delete_selected_images)

        delete_icon = QIcon("icons/delete.png")
        if not delete_icon.isNull():
            self.delete_button.setIcon(delete_icon)
            self.delete_button.setIconSize(QSize(45, 45))
        else:
            self.delete_button.setText("✕")  # fallback if icon not found

        self.delete_button.setStyleSheet("""
            QToolButton {
                background-color: #f44336;
                color: white;
                border: none;
                padding: 8px;
                border-radius: 25px;
                font-size: 24pt;
                font-weight: bold;
            }
            QToolButton:hover {
                background-color: #d32f2f;
            }
            QToolButton:disabled {
                background-color: #2a2a2a;
                color: #666666;
            }
        """)

        self.add_button.move(scroll_area.width() - 70, 20)
        self.delete_button.move(scroll_area.width() - 70, 80)
        self.add_button.raise_()
        self.delete_button.raise_()

        # update FAB positions on scroll area resize
        def update_button_positions():
            self.add_button.move(scroll_area.width() - 70, 20)
            self.delete_button.move(scroll_area.width() - 70, 80)

        original_resize = scroll_area.resizeEvent

        def new_resize_event(event):
            original_resize(event)
            update_button_positions()

        scroll_area.resizeEvent = new_resize_event

        slider_frame = QFrame()
        slider_frame.setFixedHeight(40)
        slider_layout = QHBoxLayout(slider_frame)
        slider_layout.setContentsMargins(0, 0, 0, 0)

        spacer = QSpacerItem(40, 20, QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Minimum)
        slider_layout.addItem(spacer)

        zoom_icon = QLabel()
        zoom_icon.setTextInteractionFlags(Qt.TextInteractionFlag.NoTextInteraction)

        zoom_pixmap = QPixmap("icons/zoom.png")
        if not zoom_pixmap.isNull():
            zoom_icon.setPixmap(zoom_pixmap.scaled(40, 40, Qt.AspectRatioMode.KeepAspectRatio,
                                                   Qt.TransformationMode.SmoothTransformation))
        else:
            zoom_icon.setText("🔎")  # fallback
            font = zoom_icon.font()
            font.setPointSize(14)
            zoom_icon.setFont(font)

        slider_layout.addWidget(zoom_icon)

        self.slider = QSlider(Qt.Orientation.Horizontal)
        self.slider.setRange(64, 256)
        self.slider.setValue(self.current_icon_size)
        self.slider.setFixedWidth(150)
        self.slider.valueChanged.connect(self.on_slider_change)
        slider_layout.addWidget(self.slider)

        right_zone_layout.addWidget(slider_frame, stretch=0)

        undo_action = QAction("Undo", self)
        undo_action.setShortcut(QKeySequence.StandardKey.Undo)
        undo_action.triggered.connect(self.undo)
        self.addAction(undo_action)

        redo_action = QAction("Redo", self)
        redo_action.setShortcut(QKeySequence("Ctrl+Shift+Z"))
        redo_action.triggered.connect(self.redo)
        self.addAction(redo_action)

        redo_action2 = QAction("Redo Alt", self)
        redo_action2.setShortcut(QKeySequence("Ctrl+Y"))
        redo_action2.triggered.connect(self.redo)
        self.addAction(redo_action2)

        delete_action = QAction("Delete", self)
        delete_action.setShortcut(QKeySequence.StandardKey.Delete)
        delete_action.triggered.connect(self.delete_selected_images)
        self.addAction(delete_action)

    def on_background_changed(self, text):
        """Handles the background type combo box change."""
        if text == "Solid Color":
            self.color_picker_btn.setVisible(True)
            self.image_grid.set_background_color(self.current_bg_color)
        else:  # Transparency
            self.color_picker_btn.setVisible(False)
            self.image_grid.set_background_color(QColor(0, 0, 0, 0))  # transparent

    def pick_background_color(self):
        """Opens the color picker dialog."""
        color = QColorDialog.getColor(self.current_bg_color, self, "Select Background Color")
        if color.isValid():
            self.current_bg_color = color
            self.color_picker_btn.setStyleSheet(f"""
                QPushButton {{
                    background-color: rgb({color.red()}, {color.green()}, {color.blue()});
                    border: 2px solid #3a3a3a;
                    border-radius: 4px;
                }}
                QPushButton:hover {{
                    border: 2px solid #3f51b5;
                }}
            """)
            self.image_grid.set_background_color(color)

    def eventFilter(self, obj, event):
        """Global event filter to clear selection when clicking outside a thumbnail."""
        if event.type() == event.Type.MouseButtonPress:
            if event.button() == Qt.MouseButton.LeftButton:
                widget = QApplication.widgetAt(event.globalPosition().toPoint())

                if widget is not None:
                    parent_widget = widget
                    is_thumbnail_or_dropzone = False

                    # check if the click was on a thumbnail or its child
                    while parent_widget is not None:
                        if isinstance(parent_widget, (ImageThumbnail, DropZone)):
                            is_thumbnail_or_dropzone = True
                            break
                        parent_widget = parent_widget.parent()

                    if not is_thumbnail_or_dropzone:
                        self.image_grid.clear_selection()

        return super().eventFilter(obj, event)

    def get_min_grid_size(self):
        """Calculates the 'squarest' grid (e.g., 17 items -> 5x4) to fit all images."""
        image_count = len(self.image_grid.images)
        if image_count == 0:
            return 1, 1

        import math
        rows = math.ceil(math.sqrt(image_count))
        cols = rows

        # try to make it rectangular if possible
        while (cols - 1) * rows >= image_count:
            cols -= 1

        return rows, cols

    def update_grid_constraints(self):
        """Prevents the user from setting a grid size too small to hold all images."""
        if not self.image_grid.images:
            self.columns_input.setMinimum(1)
            self.rows_input.setMinimum(1)
            return

        image_count = len(self.image_grid.images)
        current_cols = self.columns_input.value()
        current_rows = self.rows_input.value()

        import math
        min_rows = math.ceil(image_count / current_cols)
        min_cols = math.ceil(image_count / current_rows)

        # block signals to prevent feedback loop
        self.columns_input.blockSignals(True)
        self.rows_input.blockSignals(True)

        self.columns_input.setMinimum(min_cols)
        self.rows_input.setMinimum(min_rows)

        # autocorrect if the current value is now invalid
        if current_cols < min_cols:
            self.columns_input.setValue(min_cols)
        if current_rows < min_rows:
            self.rows_input.setValue(min_rows)

        self.columns_input.blockSignals(False)
        self.rows_input.blockSignals(False)

    def on_grid_changed(self):
        """Called when columns or rows spinbox is changed."""
        self.update_grid_constraints()
        self.update_resolution()
        self.on_scale_changed()

    def on_scale_changed(self):
        """Called when scale slider is moved."""
        scale = self.scale_slider.value()
        self.scale_label.setText(f"{scale}%")
        self.update_resolution()

    def update_resolution(self):
        """Updates the 'Output: W x H' label based on grid and scale."""
        if not self.image_grid.images:
            self.scale_resolution_label.setText("Output: 0 x 0 (Cell: 0 x 0)")
            return

        # assume all images are the same size as the first
        first_image = self.image_grid.images[0][0]
        cell_width = first_image.width()
        cell_height = first_image.height()

        columns = self.columns_input.value()
        rows = self.rows_input.value()

        total_width = cell_width * columns
        total_height = cell_height * rows

        scale = self.scale_slider.value() / 100.0

        # calculate final scaled output sizes
        output_width = int(total_width * scale)
        output_height = int(total_height * scale)

        # calculate final scaled cell sizes
        scaled_cell_width = int(cell_width * scale)
        scaled_cell_height = int(cell_height * scale)

        self.scale_resolution_label.setText(
            f"Output: {output_width} x {output_height} (Cell: {scaled_cell_width} x {scaled_cell_height})")

    def export_flipbook(self):
        """Generates and saves the final flipbook texture."""
        if not self.image_grid.images:
            print("No images to export")
            return

        file_path, selected_filter = QFileDialog.getSaveFileName(
            self,
            "Save Flipbook Texture",
            "flipbook",
            "PNG (*.png);;JPEG (*.jpg *.jpeg);;WebP (*.webp);;BMP (*.bmp);;TGA (*.tga);;TIFF (*.tiff *.tif)"
        )

        if not file_path:
            print("Export canceled")
            return

        try:
            columns = self.columns_input.value()
            rows = self.rows_input.value()

            first_pixmap = self.image_grid.images[0][0]
            cell_width = first_pixmap.width()
            cell_height = first_pixmap.height()

            original_width = cell_width * columns
            original_height = cell_height * rows

            flipbook_texture = QPixmap(original_width, original_height)

            # fill the texture based on background settings
            if self.bg_combo.currentText() == "Transparency":
                flipbook_texture.fill(Qt.GlobalColor.transparent)
            else:
                flipbook_texture.fill(self.current_bg_color)

            painter = QPainter(flipbook_texture)

            for idx, (pixmap, filename, full_path) in enumerate(self.image_grid.images):
                if idx >= columns * rows:
                    break  # stop if we have more images than grid cells

                row = idx // columns
                col = idx % columns

                x = col * cell_width
                y = row * cell_height

                # ensure the image is scaled to fit a cell if it's a different size
                if pixmap.width() != cell_width or pixmap.height() != cell_height:
                    scaled_pixmap = pixmap.scaled(
                        cell_width, cell_height,
                        Qt.AspectRatioMode.IgnoreAspectRatio,
                        Qt.TransformationMode.SmoothTransformation
                    )
                    painter.drawPixmap(x, y, scaled_pixmap)
                else:
                    painter.drawPixmap(x, y, pixmap)

            painter.end()

            # apply final output scaling
            scale = self.scale_slider.value() / 100.0
            output_width = int(original_width * scale)
            output_height = int(original_height * scale)

            if output_width != original_width or output_height != original_height:
                flipbook_texture = flipbook_texture.scaled(
                    output_width, output_height,
                    Qt.AspectRatioMode.IgnoreAspectRatio,
                    Qt.TransformationMode.SmoothTransformation
                )

            image = flipbook_texture.toImage()

            if file_path.lower().endswith(('.jpg', '.jpeg')):
                image.save(file_path, "JPEG", 95)
            elif file_path.lower().endswith('.png'):
                image.save(file_path, "PNG")
            elif file_path.lower().endswith('.webp'):
                image.save(file_path, "WEBP")
            elif file_path.lower().endswith('.bmp'):
                image.save(file_path, "BMP")
            elif file_path.lower().endswith(('.tiff', '.tif')):
                image.save(file_path, "TIFF")
            elif file_path.lower().endswith('.tga'):
                # special handling for TGA via PIL, as Qt's TGA support can be flaky
                buffer = image.bits().tobytes()
                pil_image = Image.frombytes(
                    'RGBA',
                    (image.width(), image.height()),
                    buffer,
                    'raw',
                    'BGRA'
                )
                pil_image.save(file_path, "TGA")
            else:
                # default to PNG
                image.save(file_path, "PNG")

            print(f"Flipbook exported successfully: {file_path}")

        except Exception as e:
            print(f"Error exporting flipbook: {e}")
            import traceback
            traceback.print_exc()

    def undo(self):
        """Wrapper for grid undo that also updates the UI state."""
        self.image_grid.undo()
        cols, rows = self.get_min_grid_size()
        self.columns_input.setValue(cols)
        self.rows_input.setValue(rows)
        self.update_grid_constraints()
        self.update_resolution()

    def redo(self):
        """Wrapper for grid redo that also updates the UI state."""
        self.image_grid.redo()
        cols, rows = self.get_min_grid_size()
        self.columns_input.setValue(cols)
        self.rows_input.setValue(rows)
        self.update_grid_constraints()
        self.update_resolution()

    def delete_selected_images(self):
        """Wrapper for grid delete that also updates the UI state."""
        self.image_grid.delete_selected()

        # reset the grid to the smallest possible size
        cols, rows = self.get_min_grid_size()
        self.columns_input.setValue(cols)
        self.rows_input.setValue(rows)
        self.update_grid_constraints()
        self.update_resolution()

    def update_delete_button_state(self):
        """Enables/disables the delete button based on selection."""
        has_selection = len(self.image_grid.selected_indices) > 0
        self.delete_button.setEnabled(has_selection)

    def add_images(self):
        """Opens file dialog to append images to the grid."""
        file_paths, _ = QFileDialog.getOpenFileNames(
            self,
            "Select Images to Add",
            "",
            f"Images ({' '.join(['*' + ext for ext in IMAGE_EXTENSIONS])})"
        )

        if not file_paths:
            return

        images_data = []
        for full_path in file_paths:
            filename = os.path.basename(full_path)

            if not filename.lower().endswith(IMAGE_EXTENSIONS):
                continue

            pixmap = QPixmap(full_path)

            # fallback to PIL for formats QPixmap might not support (e.g., some TGA/WebP)
            if pixmap.isNull():
                try:
                    pil_image = Image.open(full_path)
                    pil_image = pil_image.convert("RGBA")
                    data = pil_image.tobytes("raw", "RGBA")
                    q_image = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
                    pixmap = QPixmap.fromImage(q_image)

                    if pixmap.isNull():
                        continue

                except Exception as e:
                    print(f"Warning: Could not load image {full_path} with PIL: {e}")
                    continue

            images_data.append((pixmap, filename, full_path))

        if images_data:
            self.image_grid.append_images(images_data)

            cols, rows = self.get_min_grid_size()
            self.columns_input.setValue(cols)
            self.rows_input.setValue(rows)
            self.update_grid_constraints()
            self.update_resolution()

            self.export_button.setEnabled(True)

    def select_folder(self):
        """Opens the folder dialog to load and replace all images."""
        folder_path = QFileDialog.getExistingDirectory(self, "Select Image Folder")

        if not folder_path:
            return

        try:
            # load and sort all supported images from the folder
            file_list = sorted(
                [f for f in os.listdir(folder_path) if f.lower().endswith(IMAGE_EXTENSIONS)],
                key=lambda f: f.lower()
            )

            if not file_list:
                return

            images_data = []
            for filename in file_list:
                full_path = os.path.join(folder_path, filename)

                pixmap = QPixmap(full_path)

                # fallback to PIL
                if pixmap.isNull():
                    try:
                        pil_image = Image.open(full_path)
                        pil_image = pil_image.convert("RGBA")
                        data = pil_image.tobytes("raw", "RGBA")
                        q_image = QImage(data, pil_image.width, pil_image.height, QImage.Format.Format_RGBA8888)
                        pixmap = QPixmap.fromImage(q_image)

                        if pixmap.isNull():
                            continue
                    except Exception as e:
                        print(f"Warning: Could not load image {full_path} with PIL: {e}")
                        continue

                images_data.append((pixmap, filename, full_path))

            self.image_grid.add_images(images_data)

            cols, rows = self.get_min_grid_size()
            self.columns_input.setValue(cols)
            self.rows_input.setValue(rows)
            self.update_grid_constraints()
            self.update_resolution()

            self.export_button.setEnabled(True)

        except Exception as e:
            print(f"Error loading images: {e}")

    def on_slider_change(self, value):
        """Applies the thumbnail size slider value to the grid."""
        self.current_icon_size = value
        self.image_grid.set_thumbnail_size(value)

    def resizeEvent(self, event):
        """Triggers a grid rebuild on window resize."""
        super().resizeEvent(event)
        if hasattr(self, 'image_grid'):
            self.image_grid.resize_timer.start(100)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(STYLESHEET)

    window = FlipbookApp()
    window.show()

    sys.exit(app.exec())