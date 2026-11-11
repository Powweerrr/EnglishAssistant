import gzip
import struct

from english_assistant.dictionary.stardict import StarDictReader


def _record(word: str, offset: int, size: int) -> bytes:
    return word.encode("utf-8") + b"\0" + struct.pack(">II", offset, size)


def test_stardict_reads_article_and_inflected_form(tmp_path):
    folder = tmp_path / "en-ru"
    folder.mkdir()
    article = "рыцарь; воин".encode("utf-8")
    (folder / "en-ru.ifo").write_text(
        "StarDict's dict ifo file\nversion=2.4.2\nwordcount=1\nidxfilesize=14\n", encoding="utf-8"
    )
    (folder / "en-ru.idx").write_bytes(_record("knight", 0, len(article)))
    (folder / "en-ru.dict.dz").write_bytes(gzip.compress(article))
    (folder / "en-ru.syn").write_bytes(b"knights\0" + struct.pack(">I", 0))

    dictionary = StarDictReader(folder)
    direct = dictionary.lookup("knight")
    inflected = dictionary.lookup("knights")
    assert direct is not None and direct.article == "рыцарь; воин"
    assert inflected is not None and inflected.headword == "knight"


def test_stardict_missing_word_returns_none(tmp_path):
    folder = tmp_path / "en-ru"
    folder.mkdir()
    article = b"hello"
    (folder / "en-ru.ifo").write_text("version=2.4.2\n", encoding="utf-8")
    (folder / "en-ru.idx").write_bytes(_record("hello", 0, len(article)))
    (folder / "en-ru.dict").write_bytes(article)
    assert StarDictReader(folder).lookup("unknown") is None


def test_synonym_index_uses_idx_record_order(tmp_path):
    folder = tmp_path / "en-ru"
    folder.mkdir()
    first, second = b"first", b"second"
    (folder / "dict.ifo").write_text("version=2.4.2\n", encoding="utf-8")
    (folder / "dict.idx").write_bytes(
        _record("alpha", 0, len(first)) + _record("beta", len(first), len(second))
    )
    (folder / "dict.dict").write_bytes(first + second)
    (folder / "dict.syn").write_bytes(b"betas\0" + struct.pack(">I", 1))
    assert StarDictReader(folder).lookup("betas").article == "second"
