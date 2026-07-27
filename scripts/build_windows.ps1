
param(
    [string]$AppVersion = "1.0.0"
)


# Bewusst NICHT "Stop": native Tools (PyInstaller, ISCC) schreiben auch reine
# INFO-Meldungen nach stderr. Mit ErrorActionPreference=Stop würde PowerShell
# 5.1 das fälschlich als Abbruchfehler werten. Fehler werden stattdessen
# explizit über $LASTEXITCODE bzw. try/catch geprüft.
$ErrorActionPreference = "Continue"

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

function Remove-DirWithRetry {
    param([string]$Path, [int]$MaxAttempts = 5, [int]$DelaySeconds = 2)
    if (-not (Test-Path $Path)) { return }
    for ($i = 1; $i -le $MaxAttempts; $i++) {
        try {
            Remove-Item -Path $Path -Recurse -Force -ErrorAction Stop
            return
        } catch {
            if ($i -eq $MaxAttempts) {
                Write-Host "Konnte '$Path' nicht löschen (Datei gesperrt, z. B. durch Virenscanner, OneDrive-Sync" -ForegroundColor Yellow
                Write-Host "oder eine noch laufende DTF-Korrektur.exe). Bitte manuell prüfen/löschen und erneut starten." -ForegroundColor Yellow
                throw
            }
            Write-Host "  '$Path' ist noch gesperrt, versuche erneut ($i/$MaxAttempts) ..." -ForegroundColor DarkYellow
            Start-Sleep -Seconds $DelaySeconds
        }
    }
}

$IconPath = Join-Path $ProjectRoot "resources\icons\app_icon.ico"
if (-not (Test-Path $IconPath)) {
    Write-Host "Icon nicht gefunden - erzeuge es ..." -ForegroundColor Cyan
    & $Python scripts\generate_icon.py
}

Write-Host "Räume alte Build-Ordner auf ..." -ForegroundColor Cyan
Remove-DirWithRetry -Path (Join-Path $ProjectRoot "build")
Remove-DirWithRetry -Path (Join-Path $ProjectRoot "dist")

Write-Host "Baue DTF-Korrektur.exe mit PyInstaller ..." -ForegroundColor Cyan

$AddData = @()
if (Test-Path "resources") {
    $AddData += "--add-data"
    $AddData += "resources;resources"
}

# Kein --clean: der Ordner wurde oben bereits selbst (mit Wiederholungsversuchen)
# entfernt. PyInstallers eigenes --clean bricht bei einem Locking-Konflikt
# (z. B. Virenscanner, OneDrive-Sync) sofort mit PermissionError ab.
& $Python -m PyInstaller `
    --name "DTF-Korrektur" `
    --windowed `
    --onedir `
    --noconfirm `
    --icon $IconPath `
    --paths . `
    @AddData `
    src/app/main.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "Build fehlgeschlagen." -ForegroundColor Red
    exit $LASTEXITCODE
}

Write-Host ""
Write-Host "Fertig. Ausgabe unter: dist\DTF-Korrektur\DTF-Korrektur.exe" -ForegroundColor Green

# --- Konsolen-Build für den Kommandozeilen-/Automatisierungsmodus -------
# Eigener, separater Build (statt eines Schalters an der GUI-EXE): die GUI
# wird mit --windowed gebaut und hat daher gar kein Konsolenfenster - stdout/
# stderr/Exit-Codes kämen bei einem Taskplaner-Aufruf nirgends an. src/cli.py
# hat bewusst keine PySide6-Abhängigkeit (siehe dortiger Moduldocstring),
# wodurch dieser Build spürbar kleiner ausfällt und kein Qt mitbringt.
Write-Host ""
Write-Host "Baue DTF-Korrektur-CLI.exe (Kommandozeilenmodus) mit PyInstaller ..." -ForegroundColor Cyan

& $Python -m PyInstaller `
    --name "DTF-Korrektur-CLI" `
    --console `
    --onedir `
    --noconfirm `
    --paths . `
    @AddData `
    src/cli.py

if ($LASTEXITCODE -ne 0) {
    Write-Host "CLI-Build fehlgeschlagen (GUI-Build ist trotzdem nutzbar)." -ForegroundColor Yellow
} else {
    Write-Host "Fertig. Ausgabe unter: dist\DTF-Korrektur-CLI\DTF-Korrektur-CLI.exe" -ForegroundColor Green
}

# --- Installer (Inno Setup) ---------------------------------------------
$IsccCandidates = @(
    "$env:LOCALAPPDATA\Programs\Inno Setup 6\ISCC.exe",
    "${env:ProgramFiles(x86)}\Inno Setup 6\ISCC.exe",
    "$env:ProgramFiles\Inno Setup 6\ISCC.exe"
)
$Iscc = $IsccCandidates | Where-Object { Test-Path $_ } | Select-Object -First 1

if (-not $Iscc) {
    $found = Get-Command ISCC.exe -ErrorAction SilentlyContinue
    if ($found) { $Iscc = $found.Source }
}

if ($Iscc) {
    Write-Host ""
    Write-Host "Erzeuge Windows-Installer mit Inno Setup ..." -ForegroundColor Cyan
    & $Iscc "scripts\installer.iss" "/DMyAppVersion=$AppVersion"
    if ($LASTEXITCODE -ne 0) {
        Write-Host "Installer-Build fehlgeschlagen (PyInstaller-Build ist trotzdem nutzbar)." -ForegroundColor Yellow
    } else {
        Write-Host "Installer erstellt: dist\installer\DTF-Korrektur-Setup.exe" -ForegroundColor Green
    }
} else {
    Write-Host ""
    Write-Host "Inno Setup (ISCC.exe) nicht gefunden - es wurde kein Setup.exe erstellt." -ForegroundColor Yellow
    Write-Host "Installieren mit: winget install --id JRSoftware.InnoSetup" -ForegroundColor Yellow
    Write-Host "Danach dieses Skript erneut ausführen, oder manuell:" -ForegroundColor Yellow
    Write-Host "  ISCC.exe scripts\installer.iss" -ForegroundColor Yellow
}
