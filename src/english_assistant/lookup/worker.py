from __future__ import annotations

from PySide6.QtCore import QThread, Signal

from english_assistant.capture.cursor_capture import capture_around_cursor
from english_assistant.lookup.quick_lookup import QuickLookupResult, QuickLookupService
from english_assistant.ocr.word_locator import locate_word
from english_assistant.ocr.uia_text import locate_accessible_word
from english_assistant.ocr.word_locator import LocatedWord


class QuickLookupWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, x: int, y: int, parent=None):
        super().__init__(parent)
        self.x = x
        self.y = y

    def run(self):
        try:
            accessible = locate_accessible_word(self.x, self.y)
            if accessible is not None:
                located = LocatedWord(
                    word=accessible.word,
                    context=accessible.context,
                    confidence=1.0,
                    bounds=accessible.bounds or (self.x, self.y, self.x, self.y),
                    method=accessible.method,
                )
            else:
                capture = capture_around_cursor(self.x, self.y)
                located = locate_word(capture)
            result: QuickLookupResult = QuickLookupService().lookup(located)
            self.succeeded.emit(result)
        except Exception as error:  # noqa: BLE001 - worker boundary
            self.failed.emit(str(error))
