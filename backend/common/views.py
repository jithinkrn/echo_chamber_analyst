"""
Common views for health checks and system status.
"""

from django.http import JsonResponse
from django.db import connection
from django.conf import settings
import redis
import time


def health_check(request):
    """Basic health check endpoint."""
    return JsonResponse({
        'status': 'healthy',
        'timestamp': time.time(),
        'version': '1.0.0'
    })


def system_status(request):
    """Detailed system status including database and Redis connectivity."""
    status = {
        'status': 'healthy',
        'timestamp': time.time(),
        'services': {}
    }

    # Check database connectivity
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        status['services']['database'] = 'healthy'
    except Exception as e:
        status['services']['database'] = f'unhealthy: {str(e)}'
        status['status'] = 'degraded'

    # Check Redis connectivity
    try:
        r = redis.Redis.from_url(settings.REDIS_URL)
        r.ping()
        status['services']['redis'] = 'healthy'
    except Exception as e:
        status['services']['redis'] = f'unhealthy: {str(e)}'
        status['status'] = 'degraded'

    # Check Celery (if available)
    try:
        from celery import current_app
        inspect = current_app.control.inspect()
        stats = inspect.stats()
        if stats:
            status['services']['celery'] = 'healthy'
        else:
            status['services']['celery'] = 'no workers'
            status['status'] = 'degraded'
    except Exception as e:
        status['services']['celery'] = f'unhealthy: {str(e)}'

    return JsonResponse(status)