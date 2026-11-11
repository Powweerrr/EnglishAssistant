from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


class ScreenSelector(QWidget):
    region_selected = Signal(QRect)
    selection_cancelled = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.WindowType.FramelessWindowHint | Qt.WindowType.WindowStaysOnTopHint | Qt.WindowType.Tool)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)
        self.start_point = QPoint()
        self.current_point = QPoint()
        self.selecting = False

    def show_selector(self):
        screen = QApplication.primaryScreen()
        if screen is None:
            self.selection_cancelled.emit()
            return
        self.start_point = QPoint()
        self.current_point = QPoint()
        self.selecting = False
        self.setGeometry(screen.geometry())
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def selection_rect(self) -> QRect:
        return QRect(self.start_point, self.current_point).normalized()

    def paintEvent(self, event):
        del event
        painter = QPainter(self)
        painter.fillRect(self.rect(), QColor(0, 0, 0, 115))
        if self.selecting:
            rect = self.selection_rect()
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_Clear)
            painter.fillRect(rect, Qt.GlobalColor.transparent)
            painter.setCompositionMode(QPainter.CompositionMode.CompositionMode_SourceOver)
            painter.setPen(QPen(QColor(70, 170, 255), 2))
            painter.drawRect(rect)

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.start_point = event.position().toPoint()
            self.current_point = self.start_point
            self.selecting = True
            self.update()

    def mouseMoveEvent(self, event):
        if self.selecting:
            self.current_point = event.position().toPoint()
            self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton or not self.selecting:
            return
        self.current_point = event.position().toPoint()
        self.selecting = False
        rect = self.selection_rect()
        self.hide()
        if rect.width() < 5 or rect.height() < 5:
            self.selection_cancelled.emit()
        else:
            self.region_selected.emit(rect)

    def keyPressEvent(self, event):
        if event.key() == Qt.Key.Key_Escape:
            self.selecting = False
            self.hide()
            self.selection_cancelled.emit()
            return
        super().keyPressEvent(event)
