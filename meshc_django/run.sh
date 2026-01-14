#!/bin/bash
# Run meshc Django app with gunicorn
# Usage: ./run.sh [port]
#
# Default port: 10409

set -e

cd "$(dirname "$0")"

PORT="${1:-10409}"

# Ensure logs directory exists
mkdir -p logs

# Run gunicorn
exec gunicorn \
    --bind "0.0.0.0:${PORT}" \
    --workers 2 \
    --access-logfile - \
    --error-logfile - \
    meshc_django.wsgi:application
