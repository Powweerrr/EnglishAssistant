from __future__ import annotations

import re
from dataclasses import dataclass


_WORD = re.compile(r"^[A-Za-z]+(?:['’-][A-Za-z]+)*(?:-[A-Za-z]+)*$")


@dataclass(frozen=True, slots=True)
class AccessibleWord:
    word: str
    context: str
    bounds: tuple[int, int, int, int] | None = None
    method: str = "windows-uia-textpattern"


def locate_accessible_word(x: int, y: int) -> AccessibleWord | None:
    """Get the word at a screen point through Windows UI Automation TextPattern.

    Returns None when the target does not expose TextPattern (common for games,
    canvas-rendered text, video and protected surfaces). OCR remains the fallback.
    """
    try:
        from pywinauto import Desktop

        element = Desktop(backend="uia").from_point(x, y)
        text_pattern = element.iface_text
        word_range = text_pattern.RangeFromPoint((int(x), int(y)))
        word_range.ExpandToEnclosingUnit(2)  # TextUnit.Word
        word = (word_range.GetText(-1) or "").strip()
        if not _WORD.fullmatch(word):
            return None

        context_range = word_range.Clone()
        context_range.ExpandToEnclosingUnit(4)  # TextUnit.Paragraph
        context = (context_range.GetText(500) or word).strip()

        bounds = None
        rectangles = word_range.GetBoundingRectangles()
        if rectangles and len(rectangles) >= 4:
            left, top, width, height = (float(value) for value in rectangles[:4])
            bounds = (round(left), round(top), round(left + width), round(top + height))
        return AccessibleWord(word=word, context=context, bounds=bounds)
    except Exception:
        # UIA providers are inconsistent; never make lookup fail solely because
        # the target application does not expose accessible text.
        return None
