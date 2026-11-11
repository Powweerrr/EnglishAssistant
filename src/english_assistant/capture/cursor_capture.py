from __future__ import annotations

from dataclasses import dataclass

from PIL import Image


@dataclass(frozen=True, slots=True)
class CursorCapture:
    image: Image.Image
    origin_x: int
    origin_y: int
    cursor_x: int
    cursor_y: int


def capture_around_cursor(x: int, y: int, width: int = 520, height: int = 220) -> CursorCapture:
    """Capture a small physical-pixel region around the pointer using Desktop Duplication."""
    try:
        import mss
    except ImportError as error:  # pragma: no cover - dependency is installed by the app
        raise RuntimeError("Для поиска слова под курсором не установлен пакет mss.") from error

    with mss.mss() as capture:
        monitors = capture.monitors[1:]
        monitor = next(
            (m for m in monitors
             if m["left"] <= x < m["left"] + m["width"]
             and m["top"] <= y < m["top"] + m["height"]),
            None,
        )
        if monitor is None:
            raise RuntimeError("Не удалось определить монитор под курсором.")

        left = max(monitor["left"], min(x - width // 2, monitor["left"] + monitor["width"] - width))
        top = max(monitor["top"], min(y - height // 2, monitor["top"] + monitor["height"] - height))
        right = min(monitor["left"] + monitor["width"], left + width)
        bottom = min(monitor["top"] + monitor["height"], top + height)
        region = {"left": left, "top": top, "width": right - left, "height": bottom - top}
        shot = capture.grab(region)
        image = Image.frombytes("RGB", shot.size, shot.rgb)
        return CursorCapture(image, left, top, x, y)
