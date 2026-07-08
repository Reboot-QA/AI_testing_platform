#!/usr/bin/env bash
# 生成 jenkins/.env（首次部署必做）
#
# 用法:
#   cd /opt/AI_testing_platform/jenkins
#   bash init-env.sh

set -euo pipefail

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
ENV_FILE="$DIR/.env"
EXAMPLE="$DIR/.env.example"

generate_secret() {
  openssl rand -hex 12 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(12))'
}

[[ -f "$EXAMPLE" ]] || { echo "缺少 $EXAMPLE"; exit 1; }

if [[ -f "$ENV_FILE" ]]; then
  echo "[INFO] 已存在 $ENV_FILE，跳过"
  exit 0
fi

cp "$EXAMPLE" "$ENV_FILE"

pass="$(generate_secret)"
webhook="$(generate_secret)"
sed -i "s|^JENKINS_ADMIN_PASSWORD=.*|JENKINS_ADMIN_PASSWORD=${pass}|" "$ENV_FILE"
sed -i "s|^GITHUB_WEBHOOK_SECRET=.*|GITHUB_WEBHOOK_SECRET=${webhook}|" "$ENV_FILE"

if command -v getent >/dev/null 2>&1; then
  gid="$(getent group docker | cut -d: -f3 || echo 999)"
  if grep -q '^DOCKER_GID=' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^DOCKER_GID=.*|DOCKER_GID=${gid}|" "$ENV_FILE"
  else
    echo "DOCKER_GID=${gid}" >>"$ENV_FILE"
  fi
fi

host="$(curl -fsS --max-time 3 https://api.ipify.org 2>/dev/null | tr -d '[:space:]' || hostname -I 2>/dev/null | awk '{print $1}')"
[[ -n "$host" ]] || host="127.0.0.1"
sed -i "s|^JENKINS_URL=.*|JENKINS_URL=http://${host}:8080/|" "$ENV_FILE"

chmod 600 "$ENV_FILE" 2>/dev/null || true

echo "========================================"
echo "  已创建 $ENV_FILE"
echo "========================================"
echo "  用户名: admin"
echo "  密码:   ${pass}"
echo "  Webhook Secret: ${webhook}"
echo "========================================"
echo "下一步:"
echo "  docker compose --env-file .env up -d --build"
