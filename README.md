# English Assistant

A Windows desktop application for learning English
through screen text recognition.

## Features

- Global keyboard shortcuts
- Screen text recognition (OCR)
- English-to-Russian translation
- CEFR level estimation
- Personal vocabulary database
- Floating desktop overlay
- Anki integration (planned)

## Technology

- Python 3.12
- PySide6
- SQLite
- MSS
- Pillow
- Pytest

## Development

Create a virtual environment:

py -3.12 -m venv .venv
.\.venv\Scripts\Activate.ps1
Install dependencies:

python -m pip install -e ".[dev]"
Run the application:

python -m english_assistant.main
Run tests:

pytest
Run lint:

ruff check .