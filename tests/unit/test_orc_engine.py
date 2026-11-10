from english_assistant.ocr.engine import normalize_ocr_lines


def test_normalize_ocr_lines():
    result = normalize_ocr_lines(
        [
            "  Hello world  ",
            "",
            "This is a test.",
            "   ",
        ]
    )

    assert result == "Hello world\nThis is a test."


def test_normalize_empty_result():
    assert normalize_ocr_lines([]) == ""
    assert normalize_ocr_lines(None) == ""


def test_normalize_ignores_empty_lines():
    result = normalize_ocr_lines(["", "  ", "English"])

    assert result == "English"
