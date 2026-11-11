# EnglishAssistant 1.1.0

Desktop Windows application for reading English from the screen and studying it. The project is a complete source package with a Windows build script; the archive is not itself a precompiled Windows binary.

## Included functionality

- Screen-region selection with mouse; Escape cancels selection.
- Screenshot capture and OCR using RapidOCR + ONNX Runtime.
- Global Windows shortcut `Alt+Q` for cursor-word lookup and `Ctrl+Shift+E` for screen-region capture.
- Editable OCR text and manual text input.
- Translation EN → RU through MyMemory.
- Cursor lookup: captures a small area around the pointer, detects the nearest English word with OCR, then fetches dictionary information and translation in parallel.
- A compact non-activating popup appears near the pointer; `Alt+Q` hides it or starts another lookup.
- Quick lookup cache is stored in SQLite to avoid repeating successful network requests.
- English dictionary: phonetics, parts of speech, definitions, examples and synonyms through Free Dictionary API.
- Grammar and spelling suggestions through LanguageTool.
- Local phrase matcher for idioms and phrasal verbs.
- Local CEFR word lookup and approximate level distribution. This is a learning aid, not a certified CEFR test.
- Run-all action: invokes all five domains; a failed online domain does not prevent local domains from returning results.
- SQLite vocabulary and query history stored in the user's profile, not in the project directory.
- Vocabulary entries can be edited at save time; rows can be deleted.
- Anki-compatible CSV export (`Front;Back;Example`, UTF-8 BOM).

## Requirements

- Windows 10/11, 64-bit.
- Python 3.12 (recommended) or 3.13 installed, or an existing project `.venv`.
- Internet for translation, dictionary and grammar services. OCR and local reference lists do not require an account.

## Run from source

Open PowerShell in the project folder:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install --upgrade pip
python -m pip install -e ".[test]"
python -m english_assistant
```

If `.venv` already exists, do not recreate it; activate it and install the project into it.

## Build the Windows EXE

Run:

```powershell
Set-ExecutionPolicy -Scope Process Bypass
.\build_windows.ps1
```

The build script first looks for `.venv\Scripts\python.exe`, then the active virtual environment, then `.build-venv`, the `py -3.12` launcher and finally `python` on PATH. This specifically avoids the earlier failure where the script ignored an already-created virtual environment.

The script installs build dependencies, runs pytest and Ruff, and then builds:

```text
dist\EnglishAssistant.exe
```

The executable is a Windows binary and cannot be produced by this Linux build environment. To obtain it without a local Windows build, push this project to GitHub and run **Actions → Build Windows EXE → Run workflow**. The workflow uploads `EnglishAssistant.exe` as an artifact.

## First launch / OCR

RapidOCR may initialize or download its ONNX model on the first run. Allow the first OCR request additional time. Cursor capture uses `mss` and chooses the monitor containing the pointer. The region-selection workflow still uses the primary monitor.

Cursor word selection currently uses OCR text boxes and estimates individual word boundaries from the recognized line width. This is a fallback geometry estimate: proportional fonts, unusual spacing, vertical text, and game-specific rendering can cause a neighboring word to be selected. UI Automation text-range extraction is not yet integrated. The feature must be tested against real game screenshots on Windows before being treated as reliable.

## Data and privacy

SQLite database location:

```text
%USERPROFILE%\.english_assistant\english_assistant.sqlite3
```

Vocabulary and history remain local. Text sent to Translation, Dictionary or Grammar is transmitted to the corresponding public service. Do not send confidential text to those online domains.

## Known functional boundaries

- MyMemory, Free Dictionary and LanguageTool are public online services; availability, rate limits and quality are outside this app's control.
- Idiom/phrasal-verb and CEFR datasets are local starter reference lists, not exhaustive dictionaries. The CEFR output is a rough lexical lookup, not a complete language-level assessment.
- Dictionary lookup is for one word or expression at a time; the app asks which term to look up when the input is a longer sentence.
- Region selection currently uses the primary monitor only. Cursor capture selects the monitor under the pointer.
- This package has been syntax-compiled and its domain/storage tests have been run in the packaging environment. The Qt GUI, live online APIs and PyInstaller Windows binary must still be exercised on Windows; the Linux environment cannot certify those runtime behaviours.


## 1.2.0 core changes (work in progress)

- Quick Lookup now tries Windows UI Automation TextPattern at the pointer before capturing an OCR region. This works only in applications that expose accessible text; canvas-rendered games still require OCR.
- Added a StarDict reader for an optional offline English–Russian dictionary, including inflection (`.syn`) lookup.
- Quick Lookup checks the local dictionary before making any network request.
- Online dictionary and translation requests now run in parallel under one shared 4-second wait budget; slow requests no longer block the lookup worker while the executor context manager waits for them.

### Install the offline English–Russian dictionary

The dictionary data is not bundled in this source archive. It is published by the upstream `koreader-dicts` project under CC BY-SA 4.0. Install it once while connected to the internet:

```powershell
py -3.12 scripts/install_dictionary.py
```

The data is installed under `%USERPROFILE%\.english_assistant\dictionaries\en-ru`. Attribution and source links are in `data/dictionaries/ATTRIBUTION.md`.

**Compatibility note:** UI Automation is not available for many games and GPU-rendered interfaces. In those cases OCR is still used. This archive has automated unit tests, but the UI Automation integration and game OCR must still be validated on the target Windows machine.
