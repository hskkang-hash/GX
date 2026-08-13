#!/usr/bin/env python
import os
import sys
import django

# Setup Django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')
django.setup()

try:
    from django_celery_beat.models import PeriodicTask
    
    print('=== DISABLING DRONE STATE TASK ===')
    
    # Find the drone state task
    drone_task = PeriodicTask.objects.filter(
        task='delivery.tasks.check_all_drones_state'
    ).first()
    
    if drone_task:
        print(f'Found task: {drone_task.name}')
        print(f'Current status: Enabled = {drone_task.enabled}')
        
        if drone_task.enabled:
            drone_task.enabled = False
            drone_task.save()
            print('✅ Successfully disabled drone state task')
        else:
            print('Task is already disabled')
    else:
        print('❌ Drone state task not found')
        
    # Show all tasks
    print('\n=== ALL PERIODIC TASKS ===')
    all_tasks = PeriodicTask.objects.all()
    for task in all_tasks:
        print(f'- {task.name}: {task.task} (Enabled: {task.enabled})')
        
except Exception as e:
    print(f'Error: {e}')
