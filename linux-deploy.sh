#!/usr/bin/env bash
# AI质量平台 - Linux 一键部署脚本（Docker 全栈）
#
# 用法:
#   ./linux-deploy.sh              一键安装并启动
#   ./linux-deploy.sh up           同上
#   ./linux-deploy.sh stop         停止服务
#   ./linux-deploy.sh restart      重启
#   ./linux-deploy.sh status       查看状态
#   ./linux-deploy.sh logs         查看日志
#   ./linux-deploy.sh logs backend 查看后端日志
#
# 环境变量:
#   PUBLIC_HOST=IP       外网访问地址（默认自动检测）
#   INSTALL_DOCKER=1     缺少 Docker 时自动安装（Ubuntu/Debian，默认 1）
#   WITH_MONITORING=1    同时启动 Grafana + Loki
#   RESET_MYSQL=1        删除 MySQL 数据卷后重建（会清空数据库）
#   ENV_FILE=.env.docker 指定 env 文件

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env.docker}"
COMPOSE_FILE="$ROOT/docker-compose.yml"
PUBLIC_HOST="${PUBLIC_HOST:-}"
INSTALL_DOCKER="${INSTALL_DOCKER:-1}"
WITH_MONITORING="${WITH_MONITORING:-0}"
RESET_MYSQL="${RESET_MYSQL:-0}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERR ]${NC} $*" >&2; exit 1; }

usage() {
  cat <<EOF
AI质量平台 - Linux 一键部署（Docker）

用法: $0 [命令]

命令:
  up | start        安装 Docker（如需）、配置环境、构建并启动（默认）
  stop | down       停止并移除容器
  restart           重启全部服务
  status | ps       查看容器状态
  logs [服务名]     查看日志（backend/frontend/mysql）
  diagnose          诊断 502 / 连接问题
  init-env          仅生成 .env.docker
  help              显示帮助

环境变量:
  PUBLIC_HOST       外网 IP/域名（默认自动检测）
  INSTALL_DOCKER=1  自动安装 Docker（Ubuntu/Debian）
  WITH_MONITORING=1 启动 Grafana + Loki
  RESET_MYSQL=1     清空 MySQL 数据卷后重建
  ENV_FILE          env 文件路径（默认 .env.docker）

示例:
  chmod +x linux-deploy.sh && ./linux-deploy.sh
  PUBLIC_HOST=38.12.6.230 ./linux-deploy.sh up
  WITH_MONITORING=1 ./linux-deploy.sh up
  ./linux-deploy.sh logs backend
EOF
}

fix_script_permissions() {
  if grep -q $'\r' "$0" 2>/dev/null; then
    warn "检测到 Windows 换行(CRLF)，正在修复..."
    sed -i 's/\r$//' "$0"
  fi
  chmod +x "$0" 2>/dev/null || true
  [[ -f "$ROOT/docker/deploy.sh" ]] && chmod +x "$ROOT/docker/deploy.sh" 2>/dev/null || true
  [[ -x "$ROOT/deploy.sh" ]] && chmod +x "$ROOT/deploy.sh" 2>/dev/null || true
}

detect_public_host() {
  if [[ -n "$PUBLIC_HOST" ]]; then
    echo "$PUBLIC_HOST"
    return 0
  fi
  local ip
  for url in "https://api.ipify.org" "http://icanhazip.com"; do
    if command -v curl >/dev/null 2>&1; then
      ip="$(curl -fsS --max-time 3 "$url" 2>/dev/null | tr -d '[:space:]')"
      if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]]; then
        echo "$ip"
        return 0
      fi
    fi
  done
  if command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
    [[ -n "$ip" ]] && echo "$ip" && return 0
  fi
  echo "127.0.0.1"
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

set_env_value() {
  local key="$1"
  local value="$2"
  [[ -f "$ENV_FILE" ]] || return 0
  if grep -q "^${key}=" "$ENV_FILE"; then
    sed -i "s|^${key}=.*|${key}=${value}|" "$ENV_FILE"
  else
    echo "${key}=${value}" >>"$ENV_FILE"
  fi
}

compose_cmd() {
  local profiles=()
  if [[ "$WITH_MONITORING" == "1" ]]; then
    profiles+=(--profile monitoring)
  fi
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "${profiles[@]}" "$@"
}

ensure_docker() {
  if command -v docker >/dev/null 2>&1 && docker compose version >/dev/null 2>&1; then
    ok "Docker 已就绪: $(docker --version | head -1)"
    return 0
  fi

  if [[ "$INSTALL_DOCKER" != "1" ]]; then
    error "未安装 Docker。请执行: apt install -y docker.io docker-compose-v2"
  fi

  if ! command -v apt-get >/dev/null 2>&1; then
    error "当前系统非 apt 系，请手动安装 Docker 后重试"
  fi

  info "正在安装 Docker..."
  apt-get update -qq
  DEBIAN_FRONTEND=noninteractive apt-get install -y docker.io docker-compose-v2
  systemctl enable docker >/dev/null 2>&1 || true
  systemctl start docker >/dev/null 2>&1 || true
  ok "Docker 安装完成"
}

ensure_env_file() {
  if [[ ! -f "$ENV_FILE" ]]; then
    [[ -f "$ROOT/.env.docker.example" ]] || error "缺少 .env.docker.example"
    cp "$ROOT/.env.docker.example" "$ENV_FILE"
    ok "已创建 $ENV_FILE"
  fi

  local secret
  if grep -q '^SECRET_KEY=change-this-to-a-random-secret-key' "$ENV_FILE" 2>/dev/null; then
    if command -v openssl >/dev/null 2>&1; then
      secret="$(openssl rand -hex 32)"
    else
      secret="$(python3 -c 'import secrets; print(secrets.token_hex(32))')"
    fi
    set_env_value "SECRET_KEY" "$secret"
    ok "已自动生成 SECRET_KEY"
  fi

  local host
  host="$(detect_public_host)"
  if [[ "$host" != "127.0.0.1" ]]; then
    set_env_value "GRAFANA_ROOT_URL" "http://${host}:$(read_env_value GRAFANA_PORT 3000)"
  fi
}

stop_legacy_services() {
  info "停止传统 deploy.sh 进程，避免端口冲突..."
  if [[ -x "$ROOT/deploy.sh" ]]; then
    (cd "$ROOT" && ./deploy.sh stop) 2>/dev/null || true
  fi
  local port
  for port in 8000 5173; do
    fuser -k "${port}/tcp" 2>/dev/null || true
  done
}

cmd_init_env() {
  ensure_env_file
  ok "环境文件就绪: $ENV_FILE"
  warn "请确认 MYSQL_ROOT_PASSWORD 和 DB_PASSWORD 已修改（生产环境勿用默认密码）"
}

wait_backend_ready() {
  local i url http_port
  url="http://127.0.0.1:$(read_env_value BACKEND_PORT 8000)/health"
  http_port="$(read_env_value HTTP_PORT 5173)"
  info "等待后端就绪..."
  for i in $(seq 1 90); do
    if curl -sf "$url" >/dev/null 2>&1; then
      ok "后端 API 已就绪 (端口 $(read_env_value BACKEND_PORT 8000))"
      break
    fi
    if ! compose_cmd ps backend 2>/dev/null | grep -q "Up"; then
      warn "backend 容器未运行，查看日志..."
      compose_cmd logs backend --tail=40 >&2 || true
      return 1
    fi
    if (( i == 90 )); then
      warn "后端启动超时"
      compose_cmd logs backend --tail=40 >&2 || true
      return 1
    fi
    sleep 2
  done

  info "验证 Nginx 反代..."
  for i in $(seq 1 30); do
    if curl -sf "http://127.0.0.1:${http_port}/docs" >/dev/null 2>&1; then
      ok "前端反代正常 (端口 ${http_port})"
      return 0
    fi
    sleep 2
  done
  warn "Nginx 反代未就绪，可能出现 502"
  compose_cmd logs frontend --tail=20 >&2 || true
  compose_cmd logs backend --tail=20 >&2 || true
  return 1
}

cmd_diagnose() {
  fix_script_permissions
  ensure_docker
  local http_port backend_port
  http_port="$(read_env_value HTTP_PORT 5173)"
  backend_port="$(read_env_value BACKEND_PORT 8000)"

  echo "========== 容器状态 =========="
  compose_cmd ps || true
  echo
  echo "========== 端口监听 =========="
  ss -tlnp 2>/dev/null | grep -E ":${http_port}|:${backend_port}|:3306" || netstat -tlnp 2>/dev/null | grep -E ":${http_port}|:${backend_port}|:3306" || true
  echo
  echo "========== 后端直连 =========="
  curl -sv "http://127.0.0.1:${backend_port}/" 2>&1 | head -15 || true
  echo
  echo "========== Nginx 反代 =========="
  curl -sv "http://127.0.0.1:${http_port}/docs" 2>&1 | head -15 || true
  echo
  echo "========== backend 最近日志 =========="
  compose_cmd logs backend --tail=30 || true
}

print_banner() {
  local host http_port backend_port grafana_port
  host="$(detect_public_host)"
  http_port="$(read_env_value HTTP_PORT 5173)"
  backend_port="$(read_env_value BACKEND_PORT 8000)"
  grafana_port="$(read_env_value GRAFANA_PORT 3000)"

  echo
  echo "========================================"
  echo "  AI质量平台 - 部署完成"
  echo "========================================"
  echo "  本机前端:  http://127.0.0.1:${http_port}"
  echo "  本机后端:  http://127.0.0.1:${backend_port}"
  echo "  API 文档:  http://127.0.0.1:${http_port}/docs"
  if [[ "$host" != "127.0.0.1" ]]; then
    echo "  外网前端:  http://${host}:${http_port}"
    echo "  外网后端:  http://${host}:${backend_port}"
  fi
  echo "  默认账号:  admin / admin123"
  if [[ "$WITH_MONITORING" == "1" ]]; then
    echo "  Grafana:   http://${host}:${grafana_port}"
  fi
  echo "----------------------------------------"
  echo "  常用命令:"
  echo "    ./linux-deploy.sh status"
  echo "    ./linux-deploy.sh logs backend"
  echo "    ./linux-deploy.sh restart"
  echo "    ./linux-deploy.sh stop"
  echo "========================================"
}

cmd_up() {
  fix_script_permissions
  ensure_docker
  ensure_env_file
  stop_legacy_services

  if [[ "$RESET_MYSQL" == "1" ]]; then
    warn "RESET_MYSQL=1，将删除 MySQL 数据卷..."
    compose_cmd --profile monitoring down -v 2>/dev/null || compose_cmd down -v 2>/dev/null || true
    docker volume rm ai-testing-platform_mysql-data 2>/dev/null || true
  fi

  info "构建并启动 Docker 服务（MySQL + 后端 + 前端）..."
  compose_cmd up -d --build

  if ! compose_cmd ps backend 2>/dev/null | grep -q "Up"; then
    error "backend 启动失败，日志如下:"
    compose_cmd logs backend --tail=60 >&2 || true
  fi

  wait_backend_ready || error "部署未完成：后端或 Nginx 反代未就绪，请执行: ./linux-deploy.sh diagnose"
  ok "所有服务已启动"
  compose_cmd ps
  print_banner
}

cmd_down() {
  fix_script_permissions
  ensure_docker
  compose_cmd --profile monitoring down
  ok "服务已停止"
}

cmd_restart() {
  cmd_down
  cmd_up
}

cmd_status() {
  fix_script_permissions
  ensure_docker
  compose_cmd --profile monitoring ps
}

cmd_logs() {
  fix_script_permissions
  ensure_docker
  local service="${1:-}"
  if [[ -n "$service" ]]; then
    compose_cmd logs -f --tail=100 "$service"
  else
    compose_cmd logs -f --tail=100
  fi
}

main() {
  local cmd="${1:-up}"
  case "$cmd" in
    up|start|"") cmd_up ;;
    down|stop) cmd_down ;;
    restart) cmd_restart ;;
    status|ps) cmd_status ;;
  logs) shift || true; cmd_logs "${1:-}" ;;
  diagnose|check) cmd_diagnose ;;
  init-env|init) cmd_init_env ;;
    -h|--help|help) usage ;;
    *) error "未知命令: $cmd"; usage ;;
  esac
}

main "$@"
