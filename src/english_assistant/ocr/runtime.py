from __future__ import annotations

from functools import lru_cache
from threading import Lock

_OCR_LOCK = Lock()


@lru_cache(maxsize=1)
def get_engine():
    from rapidocr import RapidOCR
    return RapidOCR()
