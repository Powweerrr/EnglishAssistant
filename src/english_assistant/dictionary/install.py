from pathlib import Path

from english_assistant.dictionary.stardict import install_en_ru_dictionary


def main() -> int:
    destination = Path.home() / ".english_assistant" / "dictionaries" / "en-ru"
    installed = install_en_ru_dictionary(destination)
    print(f"EN–RU dictionary installed: {installed}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
