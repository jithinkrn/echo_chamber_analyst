"""
Celery configuration for EchoChamber Analyst.
"""

import os
from celery import Celery
from django.conf import settings

# Set the default Django settings module for the 'celery' program.
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

app = Celery('echochamber')

# Using a string here means the worker doesn't have to serialize
# the configuration object to child processes.
app.config_from_object('django.conf:settings', namespace='CELERY')

# Load task modules from all registered Django apps.
app.autodiscover_tasks()

# Configure Celery Beat Schedule for periodic tasks
app.conf.beat_schedule = {
    'scout-reddit-hourly': {
        'task': 'agents.tasks.scout_reddit_task',
        'schedule': 3600.0,  # Run every hour
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