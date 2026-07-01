#!/usr/bin/env bash
# AI质量平台 - Linux 服务器一键安装/重装脚本
#
# 用法:
#   curl -fsSL https://raw.githubusercontent.com/Reboot-QA/AI_testing_platform/main/install-server.sh | bash
#
# 或下载后执行:
#   PUBLIC_HOST=你的公网IP INSTALL_DIR=/opt/AI_testing_platform ./install-server.sh
#
# 环境变量:
#   INSTALL_DIR       安装目录 (默认: 当前目录下的 AI_testing_platform)
#   GIT_REPO_URL      Git 仓库 (默认官方仓库)
#   GIT_BRANCH        分支 (默认 main)
#   PUBLIC_HOST       外网 IP/域名，写入访问地址与 Grafana
#   WITH_MONITORING   1=同时启动 Grafana+Loki (需 Docker)
#   SKIP_FRONTEND     1=仅部署后端
#   REINSTALL         1=强制删除旧目录重装 (默认: 若已是 Git 仓库则 update)

set -euo pipefail

GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/Reboot-QA/AI_testing_platform.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-$(pwd)/AI_testing_platform}"
PUBLIC_HOST="${PUBLIC_HOST:-}"
WITH_MONITORING="${WITH_MONITORING:-0}"
SKIP_FRONTEND="${SKIP_FRONTEND:-0}"
REINSTALL="${REINSTALL:-0}"

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
用法: $0

环境变量:
  INSTALL_DIR=$INSTALL_DIR
  GIT_BRANCH=$GIT_BRANCH
  PUBLIC_HOST=${PUBLIC_HOST:-(自动检测)}
  WITH_MONITORING=$WITH_MONITORING
  REINSTALL=$REINSTALL

示例:
  PUBLIC_HOST=38.12.6.230 INSTALL_DIR=/opt/AI_testing_platform $0
  WITH_MONITORING=1 PUBLIC_HOST=38.12.6.230 $0
EOF
}

[[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && usage && exit 0

require_cmd() {
  command -v "$1" >/dev/null 2>&1 || error "未找到命令: $1"
}

stop_old_instance() {
  local dir="$1"
  [[ -x "$dir/deploy.sh" ]] || return 0
  info "停止旧实例服务..."
  (cd "$dir" && ./deploy.sh stop) 2>/dev/null || true
  (cd "$dir" && ./deploy.sh monitoring stop) 2>/dev/null || true
}

install_fresh() {
  local parent
  parent="$(dirname "$INSTALL_DIR")"
  mkdir -p "$parent"

  if [[ -e "$INSTALL_DIR" ]]; then
    if [[ "$REINSTALL" == "1" ]]; then
      stop_old_instance "$INSTALL_DIR"
      warn "删除旧目录: $INSTALL_DIR"
      rm -rf "$INSTALL_DIR"
    elif [[ -d "$INSTALL_DIR/.git" ]]; then
      info "目录已是 Git 仓库，执行更新而非重装"
      update_existing
      return
    elif [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
      error "目标目录非空且不是 Git 仓库: $INSTALL_DIR (可设 REINSTALL=1 强制重装)"
    fi
  fi

  info "克隆 $GIT_REPO_URL (分支: $GIT_BRANCH) -> $INSTALL_DIR"
  git clone -b "$GIT_BRANCH" --depth 1 "$GIT_REPO_URL" "$INSTALL_DIR"
  ok "克隆完成"
}

update_existing() {
  cd "$INSTALL_DIR"
  chmod +x deploy.sh
  export PUBLIC_HOST SKIP_FRONTEND
  ./deploy.sh update
  start_monitoring_if_needed
  print_done
  exit 0
}

deploy_app() {
  cd "$INSTALL_DIR"
  chmod +x deploy.sh
  export PUBLIC_HOST SKIP_FRONTEND
  info "安装依赖并启动服务..."
  ./deploy.sh
}

start_monitoring_if_needed() {
  if [[ "$WITH_MONITORING" != "1" ]]; then
    return 0
  fi
  if ! command -v docker >/dev/null 2>&1; then
    warn "未安装 Docker，跳过监控栈 (WITH_MONITORING=1 需先安装 Docker)"
    return 0
  fi
  info "启动 Grafana + Loki 监控栈..."
  export PUBLIC_HOST
  ./deploy.sh monitoring start || warn "监控栈启动失败，可稍后执行: ./deploy.sh monitoring start"
}

print_done() {
  cat <<EOF

========================================
  安装完成
========================================
  目录:   $INSTALL_DIR
  状态:   cd $INSTALL_DIR && ./deploy.sh status
  日志:   cd $INSTALL_DIR && ./deploy.sh logs
  更新:   cd $INSTALL_DIR && ./deploy.sh update
  监控:   cd $INSTALL_DIR && ./deploy.sh monitoring start

EOF
}

main() {
  require_cmd git

  if [[ "$INSTALL_DIR" != /* ]]; then
    INSTALL_DIR="$(cd "$(dirname "$INSTALL_DIR")" && pwd)/$(basename "$INSTALL_DIR")"
  fi

  info "安装目录: $INSTALL_DIR"
  install_fresh
  deploy_app
  start_monitoring_if_needed
  print_done
}

main "$@"
