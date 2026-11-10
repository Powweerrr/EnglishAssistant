import sys

from PySide6.QtCore import QTimer
from PySide6.QtWidgets import QApplication

from english_assistant.capture.screen_capture import capture_region
from english_assistant.capture.screen_selector import ScreenSelector
from english_assistant.ocr.worker import OcrWorker
from english_assistant.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)

    window = MainWindow()
    selector = ScreenSelector()

    active_workers = []

    def start_ocr(pixmap):
        """Запускает распознавание в фоновом потоке."""
        window.set_ocr_busy(True)

        worker = OcrWorker(pixmap, window)
        active_workers.append(worker)

        worker.succeeded.connect(window.set_ocr_text)
        worker.failed.connect(window.show_error)

        def finish_worker():
            window.set_ocr_busy(False)

            if worker in active_workers:
                active_workers.remove(worker)

        worker.finished.connect(finish_worker)
        worker.finished.connect(worker.deleteLater)
        worker.start()

    def start_capture():
        """Скрывает окно и запускает выделение области."""
        window.hide()
        QTimer.singleShot(250, selector.show_selector)

    def handle_selection(region):
        """Получает выделение и запускает захват с последующим OCR."""

        def process_capture():
            try:
                pixmap = capture_region(region)
                window.set_preview(pixmap)
                window.show()
                window.raise_()
                window.activateWindow()

                start_ocr(pixmap)

            except Exception as error:  # noqa: BLE001 - обрабатываем ошибку захвата экрана
                window.show()
                window.show_error(str(error))

        # Захват выполняется после скрытия окна выделения.
        QTimer.singleShot(150, process_capture)

    def handle_cancel():
        window.show()
        window.raise_()
        window.activateWindow()

    def wait_for_workers():
        """Не позволяет закрыть приложение во время выполнения OCR."""
        for worker in tuple(active_workers):
            worker.wait()

    window.capture_requested.connect(start_capture)
    selector.region_selected.connect(handle_selection)
    selector.selection_cancelled.connect(handle_cancel)

    app.aboutToQuit.connect(wait_for_workers)

    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())
