#!/usr/bin/env python3
"""
Script để monitor database connections trong PostgreSQL
Sử dụng: python monitor_db_connections.py
"""

import os
import sys
import django
import psycopg2
from datetime import datetime

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

from django.conf import settings

def get_db_connections():
    """Lấy thông tin về database connections"""
    try:
        # Kết nối trực tiếp đến PostgreSQL
        conn = psycopg2.connect(
            host=settings.DATABASES['default']['HOST'],
            port=settings.DATABASES['default']['PORT'],
            database=settings.DATABASES['default']['NAME'],
            user=settings.DATABASES['default']['USER'],
            password=settings.DATABASES['default']['PASSWORD']
        )
        
        cursor = conn.cursor()
        
        # Query để lấy thông tin connections
        cursor.execute("""
            SELECT 
                datname as database,
                usename as username,
                application_name,
                client_addr,
                state,
                query_start,
                state_change,
                query
            FROM pg_stat_activity 
            WHERE datname = %s
            ORDER BY query_start DESC
        """, (settings.DATABASES['default']['NAME'],))
        
        connections = cursor.fetchall()
        
        # Đếm số connections theo trạng thái
        cursor.execute("""
            SELECT 
                state,
                COUNT(*) as count
            FROM pg_stat_activity 
            WHERE datname = %s
            GROUP BY state
        """, (settings.DATABASES['default']['NAME'],))
        
        state_counts = dict(cursor.fetchall())
        
        # Lấy thông tin về max connections
        cursor.execute("SHOW max_connections")
        max_connections = cursor.fetchone()[0]
        
        cursor.close()
        conn.close()
        
        return {
            'connections': connections,
            'state_counts': state_counts,
            'max_connections': max_connections,
            'total_connections': len(connections)
        }
        
    except Exception as e:
        print(f"Lỗi khi kết nối database: {e}")
        return None

def print_connection_info():
    """In thông tin connections"""
    info = get_db_connections()
    
    if not info:
        return
    
    print(f"\n{'='*80}")
    print(f"DATABASE CONNECTION MONITOR - {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*80}")
    
    print(f"\n📊 TỔNG QUAN:")
    print(f"   Tổng connections: {info['total_connections']}")
    print(f"   Max connections: {info['max_connections']}")
    print(f"   Usage: {info['total_connections']}/{info['max_connections']} ({(info['total_connections']/int(info['max_connections'])*100):.1f}%)")
    
    print(f"\n📈 THEO TRẠNG THÁI:")
    for state, count in info['state_counts'].items():
        state_name = state if state else 'idle'
        print(f"   {state_name}: {count}")
    
    print(f"\n🔍 CHI TIẾT CONNECTIONS:")
    print(f"{'Database':<15} {'User':<15} {'Application':<20} {'State':<10} {'Client':<15} {'Query Start':<20}")
    print("-" * 100)
    
    for conn in info['connections'][:10]:  # Chỉ hiển thị 10 connections đầu
        database, username, app_name, client_addr, state, query_start, state_change, query = conn
        
        app_name = app_name[:18] + ".." if app_name and len(app_name) > 20 else app_name or "N/A"
        state = state or "idle"
        client_addr = str(client_addr) if client_addr else "N/A"
        query_start = query_start.strftime('%H:%M:%S') if query_start else "N/A"
        
        print(f"{database:<15} {username:<15} {app_name:<20} {state:<10} {client_addr:<15} {query_start:<20}")
    
    if len(info['connections']) > 10:
        print(f"... và {len(info['connections']) - 10} connections khác")

def main():
    """Main function"""
    try:
        print_connection_info()
    except KeyboardInterrupt:
        print("\n\n👋 Đã dừng monitoring")
        sys.exit(0)

if __name__ == "__main__":
    main()
