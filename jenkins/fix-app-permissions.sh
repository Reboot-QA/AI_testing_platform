#!/usr/bin/env bash
# 修复 Jenkins 发版权限：让 jenkins 用户(UID 1000) 能 git pull + docker compose
#
# 用法:
#   sudo bash /opt/AI_testing_platform/jenkins/fix-app-permissions.sh

set -euo pipefail

APP_DIR="${APP_DIR:-/opt/AI_testing_platform}"
JENKINS_UID="${JENKINS_UID:-1000}"
JENKINS_GID="${JENKINS_GID:-1000}"

if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
  echo "请使用 root 或 sudo 执行"
  exit 1
fi

[[ -d "$APP_DIR" ]] || { echo "目录不存在: $APP_DIR"; exit 1; }

echo "[INFO] 将 ${APP_DIR} 所有者改为 ${JENKINS_UID}:${JENKINS_GID} ..."
chown -R "${JENKINS_UID}:${JENKINS_GID}" "$APP_DIR"

if [[ -f "$APP_DIR/.env.docker" ]]; then
  chmod 640 "$APP_DIR/.env.docker"
  echo "[ OK ] .env.docker 权限: 640"
fi

chmod +x "$APP_DIR/update.sh" "$APP_DIR/linux-deploy.sh" "$APP_DIR/deploy.sh" 2>/dev/null || true
chmod +x "$APP_DIR/jenkins/"*.sh "$APP_DIR/jenkins/scripts/"*.sh 2>/dev/null || true

# Git 信任（jenkins 容器内也会执行，宿主机先配无妨）
git config --system --add safe.directory "$APP_DIR" 2>/dev/null || true

echo "[ OK ] 完成。验证:"
ls -la "$APP_DIR/update.sh"
ls -ld "$APP_DIR/.git" 2>/dev/null || true

if docker ps --format '{{.Names}}' | grep -qx ai-platform-jenkins; then
  echo
  echo "[INFO] Jenkins 容器内验证:"
  docker exec -u jenkins ai-platform-jenkins test -w "$APP_DIR/.git" && echo "  .git 可写" || echo "  .git 仍不可写"
  docker exec -u jenkins ai-platform-jenkins test -f "$APP_DIR/update.sh" && echo "  update.sh 存在" || echo "  update.sh 不存在"
fi
