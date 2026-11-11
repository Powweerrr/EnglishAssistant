from __future__ import annotations

from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QCursor
from PySide6.QtWidgets import QApplication, QFrame, QLabel, QVBoxLayout

from english_assistant.lookup.quick_lookup import QuickLookupResult


class LookupOverlay(QFrame):
    """Small non-activating popup placed next to the pointer."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowFlags(
            Qt.WindowType.Tool
            | Qt.WindowType.FramelessWindowHint
            | Qt.WindowType.WindowStaysOnTopHint
            | Qt.WindowType.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating, True)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground, False)
        self.setObjectName("lookupOverlay")
        self.setFixedWidth(390)
        self.setStyleSheet("""
            QFrame#lookupOverlay { background:#20242c; border:1px solid #536174; border-radius:12px; }
            QLabel { color:#edf2f7; background:transparent; }
            QLabel#word { color:#8ec5ff; font-size:20px; font-weight:700; }
            QLabel#translation { color:#a8e6b0; font-size:16px; font-weight:600; }
            QLabel#muted { color:#aab4c2; font-size:11px; }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(14, 12, 14, 12)
        layout.setSpacing(6)
        self.word_label = QLabel("Слово")
        self.word_label.setObjectName("word")
        self.translation_label = QLabel("Перевод…")
        self.translation_label.setObjectName("translation")
        self.translation_label.setWordWrap(True)
        self.definition_label = QLabel("")
        self.definition_label.setWordWrap(True)
        self.definition_label.setMaximumHeight(125)
        self.context_label = QLabel("")
        self.context_label.setObjectName("muted")
        self.context_label.setWordWrap(True)
        self.status_label = QLabel("Alt+Q — повторить / скрыть")
        self.status_label.setObjectName("muted")
        layout.addWidget(self.word_label)
        layout.addWidget(self.translation_label)
        layout.addWidget(self.definition_label)
        layout.addWidget(self.context_label)
        layout.addWidget(self.status_label)
        self._hide_timer = QTimer(self)
        self._hide_timer.setSingleShot(True)
        self._hide_timer.timeout.connect(self.hide)

    def show_loading(self, word: str = "Ищу слово…"):
        self.word_label.setText(word)
        self.translation_label.setText("Распознавание и поиск…")
        self.definition_label.clear()
        self.context_label.clear()
        self.status_label.setText("Alt+Q — скрыть")
        self._hide_timer.stop()
        self._place_near_cursor()
        self.show()
        self.raise_()

    def show_result(self, result: QuickLookupResult):
        self.word_label.setText(result.word)
        self.translation_label.setText(result.translation)
        definition = result.definition
        if result.phonetics:
            definition = f"/{result.phonetics}/\n{definition}"
        self.definition_label.setText(definition[:950])
        self.context_label.setText(f"Контекст: {result.context}" if result.context else "")
        suffix = " · из кэша" if result.cached else ""
        if result.warnings:
            suffix += " · часть сервисов недоступна"
        self.status_label.setText(f"Alt+Q — скрыть{suffix}")
        self.adjustSize()
        self._place_near_cursor()
        self.show()
        self.raise_()
        self._hide_timer.start(15000)

    def show_error(self, message: str):
        self.word_label.setText("Не удалось найти слово")
        self.translation_label.setText(message)
        self.definition_label.clear()
        self.context_label.clear()
        self._place_near_cursor()
        self.show()
        self.raise_()
        self._hide_timer.start(7000)

    def toggle(self):
        if self.isVisible():
            self.hide()
        else:
            self.show_loading()

    def _place_near_cursor(self):
        point = QCursor.pos()
        screen = QApplication.screenAt(point) or self.screen()
        available = screen.availableGeometry() if screen else None
        self.adjustSize()
        x, y = point.x() + 18, point.y() + 18
        if available:
            if x + self.width() > available.right():
                x = point.x() - self.width() - 18
            if y + self.height() > available.bottom():
                y = point.y() - self.height() - 18
            x = max(available.left(), x)
            y = max(available.top(), y)
        self.move(x, y)
