"""Gunicorn configuration for meshc_django.

Usage:
    gunicorn -c gunicorn.conf.py meshc_django.wsgi:application

Or with defaults:
    gunicorn meshc_django.wsgi:application
"""
import os

# Server socket
bind = os.environ.get('GUNICORN_BIND', '0.0.0.0:10409')

# Worker processes
workers = int(os.environ.get('GUNICORN_WORKERS', '2'))
worker_class = 'sync'
timeout = 30

# Logging
accesslog = '-'  # stdout
errorlog = '-'   # stderr
loglevel = os.environ.get('GUNICORN_LOG_LEVEL', 'info')

# Process naming
proc_name = 'meshc-django'

# Security
limit_request_line = 4094
limit_request_fields = 100
