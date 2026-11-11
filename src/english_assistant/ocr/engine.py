from __future__ import annotations

from io import BytesIO

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QPixmap

from english_assistant.ocr.runtime import _OCR_LOCK, get_engine


def normalize_ocr_lines(lines) -> str:
    if not lines:
        return ""
    return "\n".join(line.strip() for line in lines if line and line.strip())


def pixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    if pixmap.isNull():
        raise ValueError("Получено пустое изображение.")
    buffer = QBuffer()
    buffer.open(QIODevice.OpenModeFlag.WriteOnly)
    if not pixmap.save(buffer, "PNG"):
        raise RuntimeError("Не удалось подготовить изображение для OCR.")
    raw = bytes(buffer.data())
    buffer.close()
    return Image.open(BytesIO(raw)).convert("RGB")


def recognize_text(pixmap: QPixmap) -> str:
    with _OCR_LOCK:
        result = get_engine()(pixmap_to_pil(pixmap))
    lines = getattr(result, "txts", None)
    if lines is None and isinstance(result, tuple) and result:
        lines = result[0]
    return normalize_ocr_lines(lines)
