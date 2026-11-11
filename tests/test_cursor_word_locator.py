from types import SimpleNamespace

import pytest

from english_assistant.capture.cursor_capture import CursorCapture
from english_assistant.ocr import word_locator


class FakeEngine:
    def __call__(self, image):
        return SimpleNamespace(
            boxes=[[[0, 0], [200, 0], [200, 30], [0, 30]]],
            txts=["The brave knight"],
            scores=[0.97],
        )


def test_locator_selects_word_near_pointer(monkeypatch):
    monkeypatch.setattr(word_locator, "get_engine", lambda: FakeEngine())
    capture = CursorCapture(image=object(), origin_x=100, origin_y=200,
                            cursor_x=165, cursor_y=215)
    result = word_locator.locate_word(capture)
    assert result.word == "brave"
    assert result.context == "The brave knight"
    assert result.confidence == pytest.approx(0.97)


def test_locator_rejects_pointer_outside_recognized_word(monkeypatch):
    monkeypatch.setattr(word_locator, "get_engine", lambda: FakeEngine())
    capture = CursorCapture(image=object(), origin_x=100, origin_y=200,
                            cursor_x=500, cursor_y=500)
    with pytest.raises(ValueError, match="Курсор не попал"):
        word_locator.locate_word(capture)


def test_word_box_split_handles_apostrophes_and_hyphens():
    boxes = word_locator._word_boxes("don't re-enter", (0, 0, 200, 20))
    assert [word for word, _ in boxes] == ["don't", "re-enter"]
