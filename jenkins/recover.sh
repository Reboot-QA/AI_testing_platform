#!/usr/bin/env bash
# Jenkins 崩溃/一直「准备中」修复脚本
#
# 典型现象: docker ps 显示 Restarting，页面一直 Jenkins is getting ready
#
# 用法:
#   cd /opt/AI_testing_platform
#   sudo bash jenkins/recover.sh

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JENKINS_DIR="$ROOT/jenkins"
ENV_FILE="$JENKINS_DIR/.env"
COMPOSE_FILE="$JENKINS_DIR/docker-compose.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }

echo "========== 1. 当前容器状态 =========="
docker ps -a --filter name=ai-platform-jenkins --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true

echo
echo "========== 2. 最近错误日志 =========="
docker logs ai-platform-jenkins --tail=40 2>&1 || warn "无法读取日志（容器可能不存在）"

if [[ ! -f "$ENV_FILE" ]]; then
  info "创建 jenkins/.env ..."
  cp "$JENKINS_DIR/.env.example" "$ENV_FILE"
fi

if grep -q $'\r' "$ENV_FILE" 2>/dev/null; then
  sed -i 's/\r$//' "$ENV_FILE"
fi

pass="$(grep -E '^JENKINS_ADMIN_PASSWORD=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
if [[ -z "$pass" || "$pass" == "change-me-jenkins-password" ]]; then
  pass="$(openssl rand -hex 12 2>/dev/null || python3 -c 'import secrets; print(secrets.token_hex(12))')"
  if grep -q '^JENKINS_ADMIN_PASSWORD=' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^JENKINS_ADMIN_PASSWORD=.*|JENKINS_ADMIN_PASSWORD=${pass}|" "$ENV_FILE"
  else
    echo "JENKINS_ADMIN_PASSWORD=${pass}" >>"$ENV_FILE"
  fi
  ok "已生成 JENKINS_ADMIN_PASSWORD"
fi

if command -v getent >/dev/null 2>&1; then
  gid="$(getent group docker | cut -d: -f3 || echo 999)"
  if grep -q '^DOCKER_GID=' "$ENV_FILE" 2>/dev/null; then
    sed -i "s|^DOCKER_GID=.*|DOCKER_GID=${gid}|" "$ENV_FILE"
  else
    echo "DOCKER_GID=${gid}" >>"$ENV_FILE"
  fi
fi

chmod 600 "$ENV_FILE" 2>/dev/null || true

info "停止 Jenkins ..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down 2>/dev/null || true

if [[ "${RESET_JENKINS:-}" == "1" ]]; then
  warn "RESET_JENKINS=1：删除 Jenkins 数据卷（会丢失任务配置）..."
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" down -v 2>/dev/null || true
  docker volume rm jenkins_jenkins-data 2>/dev/null || true
else
  info "清理数据卷中可能卡住的 init 脚本 ..."
  docker run --rm -v jenkins_jenkins-data:/var/jenkins_home busybox sh -c \
    'rm -rf /var/jenkins_home/init.groovy.d 2>/dev/null; chown -R 1000:1000 /var/jenkins_home' 2>/dev/null || true
fi

info "修复数据卷权限 ..."
docker volume create jenkins_jenkins-data >/dev/null 2>&1 || true
docker run --rm -v jenkins_jenkins-data:/var/jenkins_home busybox chown -R 1000:1000 /var/jenkins_home 2>/dev/null || true

info "注入 init 脚本到数据卷（可写，避免只读挂载导致崩溃）..."
docker run --rm \
  -v jenkins_jenkins-data:/var/jenkins_home \
  -v "$JENKINS_DIR/init.groovy.d:/src:ro" \
  busybox sh -c 'mkdir -p /var/jenkins_home/init.groovy.d && cp /src/*.groovy /var/jenkins_home/init.groovy.d/ 2>/dev/null || true; chown -R 1000:1000 /var/jenkins_home/init.groovy.d' 2>/dev/null || true

info "重建并启动 Jenkins ..."
docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" up -d --build --force-recreate

info "验证部署目录挂载 ..."
if docker exec ai-platform-jenkins test -f /opt/AI_testing_platform/update.sh 2>/dev/null; then
  ok "已挂载 /opt/AI_testing_platform"
else
  warn "容器内仍看不到 update.sh，请执行:"
  warn "  docker inspect ai-platform-jenkins --format '{{range .Mounts}}{{.Source}} -> {{.Destination}}{{println}}{{end}}'"
fi

echo
info "等待启动（约 1～5 分钟），实时日志:"
echo "  docker logs -f ai-platform-jenkins"
echo

user="$(grep -E '^JENKINS_ADMIN_USER=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2-)"
user="${user:-admin}"
port="$(grep -E '^JENKINS_HTTP_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2-)"
port="${port:-8080}"

cat <<EOF
========================================
  修复命令已执行
========================================
  登录用户名: ${user}
  登录密码:   ${pass}
  访问地址:   http://服务器IP:${port}

若仍 Restarting，先查看日志:
  docker logs ai-platform-jenkins --tail=80

彻底重置 Jenkins（会丢失任务配置，推荐此时使用）:
  RESET_JENKINS=1 sudo bash jenkins/recover.sh
========================================
EOF
