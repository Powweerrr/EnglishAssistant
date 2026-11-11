from __future__ import annotations

import csv
import json
import re
import sqlite3
from dataclasses import dataclass
from datetime import datetime, timezone
from html import unescape
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urlencode, quote
from urllib.request import Request, urlopen


class DomainError(RuntimeError):
    """An actionable error from a language domain."""


@dataclass(frozen=True, slots=True)
class DomainResult:
    domain: str
    title: str
    source_text: str
    content: str
    metadata: dict


def request_json(url: str, *, params: dict | None = None, data: dict | None = None,
                 timeout: float = 18.0) -> dict | list:
    if params:
        url = f"{url}?{urlencode(params)}"
    body = urlencode(data).encode("utf-8") if data is not None else None
    headers = {
        "User-Agent": "EnglishAssistant/1.0 (desktop language learning tool)",
        "Accept": "application/json",
    }
    if body is not None:
        headers["Content-Type"] = "application/x-www-form-urlencoded; charset=UTF-8"
    request = Request(url, data=body, headers=headers,
                      method="POST" if body is not None else "GET")
    try:
        with urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read(400).decode("utf-8", errors="replace")
        raise DomainError(f"Сервис вернул HTTP {exc.code}: {detail[:250]}") from exc
    except (URLError, TimeoutError, OSError) as exc:
        raise DomainError(f"Не удалось подключиться к сервису: {exc}") from exc
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise DomainError("Сервис вернул некорректный ответ.") from exc


class TranslationDomain:
    endpoint = "https://api.mymemory.translated.net/get"

    def __init__(self, timeout: float = 18.0):
        self.timeout = timeout

    def run(self, text: str, source: str = "en", target: str = "ru") -> DomainResult:
        text = text.strip()
        if not text:
            raise DomainError("Введите текст для перевода.")
        if len(text) > 4500:
            raise DomainError("Максимальная длина одного запроса — 4500 символов.")
        if source == target:
            raise DomainError("Исходный и целевой языки должны различаться.")
        payload = request_json(self.endpoint,
                               params={"q": text, "langpair": f"{source}|{target}"}, timeout=self.timeout)
        if not isinstance(payload, dict) or payload.get("responseStatus") != 200:
            detail = payload.get("responseDetails", "Перевод не выполнен.") if isinstance(payload, dict) else "Некорректный ответ сервиса."
            raise DomainError(str(detail))
        data = payload.get("responseData") or {}
        translated = data.get("translatedText")
        if not isinstance(translated, str) or not translated.strip():
            raise DomainError("Сервис не вернул перевод.")
        return DomainResult("translation", "Перевод", text, unescape(translated).strip(),
                            {"source": source, "target": target,
                             "match": data.get("match")})


class DictionaryDomain:
    def __init__(self, timeout: float = 18.0):
        self.timeout = timeout

    endpoint = "https://api.dictionaryapi.dev/api/v2/entries/en/{}"

    def run(self, term: str) -> DomainResult:
        term = term.strip()
        if not term or len(term) > 100:
            raise DomainError("Введите английское слово или выражение длиной до 100 символов.")
        try:
            from english_assistant.dictionary import get_default_dictionary
            local = get_default_dictionary()
            entry = local.lookup(term) if local is not None else None
        except Exception:
            entry = None
        if entry is not None:
            return DomainResult(
                "dictionary", f"Локальный словарь: {entry.headword}", term,
                entry.article, {"word": term, "headword": entry.headword, "source": "offline-en-ru"},
            )
        payload = request_json(self.endpoint.format(quote(term)), timeout=self.timeout)
        if not isinstance(payload, list) or not payload:
            raise DomainError(f"Словарная статья для «{term}» не найдена.")
        entry = payload[0]
        lines: list[str] = []
        phonetics = list(dict.fromkeys(p.get("text") for p in entry.get("phonetics", []) if p.get("text")))
        if phonetics:
            lines.append("Произношение: " + " · ".join(phonetics))
        for meaning in entry.get("meanings", []):
            lines.append(f"\n{meaning.get('partOfSpeech', 'Часть речи').capitalize()}")
            for number, item in enumerate(meaning.get("definitions", [])[:8], 1):
                definition = item.get("definition", "")
                if definition:
                    lines.append(f"{number}. {definition}")
                if item.get("example"):
                    lines.append(f"   Пример: {item['example']}")
                if item.get("synonyms"):
                    lines.append("   Синонимы: " + ", ".join(item["synonyms"][:8]))
        content = "\n".join(lines).strip()
        if not content:
            raise DomainError("Словарная статья не содержит определений.")
        return DomainResult("dictionary", f"Словарь: {term}", term, content,
                            {"word": term, "phonetics": phonetics})


class GrammarDomain:
    endpoint = "https://api.languagetool.org/v2/check"

    def run(self, text: str, language: str = "en-US") -> DomainResult:
        text = text.strip()
        if not text:
            raise DomainError("Введите предложение для проверки.")
        if len(text) > 12000:
            raise DomainError("Максимальная длина текста — 12000 символов.")
        payload = request_json(self.endpoint, data={"text": text, "language": language}, timeout=30)
        matches = payload.get("matches", []) if isinstance(payload, dict) else []
        if not matches:
            content = "Замечаний не найдено. Автоматическая проверка не гарантирует абсолютную правильность текста."
        else:
            blocks = [f"Найдено замечаний: {len(matches)}", ""]
            for number, item in enumerate(matches[:40], 1):
                start, length = int(item.get("offset", 0)), int(item.get("length", 0))
                fragment = text[start:start + length]
                blocks.append(f"{number}. {item.get('message', 'Замечание')}")
                if fragment:
                    blocks.append(f"   Фрагмент: «{fragment}»")
                replacements = [r.get("value") for r in item.get("replacements", [])[:6] if r.get("value")]
                if replacements:
                    blocks.append("   Возможные варианты: " + ", ".join(replacements))
                category = (item.get("rule") or {}).get("category", {}).get("name")
                if category:
                    blocks.append(f"   Категория: {category}")
                blocks.append("")
            content = "\n".join(blocks).strip()
        return DomainResult("grammar", "Грамматика", text, content,
                            {"issue_count": len(matches), "language": language})


EXPRESSIONS: dict[str, tuple[str, str, str]] = {
    "a piece of cake": ("проще простого", "Идиома", "The test was a piece of cake."),
    "break a leg": ("ни пуха ни пера; пожелание удачи", "Идиома", "Break a leg tonight!"),
    "call it a day": ("закончить работу на сегодня", "Идиома", "Let's call it a day."),
    "get along with": ("ладить с кем-либо", "Фразовый глагол", "I get along with my classmates."),
    "give up": ("сдаваться; бросать занятие", "Фразовый глагол", "Never give up."),
    "look after": ("присматривать за кем-либо", "Фразовый глагол", "She looks after her brother."),
    "look for": ("искать", "Фразовый глагол", "I'm looking for my keys."),
    "look forward to": ("с нетерпением ждать", "Фразовый глагол", "I look forward to seeing you."),
    "put off": ("откладывать", "Фразовый глагол", "They put off the meeting."),
    "run out of": ("израсходовать; остаться без", "Фразовый глагол", "We ran out of time."),
    "take off": ("взлетать; снимать одежду", "Фразовый глагол", "The plane takes off soon."),
    "turn down": ("отклонить; убавить громкость", "Фразовый глагол", "He turned down the offer."),
    "under the weather": ("плохо себя чувствовать", "Идиома", "I'm a little under the weather."),
    "once in a blue moon": ("крайне редко", "Идиома", "It happens once in a blue moon."),
    "on the same page": ("одинаково понимать ситуацию", "Идиома", "Let's make sure we're on the same page."),
    "spill the beans": ("выдать секрет", "Идиома", "Who spilled the beans?"),
    "hit the books": ("усердно учиться", "Идиома", "I need to hit the books."),
    "cost an arm and a leg": ("стоить очень дорого", "Идиома", "That car costs an arm and a leg."),
    "break down": ("сломаться; потерять самообладание", "Фразовый глагол", "My car broke down."),
    "bring up": ("поднять тему; воспитать", "Фразовый глагол", "She brought up an interesting point."),
    "carry on": ("продолжать", "Фразовый глагол", "Please carry on."),
    "come across": ("случайно натолкнуться", "Фразовый глагол", "I came across an old photo."),
    "find out": ("выяснить, узнать", "Фразовый глагол", "We need to find out the truth."),
    "get over": ("оправиться; преодолеть", "Фразовый глагол", "It took time to get over it."),
    "make up": ("придумать; помириться", "Фразовый глагол", "They made up after the argument."),
    "set up": ("организовать; настроить", "Фразовый глагол", "We set up a new account."),
    "work out": ("получиться; тренироваться; решить", "Фразовый глагол", "Everything will work out."),
}


class ExpressionsDomain:
    def run(self, text: str) -> DomainResult:
        text = text.strip()
        if not text:
            raise DomainError("Введите текст для поиска выражений.")
        lowered = text.casefold()
        found = []
        for phrase in sorted(EXPRESSIONS, key=len, reverse=True):
            if re.search(r"(?<![\w])" + re.escape(phrase) + r"(?![\w])", lowered):
                meaning, kind, example = EXPRESSIONS[phrase]
                found.append((phrase, meaning, kind, example))
        if found:
            content = "\n\n".join(f"{phrase} — {kind}\nЗначение: {meaning}\nПример: {example}"
                                    for phrase, meaning, kind, example in found)
        else:
            content = "Совпадений во встроенном справочнике не найдено. Список выражений не является исчерпывающим."
        return DomainResult("expressions", "Идиомы и фразовые глаголы", text, content,
                            {"count": len(found), "matches": [x[0] for x in found]})


CEFR_WORDS: dict[str, str] = {}
_CEFR_GROUPS = {
    "A1": "about after again all am an and animal answer any are arm ask at away baby back bad bag ball bank bath be beautiful because bed bedroom before begin behind best better between big bird birthday black blue body book both boy bread breakfast brother brown bus but buy by call can car cat chair change child city class clean close clothes coffee cold come computer cook country day dear decide do doctor dog door down draw drink drive during each early eat egg eight eighteen eighty end enough even evening every eye face family far fast father feel few find finish first fish five floor flower fly food foot for four free friend from front fruit full fun game garden get girl give go good goodbye grandparent great green group grow hair half hand happy hard hat have he head hear hello help her here high him his home house how hungry husband I ice idea if important in inside into is it its job jump just keep key kind kitchen know land language large last late learn leave leg let letter life light like listen little live long look love lunch make man many map market married matter may me meal meet milk minute miss money month morning mother mountain mouth move much music must my name near need never new next nice night nine nineteen ninety no north nose not now number of off often old on one only open or other our out over own page paper parent park part party pass pay pen people person phone photo picture place plan play please point poor popular possible practice present pretty price problem pull put question quick quickly quiet quite radio rain read ready red remember repeat restaurant right river road room run sad safe same say school sea second see sell send sentence seven seventeen seventy she shop short should show sister sit six sixteen sixty sleep slow small snow so some son soon speak sport spring stand start stop story street student study such summer sun sure table take talk tall teacher tell ten terrible test than thank that the their them then there these they thing think thirty this those three through time tired to today together tomorrow too tooth town train travel tree true try twelve twenty two under understand until up us use usually very visit wait walk want warm was watch water way we weather week weekend well were what when where which white who why wife will window winter with woman wonderful word work world would write year yellow yes you you young your".split()
}
for _level, _words in _CEFR_GROUPS.items():
    for _word in _words:
        CEFR_WORDS.setdefault(_word, _level)


class CefrDomain:
    def run(self, text: str) -> DomainResult:
        text = text.strip()
        if not text:
            raise DomainError("Введите текст для анализа лексики.")
        words = re.findall(r"[a-z]+(?:['’-][a-z]+)?", text.casefold())
        if not words:
            raise DomainError("Английские слова не найдены.")
        matches = [(word, CEFR_WORDS[word]) for word in words if word in CEFR_WORDS]
        counts: dict[str, int] = {}
        for _, level in matches:
            counts[level] = counts.get(level, 0) + 1
        if not matches:
            content = "Слова не найдены во встроенном справочнике. Надёжно оценить CEFR по этому тексту нельзя."
        else:
            rows = ["Ориентировочная оценка известных слов:"]
            rows.extend(f"• {word} — {level}" for word, level in matches)
            rows.append("\nРаспределение: " + ", ".join(f"{k}: {v}" for k, v in sorted(counts.items())))
            rows.append("\nЭто ограниченный справочник отдельных слов, а не официальный тест уровня владения языком.")
            content = "\n".join(rows)
        return DomainResult("cefr", "Лексика и CEFR", text, content,
                            {"total_words": len(words), "matched_words": len(matches), "distribution": counts})


class VocabularyStore:
    def __init__(self, path: str | Path | None = None):
        base = Path.home() / ".english_assistant"
        self.path = Path(path) if path else base / "english_assistant.sqlite3"
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    def connect(self) -> sqlite3.Connection:
        db = sqlite3.connect(self.path, timeout=15)
        db.row_factory = sqlite3.Row
        return db

    def _init_db(self) -> None:
        with self.connect() as db:
            db.execute("""CREATE TABLE IF NOT EXISTS vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT, term TEXT NOT NULL COLLATE NOCASE,
                meaning TEXT NOT NULL DEFAULT '', example TEXT NOT NULL DEFAULT '',
                source_text TEXT NOT NULL DEFAULT '', created_at TEXT NOT NULL,
                UNIQUE(term, meaning))""")
            db.execute("""CREATE TABLE IF NOT EXISTS history (
                id INTEGER PRIMARY KEY AUTOINCREMENT, domain TEXT NOT NULL,
                source_text TEXT NOT NULL, result_text TEXT NOT NULL, created_at TEXT NOT NULL)""")
            db.execute("""CREATE TABLE IF NOT EXISTS quick_lookup_cache (
                term TEXT PRIMARY KEY COLLATE NOCASE,
                translation TEXT NOT NULL DEFAULT '',
                definition TEXT NOT NULL DEFAULT '',
                phonetics TEXT NOT NULL DEFAULT '',
                updated_at TEXT NOT NULL)""")

    @staticmethod
    def now() -> str:
        return datetime.now(timezone.utc).isoformat(timespec="seconds")

    def add_word(self, term: str, meaning: str = "", example: str = "", source_text: str = "") -> int:
        term = term.strip()
        if not term:
            raise ValueError("Нельзя сохранить пустое слово.")
        with self.connect() as db:
            db.execute("INSERT OR IGNORE INTO vocabulary(term,meaning,example,source_text,created_at) VALUES(?,?,?,?,?)",
                       (term, meaning.strip(), example.strip(), source_text.strip(), self.now()))
            row = db.execute("SELECT id FROM vocabulary WHERE term=? AND meaning=?",
                             (term, meaning.strip())).fetchone()
            return int(row["id"])

    def delete_word(self, word_id: int) -> bool:
        with self.connect() as db:
            cur = db.execute("DELETE FROM vocabulary WHERE id=?", (word_id,))
            return cur.rowcount > 0

    def words(self) -> list[dict]:
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM vocabulary ORDER BY id DESC")]

    def add_history(self, result: DomainResult) -> None:
        with self.connect() as db:
            db.execute("INSERT INTO history(domain,source_text,result_text,created_at) VALUES(?,?,?,?)",
                       (result.domain, result.source_text, result.content, self.now()))

    def history(self, limit: int = 300) -> list[dict]:
        with self.connect() as db:
            return [dict(r) for r in db.execute("SELECT * FROM history ORDER BY id DESC LIMIT ?", (limit,))]

    def get_quick_cache(self, term: str, max_age_days: int = 30) -> dict | None:
        with self.connect() as db:
            row = db.execute(
                "SELECT translation, definition, phonetics, updated_at FROM quick_lookup_cache WHERE term=?",
                (term.strip(),),
            ).fetchone()
        if row is None:
            return None
        try:
            updated = datetime.fromisoformat(row["updated_at"])
            age = datetime.now(timezone.utc) - updated
            if age.days > max_age_days:
                return None
        except (TypeError, ValueError):
            return None
        return dict(row)

    def set_quick_cache(self, term: str, translation: str, definition: str, phonetics: str = "") -> None:
        with self.connect() as db:
            db.execute(
                """INSERT INTO quick_lookup_cache(term,translation,definition,phonetics,updated_at)
                   VALUES(?,?,?,?,?) ON CONFLICT(term) DO UPDATE SET
                   translation=excluded.translation, definition=excluded.definition,
                   phonetics=excluded.phonetics, updated_at=excluded.updated_at""",
                (term.strip(), translation, definition, phonetics, self.now()),
            )

    def export_anki(self, destination: str | Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("w", encoding="utf-8-sig", newline="") as stream:
            writer = csv.writer(stream, delimiter=";", quoting=csv.QUOTE_MINIMAL)
            writer.writerow(["Front", "Back", "Example"])
            for word in reversed(self.words()):
                writer.writerow([word["term"], word["meaning"], word["example"]])
        return destination


class EnglishAssistantEngine:
    def __init__(self, store: VocabularyStore | None = None):
        self.store = store or VocabularyStore()
        self.domains = {
            "translation": TranslationDomain(), "dictionary": DictionaryDomain(),
            "grammar": GrammarDomain(), "expressions": ExpressionsDomain(),
            "cefr": CefrDomain(),
        }

    def run(self, domain: str, text: str) -> DomainResult:
        if domain not in self.domains:
            raise DomainError(f"Неизвестный домен: {domain}")
        result = self.domains[domain].run(text)
        self.store.add_history(result)
        return result

    def run_all(self, text: str) -> list[DomainResult]:
        """Run every domain independently; one unavailable online service won't stop others."""
        results: list[DomainResult] = []
        for name, domain in self.domains.items():
            try:
                result = domain.run(text)
            except DomainError as error:
                result = DomainResult(
                    name,
                    f"{name.capitalize()} — ошибка",
                    text,
                    str(error),
                    {"error": True},
                )
            self.store.add_history(result)
            results.append(result)
        return results
