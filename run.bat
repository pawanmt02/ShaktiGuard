@echo off
echo ====================================================
echo        SHAKTIGUARD: AI-Agentic Emergency Assistant
echo ====================================================
echo.

IF NOT EXIST ".venv" (
    echo [INFO] Creating Python virtual environment...
    python -m venv .venv
    echo [INFO] Installing dependencies from requirements.txt...
    .\.venv\Scripts\python -m pip install -r requirements.txt
)

echo [INFO] Starting ShaktiGuard server on http://localhost:8000 ...
.\.venv\Scripts\python main.py
pause
