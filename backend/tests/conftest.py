"""
Pytest configuration for all tests.

This file disables LangSmith tracing during tests to prevent
connection warnings and errors.
"""
import os
import warnings

# Disable LangSmith tracing for all tests
os.environ['LANGCHAIN_TRACING_V2'] = 'false'
os.environ['LANGCHAIN_API_KEY'] = ''

# Suppress LangSmith warnings
warnings.filterwarnings('ignore', category=RuntimeWarning, message='.*cannot schedule new futures.*')
warnings.filterwarnings('ignore', module='langsmith')
