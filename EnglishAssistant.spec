# Alternative PyInstaller spec. build_windows.ps1 is the supported build entry point.
from PyInstaller.utils.hooks import collect_all

rapid_datas, rapid_bins, rapid_hidden = collect_all("rapidocr")
ort_datas, ort_bins, ort_hidden = collect_all("onnxruntime")
cv_datas, cv_bins, cv_hidden = collect_all("cv2")
pynput_datas, pynput_bins, pynput_hidden = collect_all("pynput")
mss_datas, mss_bins, mss_hidden = collect_all("mss")

a = Analysis(
    ["src/english_assistant/main.py"],
    pathex=["src"],
    binaries=rapid_bins + ort_bins + cv_bins + pynput_bins + mss_bins,
    datas=rapid_datas + ort_datas + cv_datas + pynput_datas + mss_datas,
    hiddenimports=rapid_hidden + ort_hidden + cv_hidden + pynput_hidden + mss_hidden,
    hookspath=[], hooksconfig={}, runtime_hooks=[], excludes=[], noarchive=False,
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [], name="EnglishAssistant",
    debug=False, bootloader_ignore_signals=False, strip=False, upx=True,
    console=False, disable_windowed_traceback=False, argv_emulation=False,
    target_arch=None, codesign_identity=None, entitlements_file=None,
)
