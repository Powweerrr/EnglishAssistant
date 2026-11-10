from PySide6.QtCore import QRect
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import QApplication


def capture_region(region: QRect) -> QPixmap:
    """
    Создаёт снимок выделенной области основного монитора.

    Координаты region должны быть локальными координатами
    основного монитора. Перед захватом окно выделения уже скрывается.
    """
    screen = QApplication.primaryScreen()

    if screen is None:
        raise RuntimeError("Не удалось определить основной монитор.")

    if region.isEmpty():
        raise ValueError("Нельзя сделать снимок пустой области.")

    # Qt самостоятельно получает изображение рабочего стола.
    screenshot = screen.grabWindow(
        0,
        region.x(),
        region.y(),
        region.width(),
        region.height(),
    )

    if screenshot.isNull():
        raise RuntimeError("Не удалось получить снимок экрана.")

    return screenshot