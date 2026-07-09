#!/usr/bin/env bash
# AI测试平台 - Jenkins CI/CD 一键安装
#
# 在 Linux 部署服务器上执行（需已安装 Docker，或与 linux-deploy.sh 同机）:
#   cd /opt/AI_testing_platform
#   chmod +x jenkins/install.sh
#   sudo ./jenkins/install.sh
#
# 环境变量:
#   APP_DIR=/opt/AI_testing_platform     应用部署目录
#   JENKINS_HTTP_PORT=8080               Jenkins Web 端口
#   GITHUB_WEBHOOK_SECRET=随机字符串      GitHub Webhook 密钥
#   SKIP_APP_INSTALL=1                   跳过克隆/更新应用仓库
#   CREATE_JOB=1                         安装后自动创建 Pipeline 任务（默认 1）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
JENKINS_DIR="$ROOT/jenkins"
APP_DIR="${APP_DIR:-/opt/AI_testing_platform}"
JENKINS_HTTP_PORT="${JENKINS_HTTP_PORT:-8080}"
JENKINS_AGENT_PORT="${JENKINS_AGENT_PORT:-50000}"
GITHUB_WEBHOOK_SECRET="${GITHUB_WEBHOOK_SECRET:-}"
GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/Reboot-QA/AI_testing_platform.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"
CREATE_JOB="${CREATE_JOB:-1}"
SKIP_APP_INSTALL="${SKIP_APP_INSTALL:-0}"

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERR ]${NC} $*" >&2; exit 1; }

require_root() {
  if [[ "${EUID:-$(id -u)}" -ne 0 ]]; then
    error "请使用 root 或 sudo 执行: sudo $0"
  fi
}

generate_secret() {
  if command -v openssl >/dev/null 2>&1; then
    openssl rand -hex 16
  else
    python3 -c 'import secrets; print(secrets.token_hex(16))'
  fi
}

ensure_docker() {
  command -v docker >/dev/null 2>&1 || error "未安装 Docker，请先执行: ./linux-deploy.sh up"
  docker compose version >/dev/null 2>&1 || error "未安装 docker compose"
  ok "Docker 已就绪"
}

ensure_app_dir() {
  if [[ "$SKIP_APP_INSTALL" == "1" ]]; then
    [[ -d "$APP_DIR" ]] || error "APP_DIR 不存在: $APP_DIR"
    return 0
  fi

  local parent
  parent="$(dirname "$APP_DIR")"
  mkdir -p "$parent"

  if [[ -d "$APP_DIR/.git" ]]; then
    info "更新应用仓库: $APP_DIR"
    git -C "$APP_DIR" fetch origin "$GIT_BRANCH"
    git -C "$APP_DIR" checkout "$GIT_BRANCH" 2>/dev/null || true
    git -C "$APP_DIR" pull --ff-only origin "$GIT_BRANCH" || warn "git pull 失败，可稍后手动更新"
  elif [[ ! -e "$APP_DIR" ]]; then
    info "克隆应用仓库 -> $APP_DIR"
    git clone -b "$GIT_BRANCH" "$GIT_REPO_URL" "$APP_DIR"
  else
    error "目录已存在且非 git 仓库: $APP_DIR"
  fi

  if [[ ! -f "$APP_DIR/.env.docker" ]]; then
    if [[ -f "$APP_DIR/.env.docker.example" ]]; then
      cp "$APP_DIR/.env.docker.example" "$APP_DIR/.env.docker"
      warn "已创建 $APP_DIR/.env.docker，请修改密码后重新部署应用"
    fi
  fi

  chmod +x "$APP_DIR/update.sh" 2>/dev/null || true
  chmod +x "$APP_DIR/jenkins/scripts/deploy.sh" 2>/dev/null || true
  chmod +x "$APP_DIR/linux-deploy.sh" 2>/dev/null || true
  ok "应用目录就绪: $APP_DIR"
}

is_weak_jenkins_password() {
  case "$1" in
    ""|admin|admin123|password|123456|change-me-jenkins-password)
      return 0
      ;;
    *)
      return 1
      ;;
  esac
}

ensure_jenkins_env_file() {
  local env_file="$JENKINS_DIR/.env"
  local host pass user port

  if [[ ! -f "$env_file" ]]; then
    cp "$JENKINS_DIR/.env.example" "$env_file"
    ok "已创建 $env_file"
  fi

  if grep -q $'\r' "$env_file" 2>/dev/null; then
    sed -i 's/\r$//' "$env_file"
  fi

  pass="$(grep -E '^JENKINS_ADMIN_PASSWORD=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  if is_weak_jenkins_password "$pass"; then
    pass="$(generate_secret)"
    if grep -q '^JENKINS_ADMIN_PASSWORD=' "$env_file" 2>/dev/null; then
      sed -i "s|^JENKINS_ADMIN_PASSWORD=.*|JENKINS_ADMIN_PASSWORD=${pass}|" "$env_file"
    else
      echo "JENKINS_ADMIN_PASSWORD=${pass}" >>"$env_file"
    fi
    ok "已自动生成 JENKINS_ADMIN_PASSWORD"
  fi

  if [[ -z "$GITHUB_WEBHOOK_SECRET" ]]; then
    GITHUB_WEBHOOK_SECRET="$(grep -E '^GITHUB_WEBHOOK_SECRET=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  fi
  if [[ -z "$GITHUB_WEBHOOK_SECRET" || "$GITHUB_WEBHOOK_SECRET" == "change-me-webhook-secret" ]]; then
    GITHUB_WEBHOOK_SECRET="$(generate_secret)"
    if grep -q '^GITHUB_WEBHOOK_SECRET=' "$env_file" 2>/dev/null; then
      sed -i "s|^GITHUB_WEBHOOK_SECRET=.*|GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}|" "$env_file"
    else
      echo "GITHUB_WEBHOOK_SECRET=${GITHUB_WEBHOOK_SECRET}" >>"$env_file"
    fi
    ok "已自动生成 GITHUB_WEBHOOK_SECRET"
  fi

  host="$(curl -fsS --max-time 3 https://api.ipify.org 2>/dev/null | tr -d '[:space:]' || hostname -I 2>/dev/null | awk '{print $1}')"
  [[ -n "$host" ]] || host="127.0.0.1"
  port="$(grep -E '^JENKINS_HTTP_PORT=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2-)"
  port="${port:-8080}"
  if ! grep -q '^JENKINS_URL=' "$env_file" 2>/dev/null; then
    echo "JENKINS_URL=http://${host}:${port}/" >>"$env_file"
  fi

  if [[ -z "${DOCKER_GID:-}" ]] && command -v getent >/dev/null 2>&1; then
    DOCKER_GID="$(getent group docker | cut -d: -f3 || true)"
    if grep -q '^DOCKER_GID=' "$env_file" 2>/dev/null; then
      sed -i "s|^DOCKER_GID=.*|DOCKER_GID=${DOCKER_GID}|" "$env_file"
    else
      echo "DOCKER_GID=${DOCKER_GID}" >>"$env_file"
    fi
  fi

  chmod 600 "$env_file" 2>/dev/null || true
  ok "Jenkins 环境文件就绪: $env_file"
}

fix_jenkins_volume_permissions() {
  local compose_file="$JENKINS_DIR/docker-compose.yml"
  local env_file="$JENKINS_DIR/.env"
  local volume_name="jenkins_jenkins-data"

  info "修复 Jenkins 数据卷权限（jenkins 用户 UID=1000）..."
  docker compose --env-file "$env_file" -f "$compose_file" down 2>/dev/null || true

  docker volume create "$volume_name" >/dev/null 2>&1 || true
  docker run --rm \
    -v "${volume_name}:/var/jenkins_home" \
    busybox chown -R 1000:1000 /var/jenkins_home

  ok "数据卷权限已修复: $volume_name"
}

fix_app_permissions() {
  local fix_script="$APP_DIR/jenkins/fix-app-permissions.sh"
  if [[ -x "$fix_script" ]]; then
    info "修复应用目录权限（供 Jenkins git pull）..."
    APP_DIR="$APP_DIR" bash "$fix_script" || warn "权限修复失败，可手动: sudo bash $fix_script"
  fi
}

start_jenkins() {
  local env_file="$JENKINS_DIR/.env"
  [[ -f "$JENKINS_DIR/docker-compose.yml" ]] || error "缺少 $JENKINS_DIR/docker-compose.yml"

  ensure_jenkins_env_file

  fix_jenkins_volume_permissions

  info "构建并启动 Jenkins（已启用登录认证）..."
  docker compose --env-file "$env_file" -f "$JENKINS_DIR/docker-compose.yml" up -d --build

  if [[ -f "$APP_DIR/jenkins/fix-app-permissions.sh" ]]; then
    warn "首次 Jenkins 发版前请执行: sudo bash $APP_DIR/jenkins/fix-app-permissions.sh"
  fi

  wait_jenkins_ready
}

wait_jenkins_ready() {
  # 首次启动需下载/初始化插件，低配 VPS 常需 5～15 分钟
  local max_wait="${JENKINS_STARTUP_TIMEOUT:-900}"
  local interval=5
  local elapsed=0
  local code

  info "等待 Jenkins 启动（首次可能需 5～15 分钟，超时 ${max_wait}s）..."
  while (( elapsed < max_wait )); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${JENKINS_HTTP_PORT}/login" 2>/dev/null || echo 000)"
    if [[ "$code" == "200" ]]; then
      ok "Jenkins 已启动（耗时约 ${elapsed}s）"
      return 0
    fi

    if docker logs ai-platform-jenkins 2>&1 | tail -20 | grep -q "Jenkins is fully up and running"; then
      ok "Jenkins 已就绪（日志确认，耗时约 ${elapsed}s）"
      return 0
    fi

    if (( elapsed > 0 && elapsed % 30 == 0 )); then
      info "仍在启动中... 已等待 ${elapsed}s，最近日志:"
      docker logs ai-platform-jenkins --tail=5 2>&1 | sed 's/^/    /' || true
    fi

    sleep "$interval"
    elapsed=$((elapsed + interval))
  done

  warn "等待超时（${max_wait}s），但容器可能仍在后台初始化"
  warn "请继续执行: docker logs -f ai-platform-jenkins"
  warn "看到 'Jenkins is fully up and running' 后访问: http://服务器IP:${JENKINS_HTTP_PORT}"
  docker ps --filter name=ai-platform-jenkins --format 'table {{.Names}}\t{{.Status}}\t{{.Ports}}' || true
  return 0
}

create_pipeline_job() {
  [[ "$CREATE_JOB" == "1" ]] || return 0

  local crumb crumb_field token_xml job_name="ai-testing-platform-deploy"
  local jenkins_url="http://127.0.0.1:${JENKINS_HTTP_PORT}"

  info "尝试自动创建 Pipeline 任务: $job_name"

  # 首次启动可能尚无 admin 用户，跳过自动建任务
  if ! curl -sf "${jenkins_url}/api/json" >/dev/null 2>&1; then
    warn "Jenkins API 暂不可用，请手动创建任务（见 jenkins/README.md）"
    return 0
  fi

  # 使用匿名只读探测；若需认证则提示手动创建
  if curl -sf "${jenkins_url}/job/${job_name}/api/json" >/dev/null 2>&1; then
    ok "任务已存在: $job_name"
    return 0
  fi

  warn "请按 jenkins/README.md 手动创建 Pipeline 任务（首次需完成 Jenkins 初始化）"
}

print_banner() {
  local host user pass port env_file="$JENKINS_DIR/.env"
  host="$(curl -fsS --max-time 3 https://api.ipify.org 2>/dev/null | tr -d '[:space:]' || hostname -I 2>/dev/null | awk '{print $1}')"
  [[ -n "$host" ]] || host="服务器IP"
  user="$(grep -E '^JENKINS_ADMIN_USER=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2-)"
  user="${user:-admin}"
  pass="$(grep -E '^JENKINS_ADMIN_PASSWORD=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2-)"
  port="$(grep -E '^JENKINS_HTTP_PORT=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2-)"
  port="${port:-8080}"
  GITHUB_WEBHOOK_SECRET="$(grep -E '^GITHUB_WEBHOOK_SECRET=' "$env_file" 2>/dev/null | tail -1 | cut -d= -f2-)"

  cat <<EOF

========================================
  Jenkins CI/CD 安装完成
========================================
  Jenkins 地址:  http://${host}:${port}
  登录用户名:    ${user}
  登录密码:      ${pass}
  应用部署目录:  ${APP_DIR}
  Webhook 密钥:  ${GITHUB_WEBHOOK_SECRET}

  密码保存在: ${env_file}（请勿提交 Git）

下一步:
  1. 浏览器打开 Jenkins，使用上述账号登录
  2. 新建 Pipeline 任务，Script Path 填: jenkins/Jenkinsfile
  3. 在 GitHub 仓库 Settings -> Webhooks 添加:
       Payload URL: http://${host}:${port}/github-webhook/
       Content type: application/json
       Secret: ${GITHUB_WEBHOOK_SECRET}
       事件: Just the push event
  4. 手动 Build 一次验证；之后 push 到 main 将自动部署

常用命令:
  docker logs -f ai-platform-jenkins
  docker compose --env-file ${env_file} -f ${JENKINS_DIR}/docker-compose.yml restart

详细文档: ${APP_DIR}/jenkins/README.md
========================================

EOF
}

main() {
  require_root
  ensure_docker
  ensure_app_dir
  start_jenkins
  create_pipeline_job
  print_banner
}

main "$@"
