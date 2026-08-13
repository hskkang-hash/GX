#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
    from celery import current_app
    
    print('=== CELERY TASKS ===')
    
    # Check periodic tasks
    periodic_tasks = PeriodicTask.objects.all()
    print(f'Found {periodic_tasks.count()} periodic tasks:')
    
    for task in periodic_tasks:
        print(f'- {task.name}: {task.task} (Enabled: {task.enabled})')
        if task.interval:
            print(f'  Interval: {task.interval.every} {task.interval.period}')
        elif task.crontab:
            print(f'  Crontab: {task.crontab}')
        print(f'  Last run: {task.last_run_at}')
        print(f'  Total runs: {task.total_run_count}')
        print()
    
    # Check registered tasks
    print('=== REGISTERED TASKS ===')
    registered_tasks = current_app.tasks.keys()
    drone_related_tasks = [task for task in registered_tasks if 'drone' in task.lower()]
    
    print(f'Found {len(drone_related_tasks)} drone-related tasks:')
    for task in drone_related_tasks:
        print(f'- {task}')
        
except ImportError:
    print('django_celery_beat not available')
except Exception as e:
    print(f'Error checking Celery tasks: {e}')
