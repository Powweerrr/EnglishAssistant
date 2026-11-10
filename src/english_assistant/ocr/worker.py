from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap

from english_assistant.ocr.engine import recognize_text


class OcrWorker(QThread):
    """Выполняет OCR вне главного потока интерфейса."""

    succeeded = Signal(str)
    failed = Signal(str)

    def __init(self, pixmap: QPixmap, parent=None):
        super().__init(parent)
        self.pixmap = pixmap

    def run(self):
        try:
            recognized_text = recognize_text(self.pixmap)
            self.succeeded.emit(recognized_text)
        except Exception as error:  # noqa: BLE001 - передаём ошибку через сигнал потока
            self.failed.emit(str(error))