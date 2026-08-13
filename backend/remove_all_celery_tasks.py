#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from django_celery_beat.models import PeriodicTask, IntervalSchedule, CrontabSchedule
    
    print('=== CLEARING ALL CELERY TASKS ===')
    
    # Get all periodic tasks
    all_tasks = PeriodicTask.objects.all()
    print(f'Found {all_tasks.count()} periodic tasks:')
    
    # Show tasks before deletion
    for task in all_tasks:
        print(f'- {task.name}: {task.task} (Enabled: {task.enabled})')
        if task.interval:
            print(f'  Interval: {task.interval.every} {task.interval.period}')
        elif task.crontab:
            print(f'  Crontab: {task.crontab}')
        print(f'  Total runs: {task.total_run_count}')
        print()
    
    # Confirm deletion
    print('⚠️  WARNING: This will delete ALL periodic tasks!')
    confirm = input('Type "YES" to confirm deletion: ')
    
    if confirm == "YES":
        # Delete all tasks
        deleted_count = all_tasks.count()
        all_tasks.delete()
        print(f'✅ Successfully deleted {deleted_count} periodic tasks')
        
        # Also clean up unused schedules
        print('\n=== CLEANING UP UNUSED SCHEDULES ===')
        
        # Delete unused interval schedules
        unused_intervals = IntervalSchedule.objects.filter(periodictask__isnull=True)
        interval_count = unused_intervals.count()
        unused_intervals.delete()
        print(f'✅ Deleted {interval_count} unused interval schedules')
        
        # Delete unused crontab schedules
        unused_crontabs = CrontabSchedule.objects.filter(periodictask__isnull=True)
        crontab_count = unused_crontabs.count()
        unused_crontabs.delete()
        print(f'✅ Deleted {crontab_count} unused crontab schedules')
        
        print('\n✅ All Celery tasks and unused schedules have been cleared!')
        
    else:
        print('❌ Deletion cancelled')
        
    # Show remaining tasks (should be 0)
    print('\n=== REMAINING TASKS ===')
    remaining_tasks = PeriodicTask.objects.all()
    print(f'Remaining tasks: {remaining_tasks.count()}')
    
except Exception as e:
    print(f'Error: {e}')
