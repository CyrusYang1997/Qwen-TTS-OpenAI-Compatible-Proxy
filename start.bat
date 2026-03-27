@echo off
chcp 65001 >nul
title Qwen-TTS OpenAI Proxy
setlocal enabledelayedexpansion

echo ====================================
echo   Qwen-TTS OpenAI Compatible Proxy
echo ====================================
echo.

REM === Check Python ===
python --version >nul 2>&1
if %errorlevel% neq 0 (
    echo [WARN] Python not found. Attempting to install Python 3.10...
    echo.

    winget --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] winget not available. Please install Python 3.10 manually:
        echo         https://www.python.org/downloads/
        pause
        exit /b 1
    )

    echo [INFO] Installing Python 3.10 via winget...
    winget install Python.Python.3.10 --accept-package-agreements --accept-source-agreements

    REM Refresh PATH after install
    set "PATH=%LOCALAPPDATA%\Programs\Python\Python310;%LOCALAPPDATA%\Programs\Python\Python310\Scripts;%PATH%"

    REM Re-check Python regardless of winget exit code
    python --version >nul 2>&1
    if !errorlevel! neq 0 (
        echo [ERROR] Python still not available after install attempt.
        echo         Please install Python 3.10 manually: https://www.python.org/downloads/
        pause
        exit /b 1
    )
    echo [INFO] Python is ready.
    echo.
)

for /f "tokens=*" %%v in ('python --version 2^>^&1') do echo [INFO] %%v

REM === Check .env ===
if not exist ".env" (
    if exist ".env.example" (
        echo [WARN] .env not found. Copying from .env.example...
        copy ".env.example" ".env" >nul
        echo [INFO] Please edit .env and set your DASHSCOPE_API_KEY.
        echo.
    )
)

REM === Port Selection (5s timeout) ===
set "PORT=8000"
echo [INFO] Default port: 8000
echo [INFO] Enter custom port within 5 seconds, or press Enter to use default...

for /f "usebackq delims=" %%p in (`powershell -NoProfile -Command "$port=''; $sw=[System.Diagnostics.Stopwatch]::StartNew(); while($sw.ElapsedMilliseconds -lt 5000){ if([Console]::KeyAvailable){ $k=[Console]::ReadKey($false); if($k.Key -eq 'Enter'){break}else{$port+=$k.KeyChar} }else{ Start-Sleep -Milliseconds 100 } }; if($port -match '^\d+$' -and [int]$port -gt 0 -and [int]$port -lt 65536){$port}else{'8000'}"`) do set "PORT=%%p"

echo.
echo [INFO] Using port: %PORT%
echo.

set "SERVER_PORT=%PORT%"

REM === Install Dependencies ===
echo [INFO] Checking dependencies...
pip install -r requirements.txt -q 2>nul
echo [INFO] Dependencies OK.
echo.

REM === Start Server ===
echo [INFO] Starting server...
echo [INFO] API endpoint: http://localhost:%PORT%/v1/audio/speech
echo [INFO] Docs:         http://localhost:%PORT%/docs
echo [INFO] Press Ctrl+C to stop.
echo.

python main.py

pause
