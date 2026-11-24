# Lokale API mit dem eigenen Claude-Abo, zum Testen der Web-UI mit `npm run dev`.
#
# Nur für die Entwicklung auf diesem Rechner (Spec 001, AK-6.3): Die API läuft auf 127.0.0.1 und
# ruft das Modell über die Claude-Code-CLI auf (LLM_BACKEND=claude-code). Container und Demo
# nutzen weiterhin nur einen API-Key.
#
# Voraussetzungen: `docker compose up -d db`, `uv sync`, Claude Code installiert und angemeldet.
# Belegt der Container `app` Port 8000, zuerst `docker compose stop app web` oder einen anderen
# Port wählen und die Web-UI mit `API_TARGET` starten (siehe README, «Web-UI (Entwicklung)»).
#
#   .\scripts\dev-api.ps1                     # Port 8000, Haiku 5.5
#   .\scripts\dev-api.ps1 -Port 8011 -Model claude-sonnet-5-5

param(
    [int]$Port = 8000,
    [string]$Model = "claude-haiku-5-5",
    [string]$Effort = "low"
)
$ErrorActionPreference = "Stop"
$root = Split-Path -Parent $PSScriptRoot

if (-not (Get-Command claude -ErrorAction SilentlyContinue)) {
    throw "Claude Code CLI (claude) nicht gefunden. Installieren und mit 'claude' einmal anmelden."
}
if (Get-NetTCPConnection -LocalPort $Port -State Listen -ErrorAction SilentlyContinue) {
    throw "Port $Port ist belegt (läuft der Container 'app'?). 'docker compose stop app web' oder -Port wählen."
}

$env:LLM_BACKEND = "claude-code"
$env:ANTHROPIC_MODEL = $Model
$env:ANTHROPIC_EFFORT = $Effort

# Statt `uv run` den Basis-Interpreter aus .venv\pyvenv.cfg mit den Paketen aus .venv: So läuft
# die API auch, wenn Windows (App Control) .venv\Scripts\python.exe sperrt.
$venvConfig = Join-Path $root ".venv\pyvenv.cfg"
if (-not (Test-Path $venvConfig)) { throw "Keine .venv gefunden. Zuerst 'uv sync'." }
$baseDir = (Get-Content $venvConfig | Where-Object { $_ -match "^home\s*=" }) -replace "^home\s*=\s*", ""
$python = Join-Path $baseDir.Trim() "python.exe"
$env:PYTHONPATH = "$root\src;$root\.venv\Lib\site-packages"

Write-Host "API mit Claude-Abo ($Model, $Effort) auf http://127.0.0.1:$Port (Beenden mit Ctrl+C)"
Set-Location $root
& $python -m uvicorn parlrag.api.main:app --host 127.0.0.1 --port $Port
