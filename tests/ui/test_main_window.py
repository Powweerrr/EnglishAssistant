from PySide6.QtWidgets import QLabel

from english_assistant.ui.main_window import MainWindow


def test_main_window_title(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "English Assistant"


def test_main_window_initial_status(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    status = window.findChild(QLabel, "statusText")

    assert status is not None
    assert "English Assistant запущен." in status.text()