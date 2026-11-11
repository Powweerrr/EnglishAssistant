$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

function Find-Python {
    $candidates = @()

    # Prefer the project's existing virtual environment. This works even when
    # Python itself is not available through PATH.
    $projectVenv = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
    if (Test-Path $projectVenv) { $candidates += $projectVenv }

    if ($env:VIRTUAL_ENV) {
        $activePython = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
        if (Test-Path $activePython) { $candidates += $activePython }
    }

    $buildVenv = Join-Path $PSScriptRoot ".build-venv\Scripts\python.exe"
    if (Test-Path $buildVenv) { $candidates += $buildVenv }

    $pyLauncher = Get-Command py -ErrorAction SilentlyContinue
    if ($pyLauncher) {
        try {
            & $pyLauncher.Source -3.12 --version *> $null
            if ($LASTEXITCODE -eq 0) { return @{ Command = $pyLauncher.Source; Prefix = @("-3.12") } }
        } catch { }
    }

    $pythonCommand = Get-Command python -ErrorAction SilentlyContinue
    if ($pythonCommand) { $candidates += $pythonCommand.Source }

    foreach ($candidate in $candidates) {
        if (Test-Path $candidate) {
            try {
                & $candidate --version *> $null
                if ($LASTEXITCODE -eq 0) { return @{ Command = $candidate; Prefix = @() } }
            } catch { }
        }
    }

    throw "Python не найден. Если у тебя уже есть .venv, проверь файл .venv\Scripts\python.exe. Иначе установи Python 3.12 и включи Add Python to PATH."
}

Write-Host "[1/5] Locating Python..." -ForegroundColor Cyan
$pythonInfo = Find-Python
$basePython = $pythonInfo.Command
$basePrefix = $pythonInfo.Prefix
& $basePython @basePrefix --version

# Reuse the project's environment when present. Otherwise create a local build venv.
$projectPython = Join-Path $PSScriptRoot ".venv\Scripts\python.exe"
if (Test-Path $projectPython) {
    $buildPython = $projectPython
} elseif ($env:VIRTUAL_ENV -and (Test-Path (Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"))) {
    $buildPython = Join-Path $env:VIRTUAL_ENV "Scripts\python.exe"
} else {
    Write-Host "[2/5] Creating isolated build environment..." -ForegroundColor Cyan
    $buildVenv = Join-Path $PSScriptRoot ".build-venv"
    if (-not (Test-Path (Join-Path $buildVenv "Scripts\python.exe"))) {
        & $basePython @basePrefix -m venv $buildVenv
        if ($LASTEXITCODE -ne 0) { throw "Could not create the build virtual environment." }
    }
    $buildPython = Join-Path $buildVenv "Scripts\python.exe"
}

Write-Host "[3/5] Installing build dependencies..." -ForegroundColor Cyan
& $buildPython -m pip install --upgrade pip setuptools wheel
if ($LASTEXITCODE -ne 0) { throw "pip upgrade failed." }
& $buildPython -m pip install -e ".[build,test]"
if ($LASTEXITCODE -ne 0) { throw "Dependency installation failed." }

Write-Host "[4/5] Running tests and lint..." -ForegroundColor Cyan
& $buildPython -m pytest -q
if ($LASTEXITCODE -ne 0) { throw "Tests failed; executable was not built." }
& $buildPython -m ruff check src tests
if ($LASTEXITCODE -ne 0) { throw "Ruff reported issues; executable was not built." }

Write-Host "[5/5] Building Windows executable..." -ForegroundColor Cyan
if (Test-Path "dist\EnglishAssistant.exe") { Remove-Item "dist\EnglishAssistant.exe" -Force }
& $buildPython -m PyInstaller --noconfirm --clean --windowed --onefile `
    --name EnglishAssistant `
    --paths src `
    --collect-all rapidocr `
    --collect-all onnxruntime `
    --collect-all cv2 `
    --collect-all pynput `
    --collect-all mss `
    --collect-all pywinauto `
    --collect-all PySide6 `
    --hidden-import rapidocr `
    --hidden-import onnxruntime `
    --hidden-import PIL `
    --hidden-import pynput.keyboard._win32 `
    src\english_assistant\main.py
if ($LASTEXITCODE -ne 0) { throw "PyInstaller build failed." }

$exe = Join-Path $PSScriptRoot "dist\EnglishAssistant.exe"
if (-not (Test-Path $exe)) { throw "PyInstaller returned success but dist\EnglishAssistant.exe is missing." }
Write-Host "Build complete: $exe" -ForegroundColor Green
