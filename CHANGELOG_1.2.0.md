# 1.2.0 — Quick Lookup foundation (development build)

## Added
- Windows UI Automation TextPattern lookup at the pointer, with word and paragraph extraction when the target exposes accessible text.
- StarDict reader for `.ifo`, `.idx`, `.dict` / `.dict.dz`, and `.syn` data.
- Optional EN–RU dictionary installer targeting `%USERPROFILE%\\.english_assistant\\dictionaries\\en-ru`.
- Local dictionary lookup path for Dictionary and Quick Lookup.

## Changed
- Quick Lookup online dictionary and translation requests run concurrently with a shared four-second wait budget.
- Slow network tasks no longer hold the Quick Lookup worker open through `ThreadPoolExecutor.__exit__`.
- Windows executable build collects the optional pywinauto runtime.

## Not yet verified
- UI Automation against real Windows applications and games.
- OCR word selection against the user's actual game screenshots.
- First-run dictionary download from the user's Windows environment.
- Full PyInstaller executable launch on Windows.

This is a development checkpoint, not a finished application release.
