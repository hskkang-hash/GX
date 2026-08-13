# Background optimization tasks

# Import tasks to ensure they're auto-discovered by Celery
from .aggregation_tasks import *
from .cache_warming_tasks import *
