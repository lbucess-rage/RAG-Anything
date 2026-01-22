#!/bin/bash
# RAG-Anything Backend Server Management Script
# Service Name: raganything-backend

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$(dirname "$SCRIPT_DIR")")"
BACKEND_DIR="$PROJECT_ROOT/server/backend"
PID_FILE="$BACKEND_DIR/.raganything-backend.pid"
LOG_FILE="$BACKEND_DIR/logs/backend.log"
SERVICE_NAME="raganything-backend"

# Server configuration
HOST="0.0.0.0"
PORT="15001"

# Ensure log directory exists
mkdir -p "$(dirname "$LOG_FILE")"

get_pid() {
    if [ -f "$PID_FILE" ]; then
        cat "$PID_FILE"
    fi
}

is_running() {
    local pid=$(get_pid)
    if [ -n "$pid" ] && kill -0 "$pid" 2>/dev/null; then
        return 0
    fi
    return 1
}

start() {
    if is_running; then
        echo "[$SERVICE_NAME] Already running (PID: $(get_pid))"
        return 1
    fi

    echo "[$SERVICE_NAME] Starting on $HOST:$PORT..."

    cd "$BACKEND_DIR"

    # Add .venv/bin to PATH for MinerU commands
    export PATH="$PROJECT_ROOT/.venv/bin:$PATH"

    # Start server in background with nohup
    nohup python -m uvicorn app.main:app \
        --host "$HOST" \
        --port "$PORT" \
        >> "$LOG_FILE" 2>&1 &

    local pid=$!
    echo $pid > "$PID_FILE"

    # Wait a moment and check if it started
    sleep 2
    if is_running; then
        echo "[$SERVICE_NAME] Started successfully (PID: $pid)"
        echo "[$SERVICE_NAME] Logs: $LOG_FILE"
        return 0
    else
        echo "[$SERVICE_NAME] Failed to start. Check logs: $LOG_FILE"
        rm -f "$PID_FILE"
        return 1
    fi
}

stop() {
    if ! is_running; then
        echo "[$SERVICE_NAME] Not running"
        rm -f "$PID_FILE"
        return 0
    fi

    local pid=$(get_pid)
    echo "[$SERVICE_NAME] Stopping (PID: $pid)..."

    kill "$pid" 2>/dev/null

    # Wait for graceful shutdown
    local count=0
    while is_running && [ $count -lt 10 ]; do
        sleep 1
        count=$((count + 1))
    done

    if is_running; then
        echo "[$SERVICE_NAME] Force killing..."
        kill -9 "$pid" 2>/dev/null
    fi

    rm -f "$PID_FILE"
    echo "[$SERVICE_NAME] Stopped"
}

restart() {
    echo "[$SERVICE_NAME] Restarting..."
    stop
    sleep 1
    start
}

status() {
    if is_running; then
        echo "[$SERVICE_NAME] Running (PID: $(get_pid))"
        echo "[$SERVICE_NAME] URL: http://$HOST:$PORT"
    else
        echo "[$SERVICE_NAME] Not running"
    fi
}

logs() {
    if [ -f "$LOG_FILE" ]; then
        tail -f "$LOG_FILE"
    else
        echo "[$SERVICE_NAME] No log file found"
    fi
}

case "$1" in
    start)
        start
        ;;
    stop)
        stop
        ;;
    restart)
        restart
        ;;
    status)
        status
        ;;
    logs)
        logs
        ;;
    *)
        echo "Usage: $0 {start|stop|restart|status|logs}"
        exit 1
        ;;
esac
