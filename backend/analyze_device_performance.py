#!/usr/bin/env python
"""
Script để đo hiệu suất của API devices-management.

Cách sử dụng:
    python analyze_device_performance.py [--page-size=<size>] [--current-page=<page>]

Options:
    --page-size=<size>     Kích thước trang (mặc định: 25)
    --current-page=<page>  Trang hiện tại (mặc định: 1)
    --full                 Phân tích đầy đủ tất cả các truy vấn
    --help                 Hiển thị thông báo trợ giúp này
"""

import os
import sys
import time
import django
from django.conf import settings
from django.core.wsgi import get_wsgi_application

# Thiết lập môi trường Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'core.settings')
django.setup()

from django.test.client import RequestFactory
from django.db import connection, reset_queries
from devices.views.device_views import DeviceAPI

def parse_args():
    """Parse command line arguments."""
    args = {
        'page_size': 25,
        'current_page': 1,
        'full': False,
        'help': False,
    }
    
    for arg in sys.argv[1:]:
        if arg == '--help':
            args['help'] = True
        elif arg == '--full':
            args['full'] = True
        elif arg.startswith('--page-size='):
            args['page_size'] = int(arg.split('=')[1])
        elif arg.startswith('--current-page='):
            args['current_page'] = int(arg.split('=')[1])
    
    return args

def print_help():
    """Print help message."""
    print(__doc__)

def run_performance_analysis(page_size=25, current_page=1, full_analysis=False):
    """
    Chạy phân tích hiệu suất cho API list_devices.
    
    Args:
        page_size: Kích thước trang
        current_page: Trang hiện tại
        full_analysis: Nếu True, phân tích đầy đủ tất cả các truy vấn
    """
    print(f"\n{'=' * 80}")
    print(f"BẮT ĐẦU PHÂN TÍCH HIỆU SUẤT CHO API DEVICES-MANAGEMENT")
    print(f"{'=' * 80}")
    print(f"Kích thước trang: {page_size}")
    print(f"Trang hiện tại: {current_page}")
    
    # Tạo request giả lập
    factory = RequestFactory()
    request = factory.get(f'/api/devices-management?page_size={page_size}&current_page={current_page}')
    
    # Thiết lập API
    api = DeviceAPI()
    
    # Giả lập context
    class Context:
        pass
    
    context = Context()
    context.request = request
    api.context = context
    
    # Bật DEBUG để ghi nhận các truy vấn
    old_debug = settings.DEBUG
    settings.DEBUG = True
    reset_queries()
    
    # Chạy API và đo thời gian
    start_time = time.time()
    
    try:
        response = api.list_devices()
        execution_time = time.time() - start_time
        
        # Phân tích kết quả
        print(f"\nTổng thời gian thực thi: {execution_time:.4f} giây")
        
        queries = connection.queries
        query_count = len(queries)
        print(f"Tổng số truy vấn SQL: {query_count}")
        
        if query_count > 0:
            total_sql_time = sum(float(q['time']) for q in queries)
            print(f"Tổng thời gian SQL: {total_sql_time:.4f} giây ({total_sql_time/execution_time*100:.1f}% tổng thời gian)")
            
            if full_analysis:
                print(f"\n{'=' * 80}")
                print(f"CHI TIẾT CÁC TRUY VẤN SQL")
                print(f"{'=' * 80}")
                
                # Hiển thị tất cả các truy vấn
                for i, query in enumerate(queries):
                    print(f"\n{i+1}. Thời gian: {float(query['time']):.4f}s")
                    print(f"   SQL: {query['sql']}")
            else:
                # Chỉ hiển thị các truy vấn chậm
                slow_queries = [(i, q) for i, q in enumerate(queries) if float(q['time']) > 0.01]
                if slow_queries:
                    print(f"\nCác truy vấn chậm (>10ms): {len(slow_queries)}")
                    for i, query in slow_queries:
                        print(f"\n{i+1}. Thời gian: {float(query['time']):.4f}s")
                        print(f"   SQL: {query['sql'][:150]}...")
        
        # Phân tích response
        if hasattr(response, 'data'):
            data = response.data
            total_items = getattr(response, 'total_items', 0)
            total_pages = getattr(response, 'total_pages', 0)
            print(f"\nKết quả API:")
            print(f"Số bản ghi trong trang: {len(data) if isinstance(data, list) else 'N/A'}")
            print(f"Tổng số bản ghi: {total_items}")
            print(f"Tổng số trang: {total_pages}")
        
    except Exception as e:
        print(f"Lỗi khi chạy API: {str(e)}")
    
    # Khôi phục trạng thái DEBUG
    settings.DEBUG = old_debug
    
    print(f"\n{'=' * 80}")
    print(f"KẾT THÚC PHÂN TÍCH HIỆU SUẤT")
    print(f"{'=' * 80}")

if __name__ == '__main__':
    args = parse_args()
    
    if args['help']:
        print_help()
        sys.exit(0)
    
    run_performance_analysis(
        page_size=args['page_size'],
        current_page=args['current_page'],
        full_analysis=args['full']
    ) 