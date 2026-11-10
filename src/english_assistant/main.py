"""Application entry point."""

import sys

from PySide6.QtWidgets import QApplication

from english_assistant.ui.main_window import MainWindow


def main() -> int:
    app = QApplication(sys.argv)
    app.setApplicationName("English Assistant")

    app.setStyle("Fusion")

    app.setStyleSheet(
        """
        QMainWindow {
            background-color: #f4f6fa;
        }

        QWidget {
            font-family: "Segoe UI";
            font-size: 10pt;
            color: #202938;
        }

        QLabel#pageTitle {
            font-size: 25pt;
            font-weight: 700;
            color: #172033;
        }

        QLabel#pageSubtitle {
            font-size: 11pt;
            color: #64748b;
        }

        QFrame#statusCard {
            background-color: white;
            border: 1px solid #e2e8f0;
            border-radius: 14px;
        }

        QLabel#cardTitle {
            font-size: 15pt;
            font-weight: 600;
            color: #202938;
        }

        QLabel#statusText {
            font-size: 10pt;
            color: #64748b;
        }

        QStatusBar {
            background-color: #ffffff;
            border-top: 1px solid #e2e8f0;
            color: #64748b;
        }
        """
    )

    window = MainWindow()
    window.show()

    return app.exec()


if __name__ == "__main__":
    raise SystemExit(main())