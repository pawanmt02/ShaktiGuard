# ShaktiGuard Launcher for PowerShell
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host "       SHAKTIGUARD: AI-Agentic Emergency Assistant  " -ForegroundColor Yellow
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

if (-not (Test-Path ".venv")) {
    Write-Host "[INFO] Creating Python virtual environment..." -ForegroundColor Green
    python -m venv .venv
    Write-Host "[INFO] Installing dependencies..." -ForegroundColor Green
    .\.venv\Scripts\python -m pip install -r requirements.txt
}

Write-Host "[INFO] Launching ShaktiGuard on http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process "http://localhost:8000"
.\.venv\Scripts\python main.py
