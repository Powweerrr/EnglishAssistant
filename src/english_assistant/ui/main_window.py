"""Main application window."""

from PySide6.QtWidgets import (
    QFrame,
    QLabel,
    QMainWindow,
    QVBoxLayout,
    QWidget,
)


class MainWindow(QMainWindow):
    """Main window of English Assistant."""

    def __init__(self) -> None:
        super().__init__()

        self.setWindowTitle("English Assistant")
        self.resize(1000, 650)
        self.setMinimumSize(800, 500)

        self._setup_ui()

    def _setup_ui(self) -> None:
        """Create and arrange the main interface."""

        central_widget = QWidget()
        self.setCentralWidget(central_widget)

        main_layout = QVBoxLayout(central_widget)
        main_layout.setContentsMargins(36, 32, 36, 32)
        main_layout.setSpacing(24)

        # Application header
        title = QLabel("English Assistant")
        title.setObjectName("pageTitle")

        subtitle = QLabel(
            "Твой персональный помощник в изучении английского языка."
        )
        subtitle.setObjectName("pageSubtitle")

        main_layout.addWidget(title)
        main_layout.addWidget(subtitle)

        # Main workspace card
        status_card = QFrame()
        status_card.setObjectName("statusCard")

        card_layout = QVBoxLayout(status_card)
        card_layout.setContentsMargins(24, 24, 24, 24)
        card_layout.setSpacing(12)

        card_title = QLabel("Рабочее пространство")
        card_title.setObjectName("cardTitle")

        status_text = QLabel(
            "English Assistant запущен.\n\n"
            "Здесь будет отображаться распознанный текст, "
            "его перевод и объяснение английских конструкций."
        )
        status_text.setObjectName("statusText")
        status_text.setWordWrap(True)

        card_layout.addWidget(card_title)
        card_layout.addWidget(status_text)

        main_layout.addWidget(status_card)
        main_layout.addStretch()

        self.statusBar().showMessage("Приложение готово")