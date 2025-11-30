@echo off
echo ========================================
echo   KHOI DONG BACKEND API SERVER
echo ========================================
echo.

REM Kiem tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat hoac khong co trong PATH
    echo Vui long cai dat Python 3.8+ va thu lai
    pause
    exit /b 1
)

echo [1/3] Kiem tra Python...
python --version

echo.
echo [2/3] Kiem tra dependencies...
python -c "import fastapi" >nul 2>&1
if errorlevel 1 (
    echo [WARNING] FastAPI chua duoc cai dat
    echo Dang cai dat dependencies...
    pip install -r requirements.txt
    if errorlevel 1 (
        echo [ERROR] Khong the cai dat dependencies
        echo Dang thu cai dat thu cong...
        pip install fastapi uvicorn[standard] google-generativeai
        if errorlevel 1 (
            echo [ERROR] Khong the cai dat dependencies
            pause
            exit /b 1
        )
    )
) else (
    echo [OK] FastAPI da duoc cai dat
    echo [INFO] Kiem tra Gemini API library...
    python -c "import google.generativeai" >nul 2>&1
    if errorlevel 1 (
        echo [WARNING] google-generativeai chua duoc cai dat
        echo Dang cai dat...
        pip install google-generativeai
    )
)

echo.
echo [3/3] Khoi dong API server...
echo.
echo ========================================
echo   Server se chay tai: http://localhost:8000
echo   API docs: http://localhost:8000/docs
echo   Health check: http://localhost:8000/health
echo ========================================
echo.
echo [INFO] Models se mat vai phut de load lan dau tien
echo [INFO] Nhan Ctrl+C de dung server
echo.

python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload

pause

