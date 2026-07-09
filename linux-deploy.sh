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
#   BACKUP_DIR=路径      备份目录（默认 .deploy/backups/mysql）
#   BACKUP_KEEP_DAYS=30  自动清理超过 N 天的备份
#   DOCKER_BUILD_NETWORK=host  构建时使用宿主机网络（海外 VPS DNS 异常时可试）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env.docker}"
DEFAULT_MYSQL_PASSWORD='siscUTBE7250@Prod!2026'
COMPOSE_FILE="$ROOT/docker-compose.yml"
PUBLIC_HOST="${PUBLIC_HOST:-}"
INSTALL_DOCKER="${INSTALL_DOCKER:-1}"
WITH_MONITORING="${WITH_MONITORING:-0}"
RESET_MYSQL="${RESET_MYSQL:-0}"
BACKUP_DIR="${BACKUP_DIR:-$ROOT/.deploy/backups/mysql}"
BACKUP_KEEP_DAYS="${BACKUP_KEEP_DAYS:-30}"
MYSQL_CONTAINER="${MYSQL_CONTAINER:-ai-platform-mysql}"

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
  fix-db            修复 MySQL 密码不一致（清空前自动备份）
  backup-db         备份 MySQL 数据库（mysqldump + gzip）
  backup-list       列出本地备份文件
  backup-prune      清理超过 BACKUP_KEEP_DAYS 天的旧备份
  restore-db <文件> 从 .sql / .sql.gz 恢复数据库
  update | pull     从 Git 拉取代码并重新构建部署
  init-env          生成 .env.docker 并写入默认 MySQL 密码
  help              显示帮助

环境变量:
  PUBLIC_HOST       外网 IP/域名（默认自动检测）
  INSTALL_DOCKER=1  自动安装 Docker（Ubuntu/Debian）
  WITH_MONITORING=1 启动 Grafana + Loki
  RESET_MYSQL=1     清空 MySQL 数据卷前自动备份
  ENV_FILE          env 文件路径（默认 .env.docker）
  BACKUP_DIR        备份目录（默认 .deploy/backups/mysql）
  BACKUP_KEEP_DAYS  保留天数（默认 30）
  RESTORE_CONFIRM=1 恢复数据库时跳过交互确认
  DOCKER_BUILD_NETWORK  Docker 构建网络（DNS 异常时可设 host）

示例:
  chmod +x linux-deploy.sh && ./linux-deploy.sh
  PUBLIC_HOST=38.12.6.230 ./linux-deploy.sh up
  WITH_MONITORING=1 ./linux-deploy.sh up
  ./linux-deploy.sh logs backend
  ./linux-deploy.sh backup-db
  ./linux-deploy.sh restore-db .deploy/backups/mysql/ai_testcase_20260703_030000.sql.gz
EOF
}

fix_script_permissions() {
  local f
  for f in "$0" update.sh deploy.sh install-server.sh docker/deploy.sh; do
    [[ -f "$ROOT/$f" ]] || continue
    if grep -q $'\r' "$ROOT/$f" 2>/dev/null; then
      warn "检测到 $f 使用 Windows 换行(CRLF)，正在修复..."
      sed -i 's/\r$//' "$ROOT/$f"
    fi
    chmod +x "$ROOT/$f" 2>/dev/null || true
  done
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

generate_password() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 16
  else
    python3 -c 'import secrets; print(secrets.token_hex(16))'
  fi
}

is_weak_password() {
  case "$1" in
    ""|123456|password|admin123|your-password-here|change-me-to-a-strong-password|change-me-grafana-password)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

ensure_mysql_passwords() {
  local mysql_pass db_pass
  mysql_pass="$(read_env_value MYSQL_ROOT_PASSWORD)"
  db_pass="$(read_env_value DB_PASSWORD)"

  if is_weak_password "$mysql_pass" || is_weak_password "$db_pass"; then
    if is_weak_password "$mysql_pass"; then
      set_env_value "MYSQL_ROOT_PASSWORD" "$DEFAULT_MYSQL_PASSWORD"
    fi
    if is_weak_password "$db_pass"; then
      set_env_value "DB_PASSWORD" "$DEFAULT_MYSQL_PASSWORD"
    fi
    ok "已设置 MySQL 默认密码（MYSQL_ROOT_PASSWORD / DB_PASSWORD）"
    echo "       密码: $DEFAULT_MYSQL_PASSWORD"
    warn "若 MySQL 数据卷已用旧密码初始化，需执行: ./linux-deploy.sh fix-db"
  fi
}

ensure_grafana_password() {
  local grafana_pass
  grafana_pass="$(read_env_value GRAFANA_ADMIN_PASSWORD)"
  if is_weak_password "$grafana_pass"; then
    grafana_pass="$(generate_password)"
    set_env_value "GRAFANA_ADMIN_PASSWORD" "$grafana_pass"
    ok "已自动生成 GRAFANA_ADMIN_PASSWORD"
    echo "       密码: $grafana_pass"
  fi
}

compose_cmd() {
  local profiles=()
  if [[ "$WITH_MONITORING" == "1" ]]; then
    profiles+=(--profile monitoring)
  fi
  docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "${profiles[@]}" "$@"
}

health_check_hosts() {
  echo 127.0.0.1
  if getent ahostsv4 host.docker.internal >/dev/null 2>&1; then
    echo host.docker.internal
  fi
  ip route 2>/dev/null | awk '/default/ {print $3; exit}'
}

backend_health_ok() {
  local port="${1:-$(read_env_value BACKEND_PORT 8000)}"
  local host url code status

  for host in $(health_check_hosts); do
    [[ -n "$host" ]] || continue
    url="http://${host}:${port}/health"
    code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 5 "$url" 2>/dev/null || true)"
    code="${code:-000}"
    if [[ "$code" == "200" ]]; then
      return 0
    fi
    if [[ "$code" == "500" ]]; then
      echo "500"
      return 2
    fi
  done

  status="$(docker inspect ai-platform-backend --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' 2>/dev/null || echo missing)"
  [[ "$status" == "healthy" ]] && return 0
  return 1
}

http_ok() {
  local port="$1" path="${2:-/}"
  local host url code
  for host in $(health_check_hosts); do
    [[ -n "$host" ]] || continue
    url="http://${host}:${port}${path}"
    code="$(curl -s -o /dev/null -w '%{http_code}' --connect-timeout 3 --max-time 5 "$url" 2>/dev/null || true)"
    code="${code:-000}"
    [[ "$code" =~ ^(200|304)$ ]] && return 0
  done
  return 1
}

frontend_proxy_ok() {
  local http_port="${1:-5173}"
  if http_ok "$http_port" "/docs" || http_ok "$http_port" "/"; then
    return 0
  fi
  if docker exec ai-platform-frontend wget -q -O /dev/null --timeout=3 "http://127.0.0.1/docs" 2>/dev/null; then
    return 0
  fi
  if docker exec ai-platform-frontend wget -q -O /dev/null --timeout=3 "http://127.0.0.1/" 2>/dev/null; then
    return 0
  fi
  return 1
}

core_containers_running() {
  local name
  for name in ai-platform-mysql ai-platform-backend ai-platform-frontend; do
    docker ps --format '{{.Names}}' | grep -qx "$name" || return 1
  done
  return 0
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

  if grep -q $'\r' "$ENV_FILE" 2>/dev/null; then
    warn "检测到 .env.docker 含 Windows 换行(CRLF)，正在修复..."
    sed -i 's/\r$//' "$ENV_FILE"
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
    local http_port grafana_port
    http_port="$(read_env_value HTTP_PORT 5173)"
    grafana_port="$(read_env_value GRAFANA_PORT 3000)"
    set_env_value "GRAFANA_ROOT_URL" "http://${host}:${http_port}/api/v1/logs/grafana"
    set_env_value "GRAFANA_PUBLIC_URL" "http://${host}:${http_port}/api/v1/logs/grafana"
    set_env_value "LOKI_PUBLIC_URL" "http://${host}:$(read_env_value LOKI_PORT 3100)"
    set_env_value "GRAFANA_URL" "http://host.docker.internal:${grafana_port}"
  fi

  if ! grep -q '^MYSQL_PUBLISH_HOST=' "$ENV_FILE" 2>/dev/null; then
    set_env_value "MYSQL_PUBLISH_HOST" "127.0.0.1"
    ok "已设置 MYSQL_PUBLISH_HOST=127.0.0.1（仅本机/SSH 可连 MySQL）"
  fi

  ensure_mysql_passwords
  ensure_grafana_password
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

ensure_mysql_container() {
  if docker ps --format '{{.Names}}' | grep -qx "$MYSQL_CONTAINER"; then
    return 0
  fi
  error "MySQL 容器未运行: $MYSQL_CONTAINER（请先执行: ./linux-deploy.sh up）"
}

backup_timestamp() {
  date +%Y%m%d_%H%M%S
}

cmd_backup_db() {
  fix_script_permissions
  ensure_docker
  ensure_env_file
  ensure_mysql_container

  local db_name tag outfile tmpfile
  db_name="$(read_env_value DB_NAME ai_testcase)"
  tag="${BACKUP_TAG:-}"
  mkdir -p "$BACKUP_DIR"

  if [[ -n "$tag" ]]; then
    outfile="$BACKUP_DIR/${db_name}_${tag}_$(backup_timestamp).sql.gz"
  else
    outfile="$BACKUP_DIR/${db_name}_$(backup_timestamp).sql.gz"
  fi
  tmpfile="$(mktemp)"

  info "正在备份数据库 ${db_name} ..."
  if ! docker exec "$MYSQL_CONTAINER" sh -c \
    'mysqldump -uroot -p"$MYSQL_ROOT_PASSWORD" --single-transaction --routines --triggers --databases "$MYSQL_DATABASE"' \
    >"$tmpfile" 2>/dev/null; then
    rm -f "$tmpfile"
    error "备份失败，请确认 MySQL 容器健康: ./linux-deploy.sh logs mysql"
  fi

  if [[ ! -s "$tmpfile" ]]; then
    rm -f "$tmpfile"
    error "备份文件为空，请检查数据库是否存在"
  fi

  gzip -c "$tmpfile" >"$outfile"
  rm -f "$tmpfile"
  ok "备份完成: $outfile ($(du -h "$outfile" | awk '{print $1}'))"
}

cmd_backup_list() {
  fix_script_permissions
  mkdir -p "$BACKUP_DIR"
  echo "备份目录: $BACKUP_DIR"
  echo
  if ! ls -lh "$BACKUP_DIR"/*.sql.gz "$BACKUP_DIR"/*.sql 2>/dev/null; then
    warn "暂无备份文件，执行: ./linux-deploy.sh backup-db"
  fi
}

cmd_backup_prune() {
  fix_script_permissions
  mkdir -p "$BACKUP_DIR"
  local count
  count="$(find "$BACKUP_DIR" -maxdepth 1 -type f \( -name '*.sql.gz' -o -name '*.sql' \) -mtime +"$BACKUP_KEEP_DAYS" | wc -l | tr -d ' ')"
  if [[ "$count" == "0" ]]; then
    ok "无需清理（保留 ${BACKUP_KEEP_DAYS} 天内备份）"
    return 0
  fi
  info "将删除 ${count} 个超过 ${BACKUP_KEEP_DAYS} 天的备份..."
  find "$BACKUP_DIR" -maxdepth 1 -type f \( -name '*.sql.gz' -o -name '*.sql' \) -mtime +"$BACKUP_KEEP_DAYS" -print -delete
  ok "旧备份已清理"
}

cmd_restore_db() {
  fix_script_permissions
  ensure_docker
  ensure_env_file
  ensure_mysql_container

  local file="${1:-}"
  [[ -n "$file" ]] || error "用法: $0 restore-db <备份文件.sql|.sql.gz>"
  [[ -f "$file" ]] || error "备份文件不存在: $file"

  local db_name
  db_name="$(read_env_value DB_NAME ai_testcase)"

  warn "即将用备份覆盖数据库「${db_name}」中的数据: $file"
  if [[ "${RESTORE_CONFIRM:-}" != "1" ]]; then
    local ans
    read -rp "确认恢复? 输入 yes 继续: " ans
    [[ "$ans" == "yes" ]] || error "已取消"
  fi

  info "正在恢复数据库..."
  if [[ "$file" == *.gz ]]; then
    gunzip -c "$file" | docker exec -i "$MYSQL_CONTAINER" sh -c \
      'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' || error "恢复失败"
  else
    docker exec -i "$MYSQL_CONTAINER" sh -c \
      'mysql -uroot -p"$MYSQL_ROOT_PASSWORD"' <"$file" || error "恢复失败"
  fi

  info "重启后端使应用重新连接数据库..."
  docker restart ai-platform-backend >/dev/null 2>&1 || compose_cmd restart backend || true
  ok "数据库恢复完成"
}

auto_backup_before_destructive() {
  local reason="${1:-maintenance}"
  info "破坏性操作前先备份数据库（${reason}）..."
  BACKUP_TAG="$reason" cmd_backup_db || warn "自动备份失败，仍将继续操作"
}

cmd_init_env() {
  ensure_env_file
  ok "环境文件就绪: $ENV_FILE"
  echo
  grep -E '^MYSQL_ROOT_PASSWORD=|^DB_PASSWORD=|^SECRET_KEY=|^GRAFANA_ADMIN_PASSWORD=' "$ENV_FILE" || true
  warn "请妥善保存上述密码，勿提交到 Git"
}

wait_backend_ready() {
  local i http_port code body port
  port="$(read_env_value BACKEND_PORT 8000)"
  http_port="$(read_env_value HTTP_PORT 5173)"
  info "等待后端就绪 (端口 ${port})..."
  for i in $(seq 1 120); do
    body=""
    code="000"
    if backend_health_ok "$port"; then
      ok "后端 API 已就绪 (端口 ${port})"
      break
    fi
    rc=$?
    if [[ "$rc" == "2" ]]; then
      for host in $(health_check_hosts); do
        body="$(curl -s "http://${host}:${port}/health" 2>/dev/null || true)"
        [[ -n "$body" ]] && break
      done
      warn "后端启动失败: ${body:-无详情}"
      compose_cmd logs backend --tail=60 >&2 || true
      return 1
    fi
    if ! compose_cmd ps backend 2>/dev/null | grep -q "Up"; then
      warn "backend 容器未运行，查看日志..."
      compose_cmd logs backend --tail=60 >&2 || true
      return 1
    fi
    if (( i % 10 == 0 )); then
      info "等待后端就绪... (${i}/120)"
      compose_cmd logs backend --tail=5 2>/dev/null | sed 's/^/    /' >&2 || true
    fi
    if (( i == 120 )); then
      warn "后端启动超时"
      compose_cmd logs backend --tail=60 >&2 || true
      return 1
    fi
    sleep 2
  done

  info "验证前端服务..."
  for i in $(seq 1 30); do
    if frontend_proxy_ok "$http_port"; then
      ok "前端已就绪 (端口 ${http_port})"
      return 0
    fi
    sleep 2
  done
  if core_containers_running; then
    warn "宿主机端口 ${http_port} 探测失败，但 MySQL/后端/前端容器均已运行"
    ok "部署完成，请在浏览器访问: http://服务器IP:${http_port}"
    return 0
  fi
  warn "前端未就绪"
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
  echo
  echo "========== MySQL 健康检查 =========="
  docker inspect ai-platform-mysql --format '状态: {{.State.Status}} | 健康: {{if .State.Health}}{{.State.Health.Status}}{{else}}无{{end}}' 2>/dev/null || warn "MySQL 容器不存在"
  docker inspect ai-platform-mysql --format '{{range .State.Health.Log}}{{.ExitCode}} {{.Output}}{{println}}{{end}}' 2>/dev/null | tail -5 || true
  echo
  echo "========== mysql 最近日志 =========="
  compose_cmd logs mysql --tail=40 || true
  echo
  echo "========== MySQL 连接测试 =========="
  if docker ps --format '{{.Names}}' | grep -qx ai-platform-mysql; then
    local hc_ok=0
    if command -v timeout >/dev/null 2>&1; then
      timeout 15 docker exec ai-platform-mysql sh /healthcheck.sh >/dev/null 2>&1 && hc_ok=1
    else
      docker exec ai-platform-mysql sh /healthcheck.sh >/dev/null 2>&1 && hc_ok=1
    fi
    if [[ "$hc_ok" == "1" ]]; then
      ok "MySQL 健康检查脚本通过"
    else
      warn "MySQL 健康检查失败或超时，常见原因："
      echo "  1) .env.docker 密码与数据卷不一致 → ./linux-deploy.sh fix-db"
      echo "  2) MySQL 仍在重启/恢复中 → 等待 1 分钟后 ./linux-deploy.sh restart"
      if command -v timeout >/dev/null 2>&1; then
        timeout 10 docker exec ai-platform-mysql sh -c \
          'export MYSQL_PWD="$MYSQL_ROOT_PASSWORD"; mysqladmin ping -h 127.0.0.1 -uroot --connect-timeout=3' 2>&1 | tail -3 || true
      fi
    fi
  fi
}

reset_mysql_volume() {
  auto_backup_before_destructive "pre-reset"
  info "停止服务并删除 MySQL 数据卷..."
  compose_cmd --profile monitoring down -v 2>/dev/null || true
  compose_cmd down -v 2>/dev/null || true
  docker rm -f ai-platform-mysql ai-platform-backend ai-platform-frontend 2>/dev/null || true
  local vol
  for vol in ai-testing-platform_mysql-data; do
    docker volume rm "$vol" 2>/dev/null || true
  done
  while read -r vol; do
    [[ -n "$vol" ]] && docker volume rm "$vol" 2>/dev/null || true
  done < <(docker volume ls -q | grep -E 'mysql-data|ai-testing-platform' || true)
  ok "MySQL 数据卷已删除"
}

check_backend_mysql_auth_error() {
  compose_cmd logs backend 2>/dev/null | tail -30 | grep -q "Access denied for user"
}

cmd_fix_db() {
  fix_script_permissions
  ensure_docker
  ensure_env_file
  stop_legacy_services
  reset_mysql_volume
  info "将使用 .env.docker 中的密码重新初始化 MySQL："
  grep -E '^MYSQL_ROOT_PASSWORD=|^DB_PASSWORD=' "$ENV_FILE" || true
  RESET_MYSQL=0
  cmd_up
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
  echo "    ./linux-deploy.sh backup-db"
  echo "========================================"
}

cmd_up() {
  fix_script_permissions
  ensure_docker
  ensure_env_file
  stop_legacy_services

  if [[ "$RESET_MYSQL" == "1" ]]; then
    reset_mysql_volume
  fi

  info "构建并启动 Docker 服务（MySQL + 后端 + 前端）..."
  if [[ "${DOCKER_BUILD_NETWORK:-}" == "host" ]]; then
    warn "DOCKER_BUILD_NETWORK=host：构建阶段使用宿主机网络（适用于 DNS 解析异常）"
  fi
  compose_cmd up -d --build

  info "等待 MySQL 健康检查..."
  local i mysql_status
  for i in $(seq 1 60); do
    mysql_status="$(docker inspect ai-platform-mysql --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' 2>/dev/null || echo missing)"
    if [[ "$mysql_status" == "healthy" ]]; then
      ok "MySQL 已就绪"
      break
    fi
    if [[ "$mysql_status" == "missing" ]]; then
      warn "MySQL 容器不存在"
      break
    fi
    if (( i % 6 == 0 )); then
      info "MySQL 状态: ${mysql_status} (${i}/60)"
    fi
    if (( i == 60 )); then
      warn "MySQL 健康检查超时，请执行: ./linux-deploy.sh diagnose"
      compose_cmd logs mysql --tail=30 >&2 || true
    fi
    sleep 5
  done

  if check_backend_mysql_auth_error; then
    cat <<'EOF' >&2

[ERR] MySQL 密码与已有数据卷不一致（Access denied）。
      修改 .env.docker 里的 DB_PASSWORD 不会自动改库内密码。

修复（会清空数据库）:
  ./linux-deploy.sh fix-db

EOF
    exit 1
  fi

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

ensure_git_safe_directory() {
  [[ -d "$ROOT/.git" ]] || return 0
  git config --global --add safe.directory "$ROOT" 2>/dev/null || true
}

cmd_update() {
  fix_script_permissions
  ensure_docker
  ensure_env_file
  stop_legacy_services

  if [[ -d "$ROOT/.git" ]]; then
    ensure_git_safe_directory
    info "拉取 GitHub 最新代码..."
    git pull --ff-only origin "$(git rev-parse --abbrev-ref HEAD 2>/dev/null || echo main)" || \
      git pull --ff-only || error "git pull 失败，请检查网络或手动 git pull"
    ok "代码已更新: $(git log -1 --oneline 2>/dev/null || true)"
  else
    warn "当前目录不是 git 仓库，跳过 git pull"
  fi

  info "重新构建并启动 Docker 服务..."
  compose_cmd up -d --build

  info "等待 MySQL 健康检查..."
  local i mysql_status
  for i in $(seq 1 60); do
    mysql_status="$(docker inspect ai-platform-mysql --format '{{if .State.Health}}{{.State.Health.Status}}{{else}}unknown{{end}}' 2>/dev/null || echo missing)"
    if [[ "$mysql_status" == "healthy" ]]; then
      ok "MySQL 已就绪"
      break
    fi
    if [[ "$mysql_status" == "missing" ]]; then
      warn "MySQL 容器不存在"
      break
    fi
    if (( i % 6 == 0 )); then
      info "MySQL 状态: ${mysql_status} (${i}/60)"
    fi
    if (( i == 60 )); then
      warn "MySQL 健康检查超时，请执行: ./linux-deploy.sh diagnose"
      compose_cmd logs mysql --tail=30 >&2 || true
    fi
    sleep 5
  done

  if check_backend_mysql_auth_error; then
    error "MySQL 密码不一致，请执行: ./linux-deploy.sh fix-db"
  fi

  wait_backend_ready || error "更新后服务未就绪，请执行: ./linux-deploy.sh diagnose"
  ok "更新完成"
  compose_cmd ps
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
  fix-db|fixdb) cmd_fix_db ;;
  backup-db|backup) cmd_backup_db ;;
  backup-list|backups) cmd_backup_list ;;
  backup-prune|prune-backups) cmd_backup_prune ;;
  restore-db|restore) shift || true; cmd_restore_db "${1:-}" ;;
  update|pull) cmd_update ;;
  init-env|init) cmd_init_env ;;
    -h|--help|help) usage ;;
    *) error "未知命令: $cmd"; usage ;;
  esac
}

main "$@"
