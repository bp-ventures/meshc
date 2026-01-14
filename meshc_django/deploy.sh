#!/bin/bash
# Deploy script for meshc Django app
#
# Usage: ./deploy.sh [--no-restart]
#
# Steps:
#   1. Stop existing gunicorn (if running)
#   2. Pull latest code (optional, if in git repo)
#   3. Install/update dependencies
#   4. Run database migrations
#   5. Collect static files
#   6. Start gunicorn
#
# Environment variables:
#   MESHC_PORT      - Gunicorn port (default: 10409)
#   MESHC_WORKERS   - Gunicorn workers (default: 2)
#   MESHC_PIDFILE   - PID file location (default: /tmp/meshc-gunicorn.pid)

set -e

# Configuration
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"
VENV_DIR="${PROJECT_ROOT}/.venv"
PYTHON="${VENV_DIR}/bin/python"
PIP="${VENV_DIR}/bin/pip"
GUNICORN="${VENV_DIR}/bin/gunicorn"

PORT="${MESHC_PORT:-10409}"
WORKERS="${MESHC_WORKERS:-2}"
PIDFILE="${MESHC_PIDFILE:-/tmp/meshc-gunicorn.pid}"

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

log_info() { echo -e "${GREEN}[INFO]${NC} $1"; }
log_warn() { echo -e "${YELLOW}[WARN]${NC} $1"; }
log_error() { echo -e "${RED}[ERROR]${NC} $1"; }

cd "$SCRIPT_DIR"

# -----------------------------------------------------------------------------
# 1. Stop existing gunicorn
# -----------------------------------------------------------------------------
stop_gunicorn() {
    log_info "Stopping gunicorn..."

    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        if kill -0 "$PID" 2>/dev/null; then
            kill -TERM "$PID"
            sleep 2
            # Force kill if still running
            if kill -0 "$PID" 2>/dev/null; then
                log_warn "Gunicorn didn't stop gracefully, forcing..."
                kill -9 "$PID" 2>/dev/null || true
            fi
            log_info "Gunicorn stopped (PID: $PID)"
        else
            log_warn "PID file exists but process not running"
        fi
        rm -f "$PIDFILE"
    else
        # Try to find by process name
        PIDS=$(pgrep -f "gunicorn.*meshc_django" || true)
        if [ -n "$PIDS" ]; then
            log_info "Found gunicorn processes: $PIDS"
            echo "$PIDS" | xargs kill -TERM 2>/dev/null || true
            sleep 2
        else
            log_info "No running gunicorn found"
        fi
    fi
}

# -----------------------------------------------------------------------------
# 2. Check Python/venv
# -----------------------------------------------------------------------------
check_venv() {
    if [ ! -f "$PYTHON" ]; then
        log_error "Virtual environment not found at $VENV_DIR"
        log_info "Create it with: cd $PROJECT_ROOT && uv venv"
        exit 1
    fi
    log_info "Using Python: $PYTHON"
}

# -----------------------------------------------------------------------------
# 3. Install dependencies
# -----------------------------------------------------------------------------
install_deps() {
    log_info "Installing dependencies..."
    cd "$PROJECT_ROOT"

    if command -v uv &> /dev/null; then
        uv pip install -e ".[django]"
    else
        "$PIP" install -e ".[django]"
    fi

    cd "$SCRIPT_DIR"
}

# -----------------------------------------------------------------------------
# 4. Run migrations
# -----------------------------------------------------------------------------
run_migrations() {
    log_info "Running database migrations..."
    "$PYTHON" manage.py migrate --no-input
}

# -----------------------------------------------------------------------------
# 5. Collect static files
# -----------------------------------------------------------------------------
collect_static() {
    log_info "Collecting static files..."
    "$PYTHON" manage.py collectstatic --no-input --clear 2>/dev/null || \
        "$PYTHON" manage.py collectstatic --no-input
}

# -----------------------------------------------------------------------------
# 6. Start gunicorn
# -----------------------------------------------------------------------------
start_gunicorn() {
    log_info "Starting gunicorn on port $PORT with $WORKERS workers..."

    # Ensure logs directory exists
    mkdir -p logs

    # Start gunicorn in background
    "$GUNICORN" \
        --bind "0.0.0.0:${PORT}" \
        --workers "$WORKERS" \
        --pid "$PIDFILE" \
        --access-logfile logs/access.log \
        --error-logfile logs/error.log \
        --capture-output \
        --daemon \
        meshc_django.wsgi:application

    sleep 1

    if [ -f "$PIDFILE" ]; then
        PID=$(cat "$PIDFILE")
        log_info "Gunicorn started (PID: $PID)"
        log_info "Access: http://localhost:${PORT}/meshc/"
        log_info "Admin:  http://localhost:${PORT}/admin/"
        log_info "Logs:   $SCRIPT_DIR/logs/"
    else
        log_error "Failed to start gunicorn"
        exit 1
    fi
}

# -----------------------------------------------------------------------------
# Main
# -----------------------------------------------------------------------------
main() {
    log_info "=== meshc Django Deploy ==="
    log_info "Project: $PROJECT_ROOT"
    log_info "Django:  $SCRIPT_DIR"
    echo ""

    stop_gunicorn
    check_venv

    if [ "$1" != "--no-restart" ]; then
        install_deps
        run_migrations
        collect_static
        start_gunicorn

        echo ""
        log_info "=== Deploy complete ==="
    else
        log_info "Gunicorn stopped (--no-restart specified)"
    fi
}

main "$@"
