import sys
from types import SimpleNamespace

from english_assistant.ocr.uia_text import locate_accessible_word


class FakeRange:
    def __init__(self, text):
        self.text = text
        self.expanded = []

    def ExpandToEnclosingUnit(self, unit):
        self.expanded.append(unit)

    def GetText(self, maximum):
        return self.text[:maximum] if maximum >= 0 else self.text

    def Clone(self):
        return FakeRange("The brave knight entered the hall.")

    def GetBoundingRectangles(self):
        return [10.0, 20.0, 40.0, 14.0]


class FakeTextPattern:
    def RangeFromPoint(self, point):
        assert point == (120, 220)
        return FakeRange("knight")


class FakeElement:
    iface_text = FakeTextPattern()


def test_uia_returns_exact_word_and_paragraph(monkeypatch):
    monkeypatch.setitem(sys.modules, "pywinauto", SimpleNamespace(
        Desktop=lambda backend: SimpleNamespace(from_point=lambda x, y: FakeElement())
    ))
    result = locate_accessible_word(120, 220)
    assert result is not None
    assert result.word == "knight"
    assert result.context == "The brave knight entered the hall."
    assert result.bounds == (10, 20, 50, 34)


def test_uia_rejects_non_word_text(monkeypatch):
    class BadPattern:
        def RangeFromPoint(self, point):
            return FakeRange("PowerShell> py -3.12")

    monkeypatch.setitem(sys.modules, "pywinauto", SimpleNamespace(
        Desktop=lambda backend: SimpleNamespace(
            from_point=lambda x, y: SimpleNamespace(iface_text=BadPattern())
        )
    ))
    assert locate_accessible_word(1, 2) is None
