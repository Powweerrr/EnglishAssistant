from __future__ import annotations

import re
from dataclasses import dataclass

from PIL import Image

from english_assistant.capture.cursor_capture import CursorCapture
from english_assistant.ocr.runtime import _OCR_LOCK, get_engine


@dataclass(frozen=True, slots=True)
class LocatedWord:
    word: str
    context: str
    confidence: float
    bounds: tuple[int, int, int, int]
    method: str = "ocr-estimated-word-box"


_TOKEN_RE = re.compile(r"[A-Za-z]+(?:['’][A-Za-z]+)*(?:-[A-Za-z]+)*")


def _polygon_bounds(polygon) -> tuple[float, float, float, float]:
    points = list(polygon)
    xs = [float(point[0]) for point in points]
    ys = [float(point[1]) for point in points]
    return min(xs), min(ys), max(xs), max(ys)


def _glyph_weight(char: str) -> float:
    if char in "ilI.,'!:;|":
        return 0.42
    if char in "mwMW@%&":
        return 1.35
    if char.isupper():
        return 1.08
    return 0.86


def _word_boxes(text: str, bounds: tuple[float, float, float, float]):
    tokens = list(_TOKEN_RE.finditer(text))
    if not tokens:
        return []
    x1, y1, x2, y2 = bounds
    total = sum(_glyph_weight(ch) for token in tokens for ch in token.group())
    # Allocate a small share to whitespace; this is an OCR fallback, not exact glyph geometry.
    spaces = max(0, len(tokens) - 1)
    total += spaces * 0.55
    cursor = x1
    output = []
    for token in tokens:
        weight = sum(_glyph_weight(ch) for ch in token.group())
        width = (x2 - x1) * weight / total
        output.append((token.group(), (cursor, y1, cursor + width, y2)))
        cursor += width + ((x2 - x1) * 0.55 / total)
    return output


def _distance_to_rect(x: float, y: float, rect: tuple[float, float, float, float]) -> float:
    left, top, right, bottom = rect
    dx = max(left - x, 0.0, x - right)
    dy = max(top - y, 0.0, y - bottom)
    return (dx * dx + dy * dy) ** 0.5


def _unpack_result(result):
    boxes = getattr(result, "boxes", None)
    texts = getattr(result, "txts", None)
    scores = getattr(result, "scores", None)
    if boxes is None and isinstance(result, (tuple, list)) and len(result) >= 2:
        boxes, texts = result[0], result[1]
        scores = result[2] if len(result) > 2 else None
    return ([] if boxes is None else boxes,
            [] if texts is None else texts,
            [] if scores is None else scores)


def locate_word(capture: CursorCapture) -> LocatedWord:
    with _OCR_LOCK:
        result = get_engine()(capture.image)
    boxes, texts, scores = _unpack_result(result)
    candidates = []
    for index, (polygon, text) in enumerate(zip(boxes, texts)):
        if not isinstance(text, str) or not text.strip():
            continue
        local_bounds = _polygon_bounds(polygon)
        global_bounds = (
            local_bounds[0] + capture.origin_x,
            local_bounds[1] + capture.origin_y,
            local_bounds[2] + capture.origin_x,
            local_bounds[3] + capture.origin_y,
        )
        confidence = float(scores[index]) if index < len(scores) else 0.5
        for token, token_bounds in _word_boxes(text, local_bounds):
            global_token_bounds = (
                token_bounds[0] + capture.origin_x,
                token_bounds[1] + capture.origin_y,
                token_bounds[2] + capture.origin_x,
                token_bounds[3] + capture.origin_y,
            )
            distance = _distance_to_rect(capture.cursor_x, capture.cursor_y, global_token_bounds)
            candidates.append((distance, confidence, token, text.strip(), global_token_bounds))

    if not candidates:
        raise ValueError("OCR не обнаружил английское слово рядом с курсором.")

    candidates.sort(key=lambda item: (item[0], -item[1]))
    distance, confidence, word, context, bounds = candidates[0]
    if distance > 24:
        raise ValueError("Курсор не попал в распознанное слово. Наведи его ближе к центру слова.")
    return LocatedWord(
        word=word,
        context=context,
        confidence=confidence,
        bounds=tuple(round(value) for value in bounds),
    )
