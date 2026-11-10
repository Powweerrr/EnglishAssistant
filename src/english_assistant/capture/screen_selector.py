from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtWidgets import QApplication, QWidget


class ScreenSelector(QWidget):
    """Полупрозрачное окно для выделения области экрана."""

    region_selected = Signal(QRect)
    selection_cancelled = Signal()

    def __init__(self):
        super().__init__()

        # Окно без рамки, поверх остальных окон.
        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )

        # Разрешаем рисовать прозрачные участки окна.
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.setMouseTracking(True)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self.start_point = QPoint()
        self.current_point = QPoint()
        self.is_selecting = False

    def show_selector(self):
        """Показывает область выделения на основном мониторе."""
        screen = QApplication.primaryScreen()

        if screen is None:
            self.selection_cancelled.emit()
            return

        self.start_point = QPoint()
        self.current_point = QPoint()
        self.is_selecting = False

        self.setGeometry(screen.geometry())
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus()

    def selected_rectangle(self) -> QRect:
        """Возвращает нормализованный прямоугольник выделения."""
        return QRect(self.start_point, self.current_point).normalized()

    def paintEvent(self, event):
        del event

        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Затемняем весь экран, чтобы выделение было заметнее.
        painter.fillRect(self.rect(), QColor(0, 0, 0, 115))

        if self.is_selecting:
            selection = self.selected_rectangle()

            # Вырезаем выделенную область из затемнения.
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_Clear
            )
            painter.fillRect(selection, Qt.GlobalColor.transparent)

            # Рисуем рамку поверх прозрачной области.
            painter.setCompositionMode(
                QPainter.CompositionMode.CompositionMode_SourceOver
            )
            painter.setPen(QPen(QColor(70, 170, 255), 2))
            painter.drawRect(selection)

    def mousePressEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        self.start_point = event.position().toPoint()
        self.current_point = self.start_point
        self.is_selecting = True
        self.update()

    def mouseMoveEvent(self, event):
        if not self.is_selecting:
            return

        self.current_point = event.position().toPoint()
        self.update()

    def mouseReleaseEvent(self, event):
        if event.button() != Qt.MouseButton.LeftButton:
            return

        if not self.is_selecting:
            return

        self.current_point = event.position().toPoint()
        self.is_selecting = False

        selection = self.selected_rectangle()
        self.hide()

        # Не принимаем случайные клики вместо выделения.
        if selection.width() < 5 or selection.height() < 5:
            self.selection_cancelled.emit()
            return

        self.region_selected.emit(selection)

    def keyPressEvent(self, event):
        # Escape отменяет выделение и возвращает пользователя в приложение.
        if event.key() == Qt.Key.Key_Escape:
            self.is_selecting = False
            self.hide()
            self.selection_cancelled.emit()
            return

        super().keyPressEvent(event)