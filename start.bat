@echo off
title Smart Regulatory Reviewer — DAIS Hackathon 2026
color 0A

echo.
echo  ╔══════════════════════════════════════════════════════════════════╗
echo  ║         Smart Regulatory Reviewer — HKIA FCA AI Tool            ║
echo  ║                     Deloitte · DAIS Hackathon 2026               ║
echo  ╚══════════════════════════════════════════════════════════════════╝
echo.

REM ── Check Python is available ─────────────────────────────────────────────
where python >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python not found. Please install Python 3.10+ and try again.
    pause
    exit /b 1
)

REM ── Check .env file exists ────────────────────────────────────────────────
if not exist ".env" (
    echo [WARN] .env file not found.
    echo        Please create it with LLM_BASE_URL, LLM_API_KEY, LLM_MODEL
    echo        See README.md for details.
    pause
    exit /b 1
)

REM ── Use venv python if available, else system python ─────────────────────
if exist ".venv\Scripts\python.exe" (
    set PYTHON=.venv\Scripts\python.exe
    echo [INFO] Using virtual environment: .venv
) else (
    set PYTHON=python
    echo [INFO] Using system Python
)

echo [INFO] Starting backend on http://localhost:8001 ...
start "FCA Backend" cmd /k "%PYTHON% -m uvicorn backend.api:app --host 0.0.0.0 --port 8001"

echo [INFO] Waiting 5 seconds for backend to initialise...
timeout /t 5 /nobreak >nul

echo [INFO] Starting frontend on http://localhost:8501 ...
start "FCA Frontend" cmd /k "%PYTHON% -m streamlit run app.py --server.port 8501 --browser.gatherUsageStats false"

echo [INFO] Waiting 4 seconds then opening browser...
timeout /t 4 /nobreak >nul

start http://localhost:8501

echo.
echo  ╔══════════════════════════════════════════════════════════════╗
echo  ║  Both services are running.                                  ║
echo  ║                                                              ║
echo  ║  Frontend: http://localhost:8501  (opened in browser)        ║
echo  ║  Backend:  http://localhost:8001                             ║
echo  ║                                                              ║
echo  ║  Close the two terminal windows to stop the services.        ║
echo  ╚══════════════════════════════════════════════════════════════╝
echo.
pause