#!/bin/bash

echo "🔄 RESTARTING GUARDIANX BACKEND..."
echo "=================================="

# Bước 1: Dừng tất cả processes
echo "1. Dừng tất cả backend processes..."
pkill -f gunicorn
pkill -f uvicorn
pkill -f "python manage.py runserver"

# Đợi processes dừng hoàn toàn
sleep 5

# Kiểm tra xem còn processes nào không
if pgrep -f "gunicorn\|uvicorn\|runserver" > /dev/null; then
    echo "⚠️  Vẫn còn processes đang chạy, force kill..."
    pkill -9 -f gunicorn
    pkill -9 -f uvicorn
    pkill -9 -f "python manage.py runserver"
    sleep 3
fi

echo "✅ Đã dừng tất cả processes"

# Bước 2: Đợi database connections được giải phóng
echo "2. Đợi database connections được giải phóng..."
sleep 30

# Bước 3: Chạy script khẩn cấp để fix database
echo "3. Chạy database connection fix..."
python emergency_db_fix.py

# Bước 4: Khởi động lại backend
echo "4. Khởi động lại backend..."
echo "   Chọn phương thức khởi động:"
echo "   1. Docker Compose (recommended)"
echo "   2. Development server"
echo "   3. Gunicorn trực tiếp"
read -p "Nhập lựa chọn (1-3): " choice

case $choice in
    1)
        echo "🚀 Khởi động với Docker Compose..."
        docker-compose up -d backend
        ;;
    2)
        echo "🚀 Khởi động development server..."
        python manage.py runserver 0.0.0.0:8000
        ;;
    3)
        echo "🚀 Khởi động với Gunicorn..."
        gunicorn -c gunicorn.conf.py config.asgi:application
        ;;
    *)
        echo "❌ Lựa chọn không hợp lệ"
        exit 1
        ;;
esac

echo "✅ Backend đã được restart thành công!"
echo "📊 Kiểm tra trạng thái:"
echo "   - Logs: docker-compose logs -f backend"
echo "   - Health check: curl http://localhost:8000/api/health"
echo "   - Database connections: python monitor_db_connections.py"
