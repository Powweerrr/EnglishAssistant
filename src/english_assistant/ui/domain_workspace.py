from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QFileDialog, QHBoxLayout, QInputDialog, QLabel, QMessageBox, QPushButton,
    QPlainTextEdit, QTabWidget, QTableWidget, QTableWidgetItem,
    QVBoxLayout, QWidget,
)

from english_assistant.domains.core import DomainResult, EnglishAssistantEngine
from english_assistant.ui.workers import TaskWorker


class DomainWorkspace(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.engine = EnglishAssistantEngine()
        self.workers: list[TaskWorker] = []
        self.last_result: DomainResult | None = None
        self._build()

    def _build(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(8)
        root.addWidget(QLabel("Текст для анализа"))
        self.input = QPlainTextEdit()
        self.input.setPlaceholderText("Вставьте английский текст или выделите фрагмент на экране…")
        self.input.setMinimumHeight(110)
        root.addWidget(self.input)

        buttons = QHBoxLayout()
        self.domain_buttons = {}
        for key, title in (
            ("translation", "Перевести"), ("dictionary", "Словарь"),
            ("grammar", "Грамматика"), ("expressions", "Идиомы / phrasal verbs"),
            ("cefr", "CEFR"), ("all", "Запустить все домены"),
        ):
            button = QPushButton(title)
            button.clicked.connect(lambda checked=False, domain=key: self.run_domain(domain))
            buttons.addWidget(button)
            self.domain_buttons[key] = button
        root.addLayout(buttons)
        self.status = QLabel("Готово · для онлайн-доменов требуется интернет")
        root.addWidget(self.status)

        self.tabs = QTabWidget()
        self.result_output = QPlainTextEdit()
        self.result_output.setReadOnly(True)
        self.tabs.addTab(self.result_output, "Результат")
        self.vocabulary_table = QTableWidget(0, 3)
        self.vocabulary_table.setHorizontalHeaderLabels(["Слово / выражение", "Значение", "Пример"])
        self.vocabulary_table.horizontalHeader().setStretchLastSection(True)
        self.vocabulary_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabs.addTab(self.vocabulary_table, "Мой словарь")
        self.history_table = QTableWidget(0, 4)
        self.history_table.setHorizontalHeaderLabels(["Дата", "Домен", "Исходный текст", "Результат"])
        self.history_table.horizontalHeader().setStretchLastSection(True)
        self.history_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.tabs.addTab(self.history_table, "История")
        root.addWidget(self.tabs, 1)

        actions = QHBoxLayout()
        self.save_button = QPushButton("Добавить в словарь")
        self.save_button.clicked.connect(self.save_word)
        self.delete_button = QPushButton("Удалить выбранное")
        self.delete_button.clicked.connect(self.delete_word)
        self.export_button = QPushButton("Экспорт Anki CSV")
        self.export_button.clicked.connect(self.export_anki)
        self.refresh_button = QPushButton("Обновить данные")
        self.refresh_button.clicked.connect(self.refresh_tables)
        actions.addWidget(self.save_button)
        actions.addWidget(self.delete_button)
        actions.addWidget(self.export_button)
        actions.addWidget(self.refresh_button)
        root.addLayout(actions)
        self.refresh_tables()

    def set_input_text(self, text: str):
        self.input.setPlainText(text)
        self.input.setFocus()

    def run_domain(self, domain: str):
        text = self.input.toPlainText().strip()
        if not text:
            self.status.setText("Сначала введите или распознайте текст.")
            return
        if domain == "dictionary":
            selected = self.input.textCursor().selectedText().strip()
            default_term = selected or text.split()[0].strip(".,!?;:()[]{}\"'")
            term, accepted = QInputDialog.getText(
                self, "Словарь", "Какое слово или выражение разобрать?", text=default_term
            )
            if not accepted or not term.strip():
                return
            text = term.strip()
        self._set_busy(True)
        self.status.setText("Обработка…")
        task = (lambda: self.engine.run_all(text)) if domain == "all" else (lambda: self.engine.run(domain, text))
        worker = TaskWorker(task, self)
        self.workers.append(worker)
        worker.succeeded.connect(self._show_all_results if domain == "all" else self._show_result)
        worker.failed.connect(self._show_error)
        worker.finished.connect(lambda w=worker: self._finished(w))
        worker.start()

    def _set_busy(self, busy: bool):
        for button in self.domain_buttons.values():
            button.setEnabled(not busy)

    def _show_result(self, result: DomainResult):
        self.last_result = result
        self.result_output.setPlainText(result.content)
        self.tabs.setTabText(0, result.title)
        self.tabs.setCurrentIndex(0)
        self.status.setText("Готово")
        self.refresh_tables()

    def _show_all_results(self, results: list[DomainResult]):
        blocks = []
        for result in results:
            blocks.append(f"{'=' * 56}\n{result.title}\n{'=' * 56}\n{result.content}")
        self.last_result = results[0] if results else None
        self.result_output.setPlainText("\n\n".join(blocks))
        self.tabs.setTabText(0, "Все домены")
        self.tabs.setCurrentIndex(0)
        errors = sum(bool(item.metadata.get("error")) for item in results)
        self.status.setText(f"Обработано доменов: {len(results)} · ошибок: {errors}")
        self.refresh_tables()

    def _show_error(self, message: str):
        self.status.setText("Ошибка обработки")
        QMessageBox.warning(self, "EnglishAssistant", message)

    def _finished(self, worker: TaskWorker):
        if worker in self.workers:
            self.workers.remove(worker)
        worker.deleteLater()
        self._set_busy(False)

    def save_word(self):
        source = self.input.textCursor().selectedText().strip() or self.input.toPlainText().strip()
        if not source:
            self.status.setText("Нет текста для сохранения.")
            return
        default_term = source.splitlines()[0].strip()[:120]
        term, accepted = QInputDialog.getText(
            self, "Добавить в словарь", "Слово или выражение:", text=default_term
        )
        if not accepted or not term.strip():
            return
        default_meaning = self.last_result.content if self.last_result else ""
        meaning, accepted = QInputDialog.getMultiLineText(
            self, "Добавить в словарь", "Перевод / значение:", default_meaning
        )
        if not accepted:
            return
        example, accepted = QInputDialog.getMultiLineText(
            self, "Добавить в словарь", "Пример использования:", source
        )
        if not accepted:
            return
        try:
            self.engine.store.add_word(term, meaning, example, source)
        except (ValueError, OSError) as error:
            QMessageBox.warning(self, "Словарь", str(error))
            return
        self.status.setText(f"Сохранено: {term.strip()}")
        self.refresh_tables()
        self.tabs.setCurrentIndex(1)

    def delete_word(self):
        row = self.vocabulary_table.currentRow()
        if row < 0:
            return
        item = self.vocabulary_table.item(row, 0)
        word_id = item.data(Qt.ItemDataRole.UserRole) if item else None
        if word_id is not None:
            self.engine.store.delete_word(int(word_id))
            self.refresh_tables()

    def export_anki(self):
        path, _ = QFileDialog.getSaveFileName(self, "Экспорт для Anki", "english_assistant_anki.csv", "CSV (*.csv)")
        if not path:
            return
        try:
            self.engine.store.export_anki(path)
        except OSError as error:
            QMessageBox.warning(self, "Экспорт Anki", str(error))
            return
        QMessageBox.information(self, "Экспорт Anki", f"Файл сохранён:\n{path}")

    def refresh_tables(self):
        words = self.engine.store.words()
        self.vocabulary_table.setRowCount(len(words))
        for row, word in enumerate(words):
            term_item = QTableWidgetItem(word["term"])
            term_item.setData(Qt.ItemDataRole.UserRole, word["id"])
            self.vocabulary_table.setItem(row, 0, term_item)
            self.vocabulary_table.setItem(row, 1, QTableWidgetItem(word["meaning"]))
            self.vocabulary_table.setItem(row, 2, QTableWidgetItem(word["example"]))
        history = self.engine.store.history()
        self.history_table.setRowCount(len(history))
        for row, item in enumerate(history):
            values = [item["created_at"].replace("T", " ")[:19], item["domain"],
                      item["source_text"], item["result_text"]]
            for column, value in enumerate(values):
                self.history_table.setItem(row, column, QTableWidgetItem(str(value)))
