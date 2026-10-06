#!/bin/bash
set -euo pipefail

if [ $# -ne 1 ]; then
    echo "Usage: $0 {start|stop|restart|status}"
    exit 1
fi

ACTION="$1"

case "$ACTION" in
    start)
        systemctl start jarvis-local-ai.service
        ;;
    stop)
        systemctl stop jarvis-local-ai.service
        ;;
    restart)
        systemctl restart jarvis-local-ai.service
        ;;
    status)
        systemctl status jarvis-local-ai.service || exit $?
        ;;
    *)
        echo "Invalid action: $ACTION"
        exit 1
        ;;
esac
