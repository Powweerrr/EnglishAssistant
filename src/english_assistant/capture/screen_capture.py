from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication


def capture_region(region: QRect) -> QPixmap:
    screen = QApplication.primaryScreen()
    if screen is None:
        raise RuntimeError("Не удалось определить основной монитор.")
    if region.isEmpty():
        raise ValueError("Выделенная область пуста.")
    pixmap = screen.grabWindow(0, region.x(), region.y(), region.width(), region.height())
    if pixmap.isNull():
        raise RuntimeError("Не удалось получить снимок экрана.")
    return pixmap
