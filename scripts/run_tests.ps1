
$ErrorActionPreference = "Stop"

$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$ProjectRoot = Split-Path -Parent $ScriptDir
Set-Location $ProjectRoot

$Python = Join-Path $ProjectRoot ".venv\Scripts\python.exe"
if (-not (Test-Path $Python)) {
    Write-Host "Virtuelle Umgebung nicht gefunden unter .venv - bitte zuerst erstellen:" -ForegroundColor Yellow
    Write-Host "  py -3.12 -m venv .venv"
    Write-Host "  .venv\Scripts\pip install -r requirements.txt"
    exit 1
}

& $Python -m pytest tests/ -v
exit $LASTEXITCODE
