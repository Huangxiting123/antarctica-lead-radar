$ErrorActionPreference = "Stop"
Set-Location $PSScriptRoot

if (Get-Command py -ErrorAction SilentlyContinue) {
    py -3 -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    .\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name "AntarcticaLeadRadar" app.py
} else {
    python -m venv .venv
    .\.venv\Scripts\python.exe -m pip install --upgrade pip
    .\.venv\Scripts\python.exe -m pip install -r requirements-dev.txt
    .\.venv\Scripts\pyinstaller.exe --noconfirm --clean --onefile --windowed --name "AntarcticaLeadRadar" app.py
}

Write-Host "Build complete: $PSScriptRoot\dist\AntarcticaLeadRadar.exe"
