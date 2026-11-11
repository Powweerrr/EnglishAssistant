from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, wait
from dataclasses import dataclass

from english_assistant.domains.core import (
    DictionaryDomain,
    DomainError,
    TranslationDomain,
    VocabularyStore,
)
from english_assistant.ocr.word_locator import LocatedWord
from english_assistant.dictionary import get_default_dictionary


@dataclass(frozen=True, slots=True)
class QuickLookupResult:
    word: str
    context: str
    translation: str
    definition: str
    phonetics: str
    confidence: float
    cached: bool = False
    warnings: tuple[str, ...] = ()


class QuickLookupService:
    """Fast path: dictionary + one-word translation only; no full domain fan-out."""

    def __init__(self, store: VocabularyStore | None = None, local_dictionary=None):
        self.store = store or VocabularyStore()
        self.dictionary = DictionaryDomain(timeout=3.5)
        self.translation = TranslationDomain(timeout=3.5)
        self.local_dictionary = local_dictionary if local_dictionary is not None else self._load_local_dictionary()

    @staticmethod
    def _load_local_dictionary():
        return get_default_dictionary()

    def lookup(self, located: LocatedWord) -> QuickLookupResult:
        if self.local_dictionary is not None:
            local_entry = self.local_dictionary.lookup(located.word)
            if local_entry is not None:
                return QuickLookupResult(
                    word=located.word,
                    context=located.context,
                    translation=local_entry.article,
                    definition=f"Офлайн EN–RU · словарная форма: {local_entry.headword}",
                    phonetics="",
                    confidence=located.confidence,
                    cached=False,
                )
        cached = self.store.get_quick_cache(located.word)
        if cached is not None and cached["translation"] and cached["definition"]:
            return QuickLookupResult(
                word=located.word,
                context=located.context,
                translation=cached["translation"],
                definition=cached["definition"],
                phonetics=cached["phonetics"],
                confidence=located.confidence,
                cached=True,
            )

        pool = ThreadPoolExecutor(max_workers=2, thread_name_prefix="quick-lookup")
        tasks = {
            "dictionary": pool.submit(self.dictionary.run, located.word),
            "translation": pool.submit(self.translation.run, located.word),
        }
        warnings = []
        definition = phonetics = translation = ""
        done, pending = wait(tasks.values(), timeout=4.0)
        for name, future in tasks.items():
            if future not in done:
                warnings.append(f"{name.capitalize()}: превышено время ожидания (4 с)")
                continue
            try:
                result = future.result()
                if name == "dictionary":
                    definition = result.content
                    phonetics = " · ".join(result.metadata.get("phonetics", []))
                else:
                    translation = result.content
            except Exception as error:  # external providers are independent
                warnings.append(f"{name.capitalize()}: {error}")
        # Do not block the UI worker while slow providers finish. Network calls
        # have their own bounded timeout and can complete in the background.
        pool.shutdown(wait=False, cancel_futures=True)

        if not definition and not translation:
            raise DomainError("Не удалось получить данные. Проверь интернет или повтори поиск. " + " / ".join(warnings))

        self.store.set_quick_cache(located.word, translation, definition, phonetics)
        return QuickLookupResult(
            word=located.word,
            context=located.context,
            translation=translation or "Перевод недоступен",
            definition=definition or "Словарная статья недоступна",
            phonetics=phonetics,
            confidence=located.confidence,
            warnings=tuple(warnings),
        )
