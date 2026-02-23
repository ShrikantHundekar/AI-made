@echo off
echo ========================================
echo   AI Pulse Dashboard (ZYROX) — Startup
echo ========================================

REM Check Python is installed
python --version >nul 2>&1
IF ERRORLEVEL 1 (
    echo ERROR: Python not found. Please install Python 3.10+
    pause
    exit /b 1
)

REM Install dependencies if needed
echo [1/4] Installing dependencies...
pip install -r requirements.txt --quiet

REM Copy .env.example to .env if .env doesn't exist
IF NOT EXIST .env (
    echo [INFO] Creating .env from .env.example...
    copy .env.example .env >nul
    echo [INFO] IMPORTANT: Edit .env to add your Reddit + Supabase credentials!
    echo.
)

REM Create directories
IF NOT EXIST data mkdir data
IF NOT EXIST .tmp mkdir .tmp

echo [2/4] Testing Supabase connection...
python tools/supabase_sync.py --test
IF ERRORLEVEL 1 (
    echo [WARN] Supabase unreachable — running in local-only mode
)

echo [3/4] Running initial article scrape...
python tools/scraper.py
python tools/store.py

echo [4/4] Starting dashboard server...
echo.
echo  Dashboard ^-^> http://localhost:3737
echo  Supabase  ^-^> https://axuhqdtkvtorvzocpnbn.supabase.co
echo  Press Ctrl+C to stop
echo.
python server.py

pause
