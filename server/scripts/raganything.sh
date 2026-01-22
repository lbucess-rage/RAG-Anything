#!/bin/bash
# RAG-Anything Server Management Script (Combined)
# Manages both backend and frontend servers

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

show_banner() {
    echo "======================================"
    echo "  RAG-Anything Server Manager"
    echo "======================================"
    echo ""
}

start_all() {
    show_banner
    echo "Starting all servers..."
    echo ""
    "$SCRIPT_DIR/backend.sh" start
    echo ""
    "$SCRIPT_DIR/frontend.sh" start
    echo ""
    echo "======================================"
    echo "All servers started!"
    echo "  Backend:  http://0.0.0.0:15001"
    echo "  Frontend: http://0.0.0.0:19005"
    echo "======================================"
}

stop_all() {
    show_banner
    echo "Stopping all servers..."
    echo ""
    "$SCRIPT_DIR/frontend.sh" stop
    echo ""
    "$SCRIPT_DIR/backend.sh" stop
    echo ""
    echo "All servers stopped."
}

restart_all() {
    show_banner
    echo "Restarting all servers..."
    echo ""
    "$SCRIPT_DIR/backend.sh" restart
    echo ""
    "$SCRIPT_DIR/frontend.sh" restart
    echo ""
    echo "======================================"
    echo "All servers restarted!"
    echo "  Backend:  http://0.0.0.0:15001"
    echo "  Frontend: http://0.0.0.0:19005"
    echo "======================================"
}

status_all() {
    show_banner
    "$SCRIPT_DIR/backend.sh" status
    echo ""
    "$SCRIPT_DIR/frontend.sh" status
}

case "$1" in
    start)
        if [ -n "$2" ]; then
            "$SCRIPT_DIR/$2.sh" start
        else
            start_all
        fi
        ;;
    stop)
        if [ -n "$2" ]; then
            "$SCRIPT_DIR/$2.sh" stop
        else
            stop_all
        fi
        ;;
    restart)
        if [ -n "$2" ]; then
            "$SCRIPT_DIR/$2.sh" restart
        else
            restart_all
        fi
        ;;
    status)
        if [ -n "$2" ]; then
            "$SCRIPT_DIR/$2.sh" status
        else
            status_all
        fi
        ;;
    logs)
        if [ -n "$2" ]; then
            "$SCRIPT_DIR/$2.sh" logs
        else
            echo "Usage: $0 logs {backend|frontend}"
            exit 1
        fi
        ;;
    *)
        echo "RAG-Anything Server Manager"
        echo ""
        echo "Usage: $0 {start|stop|restart|status|logs} [backend|frontend]"
        echo ""
        echo "Examples:"
        echo "  $0 start              # Start all servers"
        echo "  $0 start backend      # Start backend only"
        echo "  $0 stop frontend      # Stop frontend only"
        echo "  $0 restart            # Restart all servers"
        echo "  $0 status             # Check status of all servers"
        echo "  $0 logs backend       # Tail backend logs"
        echo ""
        exit 1
        ;;
esac
