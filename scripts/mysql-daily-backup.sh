#!/usr/bin/env bash
# AI质量平台 - MySQL 每日自动备份（供 cron 调用）
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env.docker}"
BACKUP_DIR="/opt/ai-platform-backups/mysql"
BACKUP_KEEP_DAYS="30"

read_env() {
  local key="$1"
  local default="$2"
  if [[ -f "$ENV_FILE" ]]; then
    local line
    line="$(grep -E "^${key}=" "$ENV_FILE" | tail -1 || true)"
    if [[ -n "$line" ]]; then
      echo "${line#*=}"
      return 0
    fi
  fi
  echo "$default"
}

BACKUP_DIR="$(read_env BACKUP_DIR "$BACKUP_DIR")"
BACKUP_KEEP_DAYS="$(read_env BACKUP_KEEP_DAYS "$BACKUP_KEEP_DAYS")"
export BACKUP_DIR BACKUP_KEEP_DAYS ENV_FILE

mkdir -p "$BACKUP_DIR"

echo "[$(date '+%F %T')] 开始每日备份 -> $BACKUP_DIR"
"$ROOT/linux-deploy.sh" backup-db
"$ROOT/linux-deploy.sh" backup-prune
echo "[$(date '+%F %T')] 每日备份完成"
