"""
Celery configuration for EchoChamber Analyst.
"""

import os
from celery import Celery

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Construct DATABASE_URL from individual components if not already set
# This is needed for ECS where env vars are set individually
# if not os.getenv('DATABASE_URL'):
#     db_user = os.getenv('DB_USER', 'echochamber')
#     db_password = os.getenv('DB_PASSWORD', '')
#     db_host = os.getenv('DB_HOST', 'localhost')
#     db_port = os.getenv('DB_PORT', '5432')
#     db_name = os.getenv('DB_NAME', 'echochamber')
#     os.environ['DATABASE_URL'] = f'postgresql://{db_user}:{db_password}@{db_host}:{db_port}/{db_name}'

# Setup Django before importing anything that might touch models
import django
django.setup()

from django.conf import settings

app = Celery('echochamber')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Explicitly import agents tasks to ensure they're registered
try:
    from agents import tasks as agents_tasks
    task_count = len([x for x in dir(agents_tasks) if not x.startswith('_')])
    print(f"✅ Successfully loaded agents.tasks module with {task_count} items")

    # Debug: List all registered Celery tasks after import
    import time
    time.sleep(1)  # Give Celery a moment to register tasks
    print(f"📋 Registered Celery tasks: {sorted([name for name in app.tasks.keys() if not name.startswith('celery.')])}")
except ImportError as e:
    print(f"❌ Failed to import agents.tasks: {e}")
    import traceback
    traceback.print_exc()
except Exception as e:
    print(f"❌ Unexpected error loading agents.tasks: {e}")
    import traceback
    traceback.print_exc()

# Configure Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'check-scheduled-campaigns': {
        'task': 'agents.tasks.check_and_execute_scheduled_campaigns',
        'schedule': 60.0,  # Run every minute to check for campaigns that need execution
    },
    'update-dashboard-metrics': {
        'task': 'agents.tasks.update_dashboard_metrics_task',
        'schedule': 300.0,  # Run every 5 minutes to keep dashboard fresh
    },
    'cleanup-old-data': {
        'task': 'agents.tasks.cleanup_old_data_task',
        'schedule': 86400.0,  # Run daily
    },
    'generate-daily-insights': {
        'task': 'agents.tasks.generate_daily_insights_task',
        'schedule': 86400.0,  # Run daily
    },
    'check-complete-campaigns': {
        'task': 'check_and_complete_campaigns',
        'schedule': 600.0,  # Run every 10 minutes
    },
}

app.conf.timezone = 'UTC'

@app.task(bind=True)
def debug_task(self):
    print(f'Request: {self.request!r}')