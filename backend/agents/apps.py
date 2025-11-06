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
        import logging
        logger = logging.getLogger(__name__)

        try:
            # Import tasks to register them with Celery
            from . import tasks  # noqa: F401
            logger.info(f"✅ Successfully imported agents.tasks module - {len(dir(tasks))} items found")
        except ImportError as e:
            logger.error(f"❌ Failed to import agents.tasks: {e}")
            raise
        except Exception as e:
            logger.error(f"❌ Unexpected error importing agents.tasks: {e}")
            raise
