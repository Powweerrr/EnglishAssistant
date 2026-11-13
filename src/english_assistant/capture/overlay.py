"""Full-screen screen capture overlay for EnglishAssistant."""

from __future__ import annotations

import mss
from PIL import Image
from PySide6.QtCore import QPoint, QRect, Qt, Signal
from PySide6.QtGui import (
    QColor,
    QGuiApplication,
    QImage,
    QKeyEvent,
    QMouseEvent,
    QPainter,
    QPaintEvent,
    QPen,
    QPixmap,
)
from PySide6.QtWidgets import QWidget


class ScreenCaptureOverlay(QWidget):
    """Frameless top-most widget that lets the user select a screen region."""

    image_selected = Signal(object)
    canceled = Signal()

    MIN_SELECTION_SIZE = 5
    MASK_ALPHA = 120

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)

        self.setWindowFlags(
            Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.Tool
        )
        # Окно непрозрачное, мы сами рисуем замороженный скриншот.
        # WA_TranslucentBackground вызывал черный экран на Windows.
        self.setAttribute(Qt.WidgetAttribute.WA_OpaquePaintEvent, True)
        self.setAttribute(Qt.WidgetAttribute.WA_DeleteOnClose, False)
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        self.setMouseTracking(True)
        self.setCursor(Qt.CursorShape.CrossCursor)

        self._full_image: Image.Image | None = None
        self._background_pixmap = QPixmap()
        self._origin: QPoint | None = None
        self._current: QPoint | None = None
        self._dragging = False

    def start_capture(self) -> None:
        if self.isVisible():
            return

        geometry = self._compute_virtual_geometry()
        self.setGeometry(geometry)

        try:
            self._full_image = self._grab_all_screens()
        except Exception:
            self._full_image = None
            self._background_pixmap = QPixmap()
            self.hide()
            self.canceled.emit()
            return

        self._background_pixmap = self._pil_to_pixmap(self._full_image).scaled(
            self.size(),
            Qt.AspectRatioMode.IgnoreAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self._reset_selection()
        self.show()
        self.raise_()
        self.activateWindow()
        self.setFocus(Qt.FocusReason.ActiveWindowFocusReason)

    def cancel_capture(self) -> None:
        self.hide()
        self._reset_selection()
        self._full_image = None
        self._background_pixmap = QPixmap()
        self.canceled.emit()

    def _compute_virtual_geometry(self) -> QRect:
        screens = QGuiApplication.screens()
        if not screens:
            return QRect(0, 0, 1, 1)

        geometry = QRect(screens[0].geometry())
        for screen in screens[1:]:
            geometry = geometry.united(screen.geometry())
        return geometry

    def _grab_all_screens(self) -> Image.Image:
        with mss.mss() as sct:
            monitor = sct.monitors[0]
            shot = sct.grab(monitor)
            return Image.frombytes(
                "RGB",
                shot.size,
                shot.bgra,
                "raw",
                "BGRX",
            )

    def _pil_to_pixmap(self, image: Image.Image) -> QPixmap:
        rgba = image.convert("RGBA")
        data = rgba.tobytes("raw", "RGBA")
        qimage = QImage(
            data,
            rgba.width,
            rgba.height,
            rgba.width * 4,
            QImage.Format.Format_RGBA8888,
        ).copy()
        return QPixmap.fromImage(qimage)

    def _reset_selection(self) -> None:
        self._origin = None
        self._current = None
        self._dragging = False
        self.update()

    def _selection_rect(self) -> QRect:
        if self._origin is None or self._current is None:
            return QRect()
        rect = QRect(self._origin, self._current).normalized()
        return rect.intersected(self.rect())

    def _crop_selected_image(self, rect: QRect) -> Image.Image:
        if self._full_image is None:
            raise RuntimeError("No screenshot is available for cropping.")

        image_width, image_height = self._full_image.size
        widget_width = max(1, self.width())
        widget_height = max(1, self.height())

        scale_x = image_width / widget_width
        scale_y = image_height / widget_height

        left = int(round(rect.left() * scale_x))
        top = int(round(rect.top() * scale_y))
        right = int(round((rect.left() + rect.width()) * scale_x))
        bottom = int(round((rect.top() + rect.height()) * scale_y))

        left = max(0, min(left, image_width - 1))
        top = max(0, min(top, image_height - 1))
        right = max(left + 1, min(right, image_width))
        bottom = max(top + 1, min(bottom, image_height))

        return self._full_image.crop((left, top, right, bottom))

    def _finish_selection(self) -> None:
        rect = self._selection_rect()

        if (
            rect.width() < self.MIN_SELECTION_SIZE
            or rect.height() < self.MIN_SELECTION_SIZE
        ):
            self.cancel_capture()
            return

        try:
            image = self._crop_selected_image(rect)
        except Exception:
            self.cancel_capture()
            return

        self.hide()
        self._reset_selection()
        self._full_image = None
        self._background_pixmap = QPixmap()
        self.image_selected.emit(image)

    def mousePressEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton:
            point = event.position().toPoint()
            self._origin = point
            self._current = point
            self._dragging = True
            self.update()
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event: QMouseEvent) -> None:
        if self._dragging:
            self._current = event.position().toPoint()
            self.update()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event: QMouseEvent) -> None:
        if event.button() == Qt.MouseButton.LeftButton and self._dragging:
            self._current = event.position().toPoint()
            self._dragging = False
            self._finish_selection()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def keyPressEvent(self, event: QKeyEvent) -> None:
        if event.key() == Qt.Key.Key_Escape:
            self.cancel_capture()
            event.accept()
            return
        super().keyPressEvent(event)

    def paintEvent(self, event: QPaintEvent) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)

        # 1. Фон (замороженный скриншот)
        if not self._background_pixmap.isNull():
            painter.drawPixmap(self.rect(), self._background_pixmap)
        else:
            painter.fillRect(self.rect(), QColor(30, 30, 30))

        # 2. Затемнение
        painter.fillRect(self.rect(), QColor(0, 0, 0, self.MASK_ALPHA))

        # 3. "Дыра" (чистый скриншот внутри рамки)
        selection = self._selection_rect()
        if not selection.isEmpty() and not self._background_pixmap.isNull():
            painter.save()
            painter.setClipRect(selection)
            painter.drawPixmap(self.rect(), self._background_pixmap)
            painter.restore()

            # 4. Рамка и текст
            painter.setPen(QPen(QColor(0, 180, 255), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.drawRect(selection.adjusted(0, 0, -1, -1))

            painter.setPen(QColor(255, 255, 255))
            painter.drawText(
                selection.adjusted(4, 4, 0, 0),
                Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignTop,
                f"{selection.width()} x {selection.height()}",
            )

        painter.end()