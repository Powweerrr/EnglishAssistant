from collections.abc import Iterable
from functools import lru_cache
from io import BytesIO

from PIL import Image
from PySide6.QtCore import QBuffer, QIODevice
from PySide6.QtGui import QPixmap


def normalize_ocr_lines(lines: Iterable[str] | None) -> str:
    """Удаляет пустые строки и объединяет распознанный текст."""
    if not lines:
        return ""

    cleaned = [
        line.strip()
        for line in lines
        if line and line.strip()
    ]

    return "\n".join(cleaned)


@lru_cache(maxsize=1)
def get_ocr_engine():
    """Создаёт OCR-движок один раз и использует его повторно."""
    from rapidocr import RapidOCR

    return RapidOCR()


def pixmap_to_pil(pixmap: QPixmap) -> Image.Image:
    """Преобразует Qt-изображение в формат Pillow для RapidOCR."""
    if pixmap.isNull():
        raise ValueError("Получено пустое изображение.")

    image_buffer = QBuffer()
    image_buffer.open(QIODevice.OpenModeFlag.WriteOnly)

    if not pixmap.save(image_buffer, "PNG"):
        raise RuntimeError("Не удалось подготовить изображение для OCR.")

    image_bytes = bytes(image_buffer.data())
    image_buffer.close()

    return Image.open(BytesIO(image_bytes)).convert("RGB")


def recognize_text(pixmap: QPixmap) -> str:
    """Распознаёт текст на снимке экрана."""
    image = pixmap_to_pil(pixmap)
    engine = get_ocr_engine()

    result = engine(image)

    return normalize_ocr_lines(result.txts)