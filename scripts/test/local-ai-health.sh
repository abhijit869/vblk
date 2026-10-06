#!/bin/bash
set -euo pipefail
echo "Testing Local AI Health..."
if ! systemctl is-active --quiet jarvis-local-ai.service; then
    echo "Service is not running."
    exit 1
fi

HTTP_STATUS=$(curl -s -o /dev/null -w "%{http_code}" http://127.0.0.1:8081/v1/models)
if [ "$HTTP_STATUS" -ne 200 ]; then
    echo "HTTP API is unhealthy (Status $HTTP_STATUS)"
    exit 1
fi

echo "Local AI Health: PASS"
