#!/bin/sh
set -e

mkdir -p /var/log/ai-platform
touch /var/log/ai-platform/frontend.log /var/log/ai-platform/frontend.error.log 2>/dev/null || true

exec "$@"
