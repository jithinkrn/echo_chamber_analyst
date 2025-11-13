"""
Integration tests package.
"""
import os

# Setup Django before importing anything else
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

# Setup Django
import django
try:
    django.setup()
except RuntimeError:
    # Django already configured
    pass
