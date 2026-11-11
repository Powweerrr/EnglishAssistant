from __future__ import annotations

import gzip
from functools import lru_cache
import html
import re
import struct
import urllib.request
import zipfile
from dataclasses import dataclass
from pathlib import Path

DEFAULT_DOWNLOAD_URL = (
    "https://github.com/DanielGregorini/koreader-dicts/releases/latest/download/en-ru.zip"
)


@dataclass(frozen=True, slots=True)
class DictionaryEntry:
    headword: str
    article: str


class StarDictError(RuntimeError):
    pass


def _plain_article(raw: bytes) -> str:
    text = raw.decode("utf-8", errors="replace")
    text = re.sub(r"(?i)<br\s*/?>", "\n", text)
    text = re.sub(r"(?i)</(p|div|li)>", "\n", text)
    text = re.sub(r"<[^>]+>", "", text)
    text = html.unescape(text)
    return "\n".join(line.strip() for line in text.splitlines() if line.strip()).strip()


class StarDictReader:
    """Small read-only StarDict reader for .ifo/.idx/.dict.dz/.syn dictionaries."""

    def __init__(self, directory: str | Path):
        self.directory = Path(directory)
        ifo_files = list(self.directory.glob("*.ifo"))
        if len(ifo_files) != 1:
            raise StarDictError(f"Ожидался один .ifo файл в {self.directory}")
        self.prefix = ifo_files[0].with_suffix("")
        self._entries: dict[str, tuple[int, int]] = {}
        self._synonyms: dict[str, str] = {}
        self._dict_data: bytes | None = None
        self._load_index()

    def _load_index(self) -> None:
        idx_path = self.prefix.with_suffix(".idx")
        dict_path = self.prefix.with_suffix(".dict.dz")
        if not dict_path.exists():
            dict_path = self.prefix.with_suffix(".dict")
        if not idx_path.exists() or not dict_path.exists():
            raise StarDictError("В словаре отсутствует .idx или .dict/.dict.dz файл.")

        data = idx_path.read_bytes()
        cursor = 0
        while cursor < len(data):
            end = data.find(b"\0", cursor)
            if end < 0 or end + 9 > len(data):
                raise StarDictError("Повреждён индекс StarDict (.idx).")
            word = data[cursor:end].decode("utf-8", errors="replace").casefold()
            offset, size = struct.unpack_from(">II", data, end + 1)
            self._entries[word] = (offset, size)
            cursor = end + 9

        headwords = list(self._entries)
        syn_path = self.prefix.with_suffix(".syn")
        if syn_path.exists():
            syn_data = syn_path.read_bytes()
            cursor = 0
            while cursor < len(syn_data):
                end = syn_data.find(b"\0", cursor)
                if end < 0 or end + 5 > len(syn_data):
                    raise StarDictError("Повреждён индекс словоформ (.syn).")
                form = syn_data[cursor:end].decode("utf-8", errors="replace").casefold()
                index = struct.unpack_from(">I", syn_data, end + 1)[0]
                if index < len(headwords):
                    # StarDict .syn references the sorted .idx record number.
                    self._synonyms[form] = headwords[index]
                cursor = end + 5
        self._dict_path = dict_path

    def _data(self) -> bytes:
        if self._dict_data is None:
            raw = self._dict_path.read_bytes()
            try:
                self._dict_data = gzip.decompress(raw) if self._dict_path.suffix == ".dz" else raw
            except OSError as error:
                raise StarDictError("Не удалось распаковать словарную базу.") from error
        return self._dict_data

    def lookup(self, word: str) -> DictionaryEntry | None:
        key = word.strip().casefold()
        if not key:
            return None
        headword = key if key in self._entries else self._synonyms.get(key)
        if headword is None:
            return None
        offset, size = self._entries[headword]
        article = _plain_article(self._data()[offset:offset + size])
        if not article:
            return None
        return DictionaryEntry(headword=headword, article=article)


def install_en_ru_dictionary(destination: str | Path, *, url: str = DEFAULT_DOWNLOAD_URL) -> Path:
    """Download and safely install the CC BY-SA 4.0 en-ru StarDict archive."""
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    archive_path = destination / "en-ru.download.zip"
    request = urllib.request.Request(url, headers={"User-Agent": "EnglishAssistant/1.2"})
    try:
        with urllib.request.urlopen(request, timeout=45) as response, archive_path.open("wb") as out:
            while chunk := response.read(1024 * 1024):
                out.write(chunk)
        with zipfile.ZipFile(archive_path) as archive:
            root = destination.resolve()
            for member in archive.infolist():
                target = (destination / member.filename).resolve()
                if root not in target.parents and target != root:
                    raise StarDictError("Архив содержит недопустимый путь.")
            archive.extractall(destination)
    except Exception:
        archive_path.unlink(missing_ok=True)
        raise
    finally:
        archive_path.unlink(missing_ok=True)

    candidates = list(destination.rglob("*.ifo"))
    if len(candidates) != 1:
        raise StarDictError("Архив загружен, но структура словаря неожиданная.")
    StarDictReader(candidates[0].parent)  # validate before reporting success
    get_default_dictionary.cache_clear()
    return candidates[0].parent


@lru_cache(maxsize=1)
def get_default_dictionary() -> StarDictReader | None:
    root = Path.home() / ".english_assistant" / "dictionaries" / "en-ru"
    if not root.exists():
        return None
    ifo_files = list(root.rglob("*.ifo"))
    if len(ifo_files) != 1:
        return None
    try:
        return StarDictReader(ifo_files[0].parent)
    except (OSError, ValueError, StarDictError):
        return None
