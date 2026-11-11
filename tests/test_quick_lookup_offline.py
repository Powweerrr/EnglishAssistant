from english_assistant.lookup.quick_lookup import QuickLookupService
from english_assistant.domains.core import VocabularyStore
from english_assistant.ocr.word_locator import LocatedWord
from english_assistant.dictionary.stardict import DictionaryEntry


class FakeLocalDictionary:
    def lookup(self, word):
        if word.casefold() == "knights":
            return DictionaryEntry("knight", "рыцарь; воин")
        return None


def test_quick_lookup_prefers_local_dictionary_and_skips_network(tmp_path, monkeypatch):
    service = QuickLookupService(
        store=VocabularyStore(tmp_path / "quick.sqlite3"),
        local_dictionary=FakeLocalDictionary(),
    )

    def should_not_call(*args, **kwargs):
        raise AssertionError("Network providers must not run for a local dictionary hit")

    monkeypatch.setattr(service.dictionary, "run", should_not_call)
    monkeypatch.setattr(service.translation, "run", should_not_call)
    result = service.lookup(LocatedWord("knights", "The knights arrived", 1.0, (0, 0, 1, 1)))
    assert result.translation == "рыцарь; воин"
    assert "офлайн" in result.definition.casefold()
