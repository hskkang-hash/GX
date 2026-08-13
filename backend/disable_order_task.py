#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from django_celery_beat.models import PeriodicTask
    
    print('=== DISABLING ORDER STATUS TASK ===')
    
    # Find the order status task
    order_task = PeriodicTask.objects.filter(
        task='orders.tasks.check_order_statuses'
    ).first()
    
    if order_task:
        print(f'Found task: {order_task.name}')
        print(f'Current status: Enabled = {order_task.enabled}')
        print(f'Total runs: {order_task.total_run_count}')
        print(f'Last run: {order_task.last_run_at}')
        
        if order_task.enabled:
            order_task.enabled = False
            order_task.save()
            print('✅ Successfully disabled order status task')
        else:
            print('Task is already disabled')
    else:
        print('❌ Order status task not found')
        
    # Show all tasks
    print('\n=== ALL PERIODIC TASKS ===')
    all_tasks = PeriodicTask.objects.all()
    for task in all_tasks:
        print(f'- {task.name}: {task.task} (Enabled: {task.enabled})')
        
except Exception as e:
    print(f'Error: {e}')