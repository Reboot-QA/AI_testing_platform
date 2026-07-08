#!/usr/bin/env bash
# Jenkins 流水线调用的部署脚本：拉取最新代码并重建前后端 Docker 服务
#
# 环境变量:
#   APP_DIR          应用根目录（默认 /opt/AI_testing_platform）
#   ENV_FILE         Docker 环境文件（默认 $APP_DIR/.env.docker）
#   GIT_BRANCH       拉取分支（默认 main）
#   DEPLOY_TARGET    all | backend | frontend（默认 all）
#   SKIP_BACKUP      1 跳过部署前数据库备份
#   WITH_MONITORING  1 同时管理 monitoring profile

set -euo pipefail

export PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin:${PATH:-}"

APP_DIR="${APP_DIR:-/opt/AI_testing_platform}"
ENV_FILE="${ENV_FILE:-$APP_DIR/.env.docker}"
GIT_BRANCH="${GIT_BRANCH:-main}"
DEPLOY_TARGET="${DEPLOY_TARGET:-all}"
SKIP_BACKUP="${SKIP_BACKUP:-0}"
WITH_MONITORING="${WITH_MONITORING:-0}"
COMPOSE_FILE="$APP_DIR/docker-compose.yml"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERR ]${NC} $*" >&2; exit 1; }

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || error "未找到命令: $1（请重建 Jenkins 镜像: cd jenkins && docker compose --env-file .env up -d --build）"
}

compose_cmd() {
  local profiles=()
  if [[ "$WITH_MONITORING" == "1" ]]; then
    profiles+=(--profile monitoring)
  fi
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "${profiles[@]}" "$@"
}

wait_mysql_healthy() {
  local i status
  for i in $(seq 1 60); do
    status="$(docker inspect ai-platform-mysql --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' 2>/dev/null || echo missing)"
    if [[ "$status" == "healthy" ]]; then
      ok "MySQL 已就绪"
      return 0
    fi
    if [[ "$status" == "missing" ]]; then
      warn "MySQL 容器不存在，跳过健康等待"
      return 0
    fi
    sleep 5
  done
  warn "MySQL 健康检查超时"
  return 1
}

wait_backend_ready() {
  local i url port code
  port="$(grep -E '^BACKEND_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2)"
  port="${port:-8000}"
  url="http://127.0.0.1:${port}/health"

  info "等待后端就绪: $url"
  for i in $(seq 1 90); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "$url" 2>/dev/null || echo 000)"
    if [[ "$code" == "200" ]]; then
      ok "后端健康检查通过"
      return 0
    fi
    sleep 2
  done
  error "后端启动超时，请查看: docker logs ai-platform-backend --tail=50"
}

wait_frontend_ready() {
  local i port code
  port="$(grep -E '^HTTP_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2)"
  port="${port:-5173}"

  info "等待前端反代就绪: http://127.0.0.1:${port}/"
  for i in $(seq 1 30); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${port}/" 2>/dev/null || echo 000)"
    if [[ "$code" =~ ^(200|304)$ ]]; then
      ok "前端已就绪"
      return 0
    fi
    sleep 2
  done
  warn "前端健康检查未通过，请查看: docker logs ai-platform-frontend --tail=30"
}

pull_latest() {
  [[ -d "$APP_DIR/.git" ]] || error "部署目录不是 git 仓库: $APP_DIR"

  cd "$APP_DIR"
  info "拉取最新代码 (分支: $GIT_BRANCH)..."
  git fetch origin "$GIT_BRANCH"
  git checkout "$GIT_BRANCH" 2>/dev/null || git checkout -b "$GIT_BRANCH" "origin/$GIT_BRANCH"
  git pull --ff-only origin "$GIT_BRANCH" || error "git pull 失败"
  ok "代码已更新: $(git log -1 --oneline)"
}

backup_db_if_possible() {
  [[ "$SKIP_BACKUP" == "1" ]] && return 0
  [[ -x "$APP_DIR/linux-deploy.sh" ]] || return 0
  if docker ps --format '{{.Names}}' | grep -qx ai-platform-mysql; then
    info "部署前自动备份数据库..."
    BACKUP_TAG=pre-jenkins-deploy bash "$APP_DIR/linux-deploy.sh" backup-db || warn "自动备份失败，继续部署"
  fi
}

deploy_services() {
  [[ -f "$ENV_FILE" ]] || error "缺少环境文件: $ENV_FILE（请先 cp .env.docker.example .env.docker）"

  case "$DEPLOY_TARGET" in
    all)
      info "重建并启动全部服务 (backend + frontend)..."
      compose_cmd up -d --build backend frontend
      ;;
    backend)
      info "仅重建并启动后端..."
      compose_cmd up -d --build backend
      ;;
    frontend)
      info "仅重建并启动前端..."
      compose_cmd up -d --build frontend
      ;;
    *)
      error "未知 DEPLOY_TARGET: $DEPLOY_TARGET（可选: all/backend/frontend）"
      ;;
  esac
}

print_summary() {
  local http_port backend_port
  http_port="$(grep -E '^HTTP_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2)"
  backend_port="$(grep -E '^BACKEND_PORT=' "$ENV_FILE" 2>/dev/null | tail -1 | cut -d= -f2)"
  http_port="${http_port:-5173}"
  backend_port="${backend_port:-8000}"

  echo
  echo "========================================"
  echo "  Jenkins 部署完成"
  echo "========================================"
  echo "  前端: http://127.0.0.1:${http_port}"
  echo "  后端: http://127.0.0.1:${backend_port}/health"
  echo "  提交: $(cd "$APP_DIR" && git log -1 --oneline 2>/dev/null || echo unknown)"
  echo "========================================"
  compose_cmd ps || true
}

main() {
  require_cmd docker
  require_cmd git
  require_cmd curl
  docker compose version >/dev/null 2>&1 || error "未安装 docker compose"

  info "部署目录: $APP_DIR"
  info "部署目标: $DEPLOY_TARGET"

  pull_latest
  backup_db_if_possible
  deploy_services
  wait_mysql_healthy || true

  if [[ "$DEPLOY_TARGET" != "frontend" ]]; then
    wait_backend_ready
  fi
  if [[ "$DEPLOY_TARGET" != "backend" ]]; then
    wait_frontend_ready
  fi

  print_summary
}

main "$@"
