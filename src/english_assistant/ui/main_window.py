from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout,
    QLabel,
    QMainWindow,
    QPlainTextEdit,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Основное рабочее окно EnglishAssistant."""

    capture_requested = Signal()

    def __init__(self):
        super().__init__()

        self.setWindowTitle("EnglishAssistant")
        self.resize(1050, 650)
        self.setMinimumSize(700, 450)

        self.preview_pixmap = None

        self._create_interface()

    def _create_interface(self):
        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(18, 18, 18, 18)
        main_layout.setSpacing(12)

        toolbar = QHBoxLayout()

        self.capture_button = QPushButton("Выделить текст на экране")
        self.capture_button.setObjectName("captureButton")
        self.capture_button.setMinimumHeight(42)
        self.capture_button.clicked.connect(self.capture_requested.emit)

        self.status_label = QLabel("Готов к работе")
        self.status_label.setObjectName("statusLabel")

        toolbar.addWidget(self.capture_button)
        toolbar.addWidget(self.status_label, 1)

        splitter = QSplitter(Qt.Orientation.Horizontal)

        self.preview_label = QLabel("Здесь появится снимок экрана")
        self.preview_label.setObjectName("previewLabel")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(250, 250)
        self.preview_label.setStyleSheet(
            """
            QLabel {
                background: #202124;
                color: #b8b8b8;
                border: 1px solid #444444;
                border-radius: 8px;
                padding: 10px;
            }
            """
        )

        self.text_output = QPlainTextEdit()
        self.text_output.setObjectName("recognizedText")
        self.text_output.setReadOnly(True)
        self.text_output.setPlaceholderText(
            "Распознанный английский текст появится здесь..."
        )

        splitter.addWidget(self.preview_label)
        splitter.addWidget(self.text_output)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 1)

        main_layout.addLayout(toolbar)
        main_layout.addWidget(splitter, 1)

    def set_preview(self, pixmap: QPixmap):
        """Показывает снимок выделенной области."""
        self.preview_pixmap = pixmap
        self._update_preview()

    def _update_preview(self):
        if self.preview_pixmap is None:
            return

        scaled = self.preview_pixmap.scaled(
            self.preview_label.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        self.preview_label.setPixmap(scaled)

    def set_ocr_text(self, text: str):
        """Выводит распознанный текст."""
        if text:
            self.text_output.setPlainText(text)
            self.status_label.setText("Текст успешно распознан")
        else:
            self.text_output.clear()
            self.status_label.setText("Текст на изображении не найден")

    def set_ocr_busy(self, busy: bool):
        self.capture_button.setEnabled(not busy)

        if busy:
            self.status_label.setText("Распознавание текста...")

    def show_error(self, message: str):
        self.status_label.setText("Ошибка")
        self.text_output.setPlainText(message)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview()
