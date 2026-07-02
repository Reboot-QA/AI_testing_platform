#!/bin/sh
set -e

cd /app
mkdir -p /app/logs

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
        err = str(exc)
        print(f"[INFO] MySQL not ready ({attempt}/60): {exc}")
        if "1045" in err or "Access denied" in err:
            print(
                "[ERR] MySQL 账号或密码错误，.env.docker 中 DB_PASSWORD 与数据库不一致。",
                file=sys.stderr,
            )
            print(
                "[ERR] 修复: RESET_MYSQL=1 ./linux-deploy.sh up  （会清空数据库）",
                file=sys.stderr,
            )
            sys.exit(1)
        time.sleep(2)

print("[ERR] MySQL connection timed out", file=sys.stderr)
sys.exit(1)
PY

echo "[INFO] Starting backend on 0.0.0.0:8000 ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
