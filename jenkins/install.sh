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

  chmod +x "$APP_DIR/jenkins/scripts/deploy.sh" 2>/dev/null || true
  chmod +x "$APP_DIR/linux-deploy.sh" 2>/dev/null || true
  ok "应用目录就绪: $APP_DIR"
}

start_jenkins() {
  [[ -f "$JENKINS_DIR/docker-compose.yml" ]] || error "缺少 $JENKINS_DIR/docker-compose.yml"

  if [[ -z "$GITHUB_WEBHOOK_SECRET" ]]; then
    GITHUB_WEBHOOK_SECRET="$(generate_secret)"
    ok "已生成 GITHUB_WEBHOOK_SECRET: $GITHUB_WEBHOOK_SECRET"
  fi

  export APP_DIR JENKINS_HTTP_PORT JENKINS_AGENT_PORT GITHUB_WEBHOOK_SECRET

  info "构建并启动 Jenkins..."
  docker compose -f "$JENKINS_DIR/docker-compose.yml" up -d --build

  info "等待 Jenkins 启动..."
  local i code
  for i in $(seq 1 60); do
    code="$(curl -s -o /dev/null -w '%{http_code}' "http://127.0.0.1:${JENKINS_HTTP_PORT}/login" 2>/dev/null || echo 000)"
    if [[ "$code" == "200" ]]; then
      ok "Jenkins 已启动"
      return 0
    fi
    sleep 3
  done
  error "Jenkins 启动超时，请查看: docker logs ai-platform-jenkins --tail=50"
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
  local host
  host="$(curl -fsS --max-time 3 https://api.ipify.org 2>/dev/null | tr -d '[:space:]' || hostname -I 2>/dev/null | awk '{print $1}')"
  [[ -n "$host" ]] || host="服务器IP"

  cat <<EOF

========================================
  Jenkins CI/CD 安装完成
========================================
  Jenkins 地址:  http://${host}:${JENKINS_HTTP_PORT}
  应用部署目录:  ${APP_DIR}
  Webhook 密钥:  ${GITHUB_WEBHOOK_SECRET}

下一步:
  1. 浏览器打开 Jenkins，完成首次向导（或已跳过向导）
  2. 新建 Pipeline 任务，Script Path 填: jenkins/Jenkinsfile
  3. 在 GitHub 仓库 Settings -> Webhooks 添加:
       Payload URL: http://${host}:${JENKINS_HTTP_PORT}/github-webhook/
       Content type: application/json
       Secret: ${GITHUB_WEBHOOK_SECRET}
       事件: Just the push event
  4. 手动 Build 一次验证；之后 push 到 main 将自动部署

常用命令:
  docker logs -f ai-platform-jenkins
  docker compose -f ${JENKINS_DIR}/docker-compose.yml restart
  docker compose -f ${JENKINS_DIR}/docker-compose.yml down

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
