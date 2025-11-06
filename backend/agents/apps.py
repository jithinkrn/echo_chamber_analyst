"""
Django app configuration for agents.
"""

from django.apps import AppConfig


class AgentsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'agents'

    def ready(self):
        """
        Import tasks module when the app is ready.
        This ensures all Celery tasks are registered when Django starts.
        """
        try:
            # Import tasks to register them with Celery
            from . import tasks  # noqa: F401
        except ImportError:
            pass
