from __future__ import annotations

from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QHBoxLayout, QLabel, QMainWindow, QPlainTextEdit, QPushButton,
    QSplitter, QVBoxLayout, QWidget,
)

from english_assistant.ui.domain_workspace import DomainWorkspace


class MainWindow(QMainWindow):
    capture_requested = Signal()
    quick_lookup_requested = Signal()

    def __init__(self):
        super().__init__()
        self.setWindowTitle("EnglishAssistant")
        self.resize(1450, 850)
        self.setMinimumSize(1000, 650)
        self.preview_pixmap: QPixmap | None = None
        self._build()

    def _build(self):
        central = QWidget()
        self.setCentralWidget(central)
        layout = QVBoxLayout(central)
        layout.setContentsMargins(12, 12, 12, 12)
        layout.setSpacing(8)
        toolbar = QHBoxLayout()
        self.quick_lookup_button = QPushButton("Слово под курсором · Alt+Q")
        self.quick_lookup_button.setMinimumHeight(40)
        self.quick_lookup_button.clicked.connect(self.quick_lookup_requested.emit)
        self.capture_button = QPushButton("Перевести область · Ctrl+Shift+E")
        self.capture_button.setMinimumHeight(40)
        self.capture_button.clicked.connect(self.capture_requested.emit)
        self.status_label = QLabel("Готов к работе")
        toolbar.addWidget(self.quick_lookup_button)
        toolbar.addWidget(self.capture_button)
        toolbar.addWidget(self.status_label, 1)
        layout.addLayout(toolbar)

        splitter = QSplitter(Qt.Orientation.Horizontal)
        left = QWidget()
        left_layout = QVBoxLayout(left)
        left_layout.setContentsMargins(0, 0, 0, 0)
        left_layout.addWidget(QLabel("Снимок выделенной области"))
        self.preview_label = QLabel("Здесь появится снимок экрана")
        self.preview_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.preview_label.setMinimumSize(260, 220)
        self.preview_label.setStyleSheet("QLabel { background:#202124; color:#b8b8b8; border:1px solid #444; border-radius:8px; padding:8px; }")
        left_layout.addWidget(self.preview_label, 1)
        left_layout.addWidget(QLabel("Распознанный текст · можно исправить вручную"))
        self.text_output = QPlainTextEdit()
        self.text_output.setPlaceholderText("После OCR здесь появится распознанный текст. Можно также вставить его вручную.")
        self.text_output.textChanged.connect(self._sync_domain_text)
        left_layout.addWidget(self.text_output, 1)
        self.domains = DomainWorkspace()
        splitter.addWidget(left)
        splitter.addWidget(self.domains)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        layout.addWidget(splitter, 1)

    def _sync_domain_text(self):
        if self.domains.input.toPlainText() != self.text_output.toPlainText():
            self.domains.set_input_text(self.text_output.toPlainText())

    def set_preview(self, pixmap: QPixmap):
        self.preview_pixmap = pixmap
        self._update_preview()

    def _update_preview(self):
        if self.preview_pixmap is not None:
            self.preview_label.setPixmap(self.preview_pixmap.scaled(
                self.preview_label.size(), Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation))

    def set_ocr_text(self, text: str):
        self.text_output.blockSignals(True)
        self.text_output.setPlainText(text)
        self.text_output.blockSignals(False)
        self.domains.set_input_text(text)
        self.status_label.setText("Текст распознан" if text else "Текст на изображении не найден")

    def set_ocr_busy(self, busy: bool):
        self.capture_button.setEnabled(not busy)
        if busy:
            self.status_label.setText("Распознавание текста…")

    def show_error(self, message: str):
        self.status_label.setText("Ошибка OCR")
        self.text_output.setPlainText(message)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._update_preview()
