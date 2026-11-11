from english_assistant.domains.core import VocabularyStore


def test_quick_lookup_cache_round_trip(tmp_path):
    store = VocabularyStore(tmp_path / "cache.sqlite3")
    assert store.get_quick_cache("hello") is None
    store.set_quick_cache("Hello", "привет", "a greeting", "/həˈləʊ/")
    cached = store.get_quick_cache("hello")
    assert cached is not None
    assert cached["translation"] == "привет"
    assert cached["definition"] == "a greeting"
    assert cached["phonetics"] == "/həˈləʊ/"


def test_quick_lookup_uses_cache_without_calling_network(tmp_path):
    from english_assistant.lookup.quick_lookup import QuickLookupService
    from english_assistant.ocr.word_locator import LocatedWord

    store = VocabularyStore(tmp_path / "quick.sqlite3")
    store.set_quick_cache("knight", "рыцарь", "a man who served a king", "/naɪt/")
    result = QuickLookupService(store).lookup(
        LocatedWord("knight", "The knight entered.", 0.98, (1, 2, 3, 4))
    )
    assert result.cached is True
    assert result.translation == "рыцарь"
    assert result.word == "knight"
