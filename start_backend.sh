#!/bin/bash

echo "========================================"
echo "  KHOI DONG BACKEND API SERVER"
echo "========================================"
echo ""

# Kiểm tra Python
if ! command -v python3 &> /dev/null; then
    echo "[ERROR] Python3 chưa được cài đặt"
    echo "Vui lòng cài đặt Python 3.8+ và thử lại"
    exit 1
fi

echo "[1/3] Kiểm tra Python..."
python3 --version

echo ""
echo "[2/3] Kiểm tra dependencies..."
if ! python3 -c "import fastapi" 2>/dev/null; then
    echo "[WARNING] FastAPI chưa được cài đặt"
    echo "Đang cài đặt FastAPI và Uvicorn..."
    pip3 install fastapi uvicorn[standard]
    if [ $? -ne 0 ]; then
        echo "[ERROR] Không thể cài đặt dependencies"
        exit 1
    fi
else
    echo "[OK] FastAPI đã được cài đặt"
fi

echo ""
echo "[3/3] Khởi động API server..."
echo ""
echo "========================================"
echo "  Server sẽ chạy tại: http://localhost:8000"
echo "  API docs: http://localhost:8000/docs"
echo "  Health check: http://localhost:8000/health"
echo "========================================"
echo ""
echo "[INFO] Models sẽ mất vài phút để load lần đầu tiên"
echo "[INFO] Nhấn Ctrl+C để dừng server"
echo ""

python3 -m uvicorn api_server:app --host 0.0.0.0 --port 8000 --reload

