from PySide6.QtWidgets import QLabel, QPlainTextEdit, QPushButton

from english_assistant.ui.main_window import MainWindow


def test_main_window_opens(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.windowTitle() == "EnglishAssistant"
    assert window.isVisible() is False


def test_capture_button_exists(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    button = window.findChild(QPushButton, "captureButton")

    assert button is not None
    assert button.text() == "Выделить текст на экране"


def test_preview_label_exists(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    assert window.findChild(QLabel, "previewLabel") is not None


def test_recognized_text_output_exists(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    output = window.findChild(QPlainTextEdit, "recognizedText")

    assert output is not None


def test_capture_button_emits_signal(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    with qtbot.waitSignal(window.capture_requested, timeout=1000):
        window.capture_button.click()


def test_ocr_text_is_displayed(qtbot):
    window = MainWindow()
    qtbot.addWidget(window)

    window.set_ocr_text("Hello world")

    assert window.text_output.toPlainText() == "Hello world"
    assert window.status_label.text() == "Текст успешно распознан"
