#!/usr/bin/env bash
# 为已安装的 Jenkins 启用登录认证（JCasC 本地账号）
#
# 用法:
#   cd /opt/AI_testing_platform/jenkins
#   cp .env.example .env && vi .env   # 修改 JENKINS_ADMIN_PASSWORD
#   sudo bash enable-auth.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JENKINS_DIR="$ROOT/jenkins"
ENV_FILE="$JENKINS_DIR/.env"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERR ]${NC} $*" >&2; exit 1; }

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 12
  else
    python3 -c 'import secrets; print(secrets.token_hex(12))'
  fi
}

read_env() {
  grep -E "^${1}=" "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true
}

set_env() {
  local key="$1" val="$2"
  if grep -q "^${key}=" "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^${key}=.*|${key}=${val}|" "$ENV_FILE"
  else
    echo "${key}=${val}" >>"$ENV_FILE"
  fi
}

[[ -f "$JENKINS_DIR/docker-compose.yml" ]] || error "缺少 $JENKINS_DIR/docker-compose.yml"

if [[ ! -f "$ENV_FILE" ]]; then
  cp "$JENKINS_DIR/.env.example" "$ENV_FILE"
  ok "已创建 $ENV_FILE"
fi

pass="$(read_env JENKINS_ADMIN_PASSWORD)"
if [[ -z "$pass" || "$pass" == "change-me-jenkins-password" ]]; then
  pass="$(generate_secret)"
  set_env JENKINS_ADMIN_PASSWORD "$pass"
  ok "已生成 JENKINS_ADMIN_PASSWORD"
fi

host="$(curl -fsS --max-time 3 https://api.ipify.org 2>/dev/null | tr -d '[:space:]' || hostname -I 2>/dev/null | awk '{print $1}')"
[[ -n "$host" ]] || host="127.0.0.1"
port="$(read_env JENKINS_HTTP_PORT)"
port="${port:-8080}"
set_env JENKINS_URL "http://${host}:${port}/"

if command -v getent >/dev/null 2>&1; then
  gid="$(getent group docker | cut -d: -f3 || echo 999)"
  set_env DOCKER_GID "$gid"
fi

info "修复数据卷权限..."
docker compose --env-file "$ENV_FILE" -f "$JENKINS_DIR/docker-compose.yml" down 2>/dev/null || true
docker run --rm -v jenkins_jenkins-data:/var/jenkins_home busybox chown -R 1000:1000 /var/jenkins_home 2>/dev/null || true

info "重建并启动 Jenkins（启用登录认证）..."
docker compose --env-file "$ENV_FILE" -f "$JENKINS_DIR/docker-compose.yml" up -d --build

user="$(read_env JENKINS_ADMIN_USER)"
user="${user:-admin}"

cat <<EOF

========================================
  Jenkins 登录认证已启用
========================================
  地址:   http://${host}:${port}
  用户名: ${user}
  密码:   ${pass}

请妥善保存密码。GitHub Webhook 仍可匿名 POST 到 /github-webhook/
========================================

EOF
