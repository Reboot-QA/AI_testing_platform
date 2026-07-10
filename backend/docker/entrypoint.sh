#!/bin/sh
set -e

cd /app
mkdir -p /app/logs
touch /app/logs/backend.log /app/logs/ensure.log 2>/dev/null || true

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
        if "1045" in err or "Access denied" in err:
            print(
                "[ERR] MySQL 账号或密码错误，.env.docker 中 DB_PASSWORD 与已有数据卷不一致。",
                file=sys.stderr,
            )
            print(
                "[ERR] 修复: ./linux-deploy.sh fix-db  （会清空数据库后按 .env.docker 重建）",
                file=sys.stderr,
            )
            # 避免 exit 触发 restart 策略导致日志刷屏
            while True:
                time.sleep(86400)
        if "1049" in err or "Unknown database" in err:
            print(
                "[ERR] 数据库不存在（Unknown database）。应用不会自动删库，常见原因：",
                file=sys.stderr,
            )
            print(
                "[ERR]   1) 执行过 fix-db / RESET_MYSQL=1 / docker compose down -v 清空数据卷",
                file=sys.stderr,
            )
            print(
                "[ERR]   2) 数据卷仍在但库被手动 DROP，MySQL 不会自动重建（仅首次空卷初始化）",
                file=sys.stderr,
            )
            print(
                "[ERR] 修复: 在 MySQL 容器内 CREATE DATABASE，或 ./linux-deploy.sh fix-db 重建",
                file=sys.stderr,
            )
            while True:
                time.sleep(86400)
        print(f"[INFO] MySQL not ready ({attempt}/60): {exc}")
        time.sleep(2)

print("[ERR] MySQL connection timed out", file=sys.stderr)
sys.exit(1)
PY

echo "[INFO] Running database bootstrap..."
python - <<'PY'
import logging
import sys

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s",
)

try:
    from app.bootstrap import run_bootstrap

    run_bootstrap()
except Exception:
    logging.getLogger(__name__).exception("数据库初始化失败")
    sys.exit(1)
PY

export APP_BOOTSTRAP_DONE=1

echo "[INFO] Starting backend on 0.0.0.0:8000 ..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 1 --log-level info
