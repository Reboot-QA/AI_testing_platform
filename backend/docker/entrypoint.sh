#!/bin/sh
set -e

mkdir -p /app/logs
touch /app/logs/backend.log

echo "[INFO] Waiting for MySQL at ${DB_HOST:-mysql}:${DB_PORT:-3306} ..."
python - <<'PY'
import os
import sys
import time

import pymysql

host = os.environ.get("DB_HOST", "mysql")
port = int(os.environ.get("DB_PORT", "3306"))
user = os.environ.get("DB_USER", "root")
password = os.environ.get("DB_PASSWORD", "")
database = os.environ.get("DB_NAME", "ai_testcase")

for attempt in range(1, 61):
    try:
        conn = pymysql.connect(
            host=host,
            port=port,
            user=user,
            password=password,
            database=database,
            charset="utf8mb4",
            connect_timeout=5,
        )
        conn.close()
        print("[OK] MySQL is ready")
        sys.exit(0)
    except Exception as exc:
        print(f"[INFO] MySQL not ready ({attempt}/60): {exc}")
        time.sleep(2)

print("[ERR] MySQL connection timed out", file=sys.stderr)
sys.exit(1)
PY

echo "[INFO] Starting backend on 0.0.0.0:8000 ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 2 2>&1 | tee -a /app/logs/backend.log
