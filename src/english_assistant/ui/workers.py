from collections.abc import Callable
from PySide6.QtCore import QThread, Signal


class TaskWorker(QThread):
    succeeded = Signal(object)
    failed = Signal(str)

    def __init__(self, task: Callable, parent=None):
        super().__init__(parent)
        self.task = task

    def run(self):
        try:
            self.succeeded.emit(self.task())
        except Exception as error:  # noqa: BLE001 - передача ошибки в GUI
            self.failed.emit(str(error))
