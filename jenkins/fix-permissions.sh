#!/usr/bin/env bash
# 修复 Jenkins 数据卷权限（Permission denied on /var/jenkins_home）
#
# 原因：数据卷曾被 root 创建，Jenkins 容器内 jenkins 用户(UID 1000) 无法写入
#
# 用法:
#   sudo bash jenkins/fix-permissions.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
COMPOSE_FILE="$ROOT/jenkins/docker-compose.yml"
ENV_FILE="$ROOT/jenkins/.env"
VOLUME_NAME="jenkins_jenkins-data"

if [[ ! -f "$ENV_FILE" ]]; then
  echo "[WARN] 缺少 $ENV_FILE，请先: cp jenkins/.env.example jenkins/.env"
  exit 1
fi

echo "[INFO] 停止 Jenkins 容器..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down 2>/dev/null || true

echo "[INFO] 修复数据卷权限 -> 1000:1000 (jenkins)..."
docker volume create "$VOLUME_NAME" >/dev/null 2>&1 || true
docker run --rm \
  -v "${VOLUME_NAME}:/var/jenkins_home" \
  busybox chown -R 1000:1000 /var/jenkins_home

if command -v getent >/dev/null 2>&1; then
  export DOCKER_GID="$(getent group docker | cut -d: -f3 || echo 999)"
else
  export DOCKER_GID="${DOCKER_GID:-999}"
fi

echo "[INFO] 重新启动 Jenkins..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d

echo "[ OK ] 完成。查看日志: docker logs -f ai-platform-jenkins"
