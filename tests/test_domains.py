from pathlib import Path

import pytest

from english_assistant.domains.core import (
    CefrDomain, DictionaryDomain, DomainError, ExpressionsDomain,
    GrammarDomain, TranslationDomain, VocabularyStore,
)


def test_translation_rejects_empty_text():
    with pytest.raises(DomainError):
        TranslationDomain().run("   ")


def test_translation_rejects_same_language():
    with pytest.raises(DomainError):
        TranslationDomain().run("hello", "en", "en")


def test_dictionary_rejects_empty_word():
    with pytest.raises(DomainError):
        DictionaryDomain().run("")


def test_grammar_rejects_empty_text():
    with pytest.raises(DomainError):
        GrammarDomain().run(" ")


def test_expression_matcher_finds_multiword_phrase():
    result = ExpressionsDomain().run("I look forward to seeing you.")
    assert "look forward to" in result.content
    assert result.metadata["count"] == 1


def test_expression_matcher_does_not_match_inside_word():
    result = ExpressionsDomain().run("The word giveaway is here.")
    assert result.metadata["count"] == 0


def test_cefr_returns_word_distribution():
    result = CefrDomain().run("I have a good book")
    assert result.metadata["matched_words"] > 0
    assert "A1" in result.metadata["distribution"]


def test_store_word_history_and_anki_export(tmp_path: Path):
    store = VocabularyStore(tmp_path / "test.sqlite3")
    word_id = store.add_word("look up", "искать в словаре", "Look it up.")
    assert word_id > 0
    assert store.words()[0]["term"] == "look up"
    assert store.delete_word(word_id)
    assert store.words() == []
    output = store.export_anki(tmp_path / "cards.csv")
    assert output.exists()
    assert "Front;Back;Example" in output.read_text(encoding="utf-8-sig")


def test_run_all_keeps_working_when_one_domain_fails(tmp_path: Path):
    from english_assistant.domains.core import EnglishAssistantEngine

    engine = EnglishAssistantEngine(VocabularyStore(tmp_path / "all.sqlite3"))

    class BrokenDomain:
        def run(self, text):
            raise DomainError("offline")

    engine.domains["translation"] = BrokenDomain()
    results = engine.run_all("A simple sentence.")
    assert len(results) == 5
    assert results[0].metadata["error"] is True
    assert len(engine.store.history()) == 5


def test_store_persists_history_and_word(tmp_path: Path):
    from english_assistant.domains.core import DomainResult

    path = tmp_path / "persistent.sqlite3"
    store = VocabularyStore(path)
    store.add_word("resilient", "стойкий", "She is resilient.")
    store.add_history(DomainResult("dictionary", "Словарь", "resilient", "стойкий", {}))

    reopened = VocabularyStore(path)
    assert reopened.words()[0]["term"] == "resilient"
    assert reopened.history()[0]["result_text"] == "стойкий"


def test_dictionary_domain_uses_offline_entry_before_network(monkeypatch):
    from types import SimpleNamespace
    from english_assistant import dictionary

    class LocalDictionary:
        def lookup(self, term):
            return SimpleNamespace(headword="knight", article="рыцарь") if term == "knights" else None

    monkeypatch.setattr(dictionary, "get_default_dictionary", lambda: LocalDictionary())
    monkeypatch.setattr(
        "english_assistant.domains.core.request_json",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("network must not be called")),
    )
    result = DictionaryDomain().run("knights")
    assert result.content == "рыцарь"
    assert result.metadata["source"] == "offline-en-ru"
