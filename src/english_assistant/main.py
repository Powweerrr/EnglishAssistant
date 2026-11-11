from __future__ import annotations

import sys

from PySide6.QtCore import QObject, QThread, QTimer, Signal
from PySide6.QtGui import QCursor, QPixmap
from PySide6.QtWidgets import QApplication

from english_assistant.capture.screen_capture import capture_region
from english_assistant.capture.screen_selector import ScreenSelector
from english_assistant.lookup.worker import QuickLookupWorker
from english_assistant.ocr.worker import OcrWorker
from english_assistant.ui.lookup_overlay import LookupOverlay
from english_assistant.ui.main_window import MainWindow


class HotkeyBridge(QObject):
    capture_triggered = Signal()
    quick_lookup_triggered = Signal()


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("EnglishAssistant")
    app.setOrganizationName("EnglishAssistant")
    window = MainWindow()
    selector = ScreenSelector()
    overlay = LookupOverlay()
    workers: list[QThread] = []
    bridge = HotkeyBridge()
    lookup_generation = 0

    def track_worker(worker):
        workers.append(worker)

        def finished():
            if worker in workers:
                workers.remove(worker)
            worker.deleteLater()

        worker.finished.connect(finished)
        worker.start()

    def start_ocr(pixmap: QPixmap):
        window.set_ocr_busy(True)
        worker = OcrWorker(pixmap, window)
        worker.succeeded.connect(window.set_ocr_text)
        worker.failed.connect(window.show_error)

        def finished():
            window.set_ocr_busy(False)

        worker.finished.connect(finished)
        track_worker(worker)

    def start_capture():
        overlay.hide()
        window.hide()
        QTimer.singleShot(180, selector.show_selector)

    def selected(region):
        def process():
            try:
                pixmap = capture_region(region)
                window.set_preview(pixmap)
                window.show()
                window.raise_()
                window.activateWindow()
                start_ocr(pixmap)
            except (RuntimeError, ValueError, OSError) as error:
                window.show()
                window.show_error(str(error))
        QTimer.singleShot(160, process)

    def cancelled():
        window.show()
        window.raise_()
        window.activateWindow()

    def start_quick_lookup():
        nonlocal lookup_generation
        lookup_generation += 1
        generation = lookup_generation
        if overlay.isVisible():
            overlay.hide()
            return
        point = QCursor.pos()
        overlay.show_loading()
        worker = QuickLookupWorker(point.x(), point.y(), window)
        worker.succeeded.connect(
            lambda result, request_id=generation:
                overlay.show_result(result) if request_id == lookup_generation else None
        )
        worker.failed.connect(
            lambda message, request_id=generation:
                overlay.show_error(message) if request_id == lookup_generation else None
        )
        track_worker(worker)

    window.capture_requested.connect(start_capture)
    window.quick_lookup_requested.connect(start_quick_lookup)
    bridge.capture_triggered.connect(start_capture)
    bridge.quick_lookup_triggered.connect(start_quick_lookup)
    selector.region_selected.connect(selected)
    selector.selection_cancelled.connect(cancelled)

    hotkey_listener = None
    try:
        from pynput import keyboard
        hotkey_listener = keyboard.GlobalHotKeys({
            "<ctrl>+<shift>+e": bridge.capture_triggered.emit,
            "<alt>+q": bridge.quick_lookup_triggered.emit,
        })
        hotkey_listener.start()
    except (ImportError, OSError):
        window.status_label.setText("Готов · глобальные клавиши недоступны в этой системе")

    def wait_workers():
        if hotkey_listener is not None:
            hotkey_listener.stop()
        for worker in tuple(workers):
            worker.wait(5000)

    app.aboutToQuit.connect(wait_workers)
    window.show()
    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
