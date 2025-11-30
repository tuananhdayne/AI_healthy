@echo off
echo ========================================
echo   KHOI DONG WEB CHATBOT
echo ========================================
echo.
echo [INFO] Script nay se khoi dong:
echo   1. Backend API (port 8000)
echo   2. Frontend Angular (port 4200)
echo.
echo [LUU Y] Can 2 terminal:
echo   - Terminal 1: Backend (models se mat 2-5 phut de load)
echo   - Terminal 2: Frontend
echo.
pause

echo.
echo ========================================
echo   KHOI DONG BACKEND (Terminal 1)
echo ========================================
echo.

REM Kiem tra Python
python --version >nul 2>&1
if errorlevel 1 (
    echo [ERROR] Python chua duoc cai dat
    pause
    exit /b 1
)

echo [INFO] Dang khoi dong Backend API...
echo [INFO] Models se mat 2-5 phut de load lan dau tien
echo [INFO] Doi den khi thay: "TAT CA MODELS DA SAN SANG!"
echo.

start "Backend API Server" cmd /k "cd /d %~dp0 && python -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload"

timeout /t 3 /nobreak >nul

echo.
echo ========================================
echo   KHOI DONG FRONTEND (Terminal 2)
echo ========================================
echo.

cd AI-Web

REM Kiem tra node_modules
if not exist "node_modules" (
    echo [WARNING] node_modules chua co, dang cai dat...
    call npm install
    if errorlevel 1 (
        echo [ERROR] Khong the cai dat dependencies
        pause
        exit /b 1
    )
)

echo [INFO] Dang khoi dong Frontend Angular...
echo [INFO] Frontend se chay tai: http://localhost:4200
echo.

start "Frontend Angular" cmd /k "cd /d %~dp0AI-Web && npm start"

echo.
echo ========================================
echo   DA KHOI DONG XONG!
echo ========================================
echo.
echo [INFO] Backend: http://localhost:8000
echo [INFO] Frontend: http://localhost:4200
echo.
echo [INFO] Doi Backend load models xong (2-5 phut)
echo [INFO] Sau do mo trinh duyet: http://localhost:4200
echo.
pause

