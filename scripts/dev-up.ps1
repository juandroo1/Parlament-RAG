# Lokale Entwicklung mit dem eigenen Claude-Abo, mit einem Befehl.
#
# Startet die Datenbank im Container und stoppt die Container `app` und `web`: Sie antworten nur
# mit einem API-Key und belegen Port 8000. Danach startet die Web-UI (Vite) und im Vordergrund die
# API mit dem Claude-Abo (scripts/dev-api.ps1, LLM_BACKEND=claude-code). Ctrl+C beendet API und
# Web-UI; die Datenbank läuft weiter. Nur für die Entwicklung auf diesem Rechner (Spec 001, AK-6.3).
#
# Voraussetzungen: Docker, `uv sync`, `cd web; npm install`, Claude Code installiert und angemeldet.
#
#   .\scripts\dev-up.ps1                                  # API :8000, Web-UI :5173, Haiku 5.5
#   .\scripts\dev-up.ps1 -WebPort 5180 -Model claude-sonnet-5-5

param(
    [int]$Port = 8000,
    [int]$WebPort = 5173,
    [string]$Model = "claude-haiku-5-5",
    [string]$Effort = "low"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot
$web = Join-Path $root "web"
$vite = Join-Path $web "node_modules\vite\bin\vite.js"

# Alles prüfen, bevor etwas gestartet oder gestoppt wird.
foreach ($tool in "docker", "node", "claude") {
    if (-not (Get-Command $tool -ErrorAction SilentlyContinue)) {
        throw "$tool nicht gefunden. Voraussetzungen: Docker, Node.js 24, Claude Code (einmal 'claude' starten und anmelden)."
    }
}
if (-not (Test-Path $vite)) { throw "Web-Abhängigkeiten fehlen. Zuerst 'cd web; npm install'." }
if (-not (Test-Path (Join-Path $root ".venv\pyvenv.cfg"))) { throw "Keine .venv gefunden. Zuerst 'uv sync'." }
if (Get-NetTCPConnection -LocalPort $WebPort -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $WebPort ist belegt (läuft schon eine Web-UI?). Beenden oder -WebPort wählen."
}

Set-Location $root
Write-Host "Datenbank starten ..."
docker compose up -d --wait db
if ($LASTEXITCODE -ne 0) { throw "Die Datenbank startete nicht (docker compose up -d --wait db)." }
Write-Host "Container app und web stoppen (sie antworten nur mit API-Key) ..."
docker compose stop app web
if ($LASTEXITCODE -ne 0) { throw "'docker compose stop app web' schlug fehl." }

# Vite direkt mit node starten (nicht über npm.cmd), damit Ctrl+C ohne Rückfrage beendet.
$env:API_TARGET = "http://127.0.0.1:$Port"
$webProcess = Start-Process -FilePath "node" -WorkingDirectory $web -NoNewWindow -PassThru `
    -ArgumentList "`"$vite`"", "--port", $WebPort, "--strictPort"
Write-Host "Web-UI auf http://127.0.0.1:$WebPort (leitet /api an $env:API_TARGET weiter)"
try {
    & (Join-Path $PSScriptRoot "dev-api.ps1") -Port $Port -Model $Model -Effort $Effort
}
finally {
    if (-not $webProcess.HasExited) { & taskkill /PID $webProcess.Id /T /F | Out-Null }
    Write-Host "API und Web-UI beendet. Die Datenbank läuft weiter (stoppen: docker compose stop db)."
}
