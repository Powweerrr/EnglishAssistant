from PySide6.QtCore import QThread, Signal
from PySide6.QtGui import QPixmap

from english_assistant.ocr.engine import recognize_text


class OcrWorker(QThread):
    succeeded = Signal(str)
    failed = Signal(str)

    def __init__(self, pixmap: QPixmap, parent=None):
        super().__init__(parent)
        self.pixmap = pixmap

    def run(self):
        try:
            self.succeeded.emit(recognize_text(self.pixmap))
        except Exception as error:  # noqa: BLE001 - сообщаем об ошибке через сигнал потока
            self.failed.emit(str(error))
