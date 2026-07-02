#!/usr/bin/env bash
# AI质量平台 - Docker 一键部署脚本
#
# 用法:
#   ./docker/deploy.sh up          构建并启动（MySQL + 后端 + 前端）
#   ./docker/deploy.sh up --monitoring   同时启动 Grafana + Loki
#   ./docker/deploy.sh down        停止并移除容器
#   ./docker/deploy.sh restart     重启所有服务
#   ./docker/deploy.sh logs        查看日志
#   ./docker/deploy.sh status      查看状态
#   ./docker/deploy.sh build       仅构建镜像

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env.docker}"
COMPOSE=(docker compose --env-file "$ENV_FILE" -f "$ROOT/docker-compose.yml")

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERR ]${NC} $*" >&2; exit 1; }

ensure_env() {
  if [[ ! -f "$ENV_FILE" ]]; then
    if [[ -f "$ROOT/.env.docker.example" ]]; then
      cp "$ROOT/.env.docker.example" "$ENV_FILE"
      warn "已创建 $ENV_FILE，请修改数据库密码和 SECRET_KEY 后再用于生产"
    else
      error "缺少 $ENV_FILE，请从 .env.docker.example 复制"
    fi
  fi
}

ensure_docker() {
  command -v docker >/dev/null 2>&1 || error "未找到 docker，请先安装 Docker"
  docker compose version >/dev/null 2>&1 || error "未找到 docker compose 插件"
}

compose_profiles() {
  local profiles=()
  if [[ "${WITH_MONITORING:-0}" == "1" || "${2:-}" == "--monitoring" ]]; then
    profiles+=(--profile monitoring)
  fi
  printf '%s\n' "${profiles[@]}"
}

read_env_value() {
  local key="$1"
  local default="${2:-}"
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

print_access() {
  local http_port backend_port
  http_port="$(read_env_value HTTP_PORT 5173)"
  backend_port="$(read_env_value BACKEND_PORT 8000)"
  echo
  echo "========================================"
  echo "  AI质量平台 - Docker 部署完成"
  echo "========================================"
  echo "  前端:  http://127.0.0.1:${http_port}"
  echo "  后端:  http://127.0.0.1:${backend_port}"
  echo "  文档:  http://127.0.0.1:${http_port}/docs"
  echo "  账号:  admin / admin123"
  if [[ "${WITH_MONITORING:-0}" == "1" ]]; then
    local grafana_port
    grafana_port="$(read_env_value GRAFANA_PORT 3000)"
    echo "  Grafana: http://127.0.0.1:${grafana_port} (admin / $(read_env_value GRAFANA_ADMIN_PASSWORD admin123))"
  fi
  echo "========================================"
}

cmd_up() {
  ensure_env
  ensure_docker
  local profiles
  profiles="$(compose_profiles "$@")"
  info "构建并启动 Docker 服务..."
  # shellcheck disable=SC2086
  "${COMPOSE[@]}" $profiles up -d --build
  if ! "${COMPOSE[@]}" ps backend 2>/dev/null | grep -q "Up"; then
    error "backend 容器启动失败，最近日志："
    "${COMPOSE[@]}" logs backend --tail=60 >&2 || true
    exit 1
  fi
  ok "服务已启动"
  print_access
}

cmd_down() {
  ensure_docker
  # 始终带上 monitoring profile，确保监控栈一并停止
  "${COMPOSE[@]}" --profile monitoring down
  ok "服务已停止"
}

cmd_restart() {
  cmd_down "$@"
  cmd_up "$@"
}

cmd_build() {
  ensure_env
  ensure_docker
  local profiles
  profiles="$(compose_profiles "$@")"
  # shellcheck disable=SC2086
  "${COMPOSE[@]}" $profiles build
  ok "镜像构建完成"
}

cmd_logs() {
  ensure_docker
  local service="${2:-}"
  local profiles
  profiles="$(compose_profiles "$@")"
  if [[ -n "$service" && "$service" != "--monitoring" ]]; then
    # shellcheck disable=SC2086
    "${COMPOSE[@]}" $profiles logs -f --tail=100 "$service"
  else
    # shellcheck disable=SC2086
    "${COMPOSE[@]}" $profiles logs -f --tail=100
  fi
}

cmd_status() {
  ensure_docker
  "${COMPOSE[@]}" --profile monitoring ps
}

usage() {
  cat <<EOF
AI质量平台 - Docker 部署

用法: $0 [命令] [选项]

命令:
  up [--monitoring]     构建并启动全部服务
  down [--monitoring]   停止并移除容器
  restart               重启
  build [--monitoring]  仅构建镜像
  logs [服务名]         查看日志 (backend/frontend/mysql/...)
  status                查看容器状态

环境变量:
  ENV_FILE=.env.docker  指定 env 文件
  WITH_MONITORING=1     启用 Grafana + Loki

示例:
  cp .env.docker.example .env.docker
  ./docker/deploy.sh up
  WITH_MONITORING=1 ./docker/deploy.sh up
  ./docker/deploy.sh logs backend
EOF
}

main() {
  local cmd="${1:-up}"
  case "$cmd" in
    up|start) cmd_up "$@" ;;
    down|stop) cmd_down "$@" ;;
    restart) cmd_restart "$@" ;;
    build) cmd_build "$@" ;;
    logs) cmd_logs "$@" ;;
    status|ps) cmd_status "$@" ;;
    -h|--help|help) usage ;;
    *) error "未知命令: $cmd"; usage ;;
  esac
}

main "$@"
