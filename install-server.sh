#!/usr/bin/env bash
# AI质量平台 - Linux 服务器远程一键安装
#
# 用法:
#   curl -fsSL https://raw.githubusercontent.com/Reboot-QA/AI_testing_platform/main/install-server.sh | bash
#
# 或:
#   PUBLIC_HOST=你的公网IP INSTALL_DIR=/opt/AI_testing_platform ./install-server.sh

set -euo pipefail

GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/Reboot-QA/AI_testing_platform.git}"
GIT_BRANCH="${GIT_BRANCH:-main}"
INSTALL_DIR="${INSTALL_DIR:-$(pwd)/AI_testing_platform}"
PUBLIC_HOST="${PUBLIC_HOST:-}"
WITH_MONITORING="${WITH_MONITORING:-0}"
REINSTALL="${REINSTALL:-0}"
INSTALL_DOCKER="${INSTALL_DOCKER:-1}"

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
  command -v "$1" >/dev/null 2>&1 || error "未找到命令: $1"
}

install_fresh() {
  local parent
  parent="$(dirname "$INSTALL_DIR")"
  mkdir -p "$parent"

  if [[ -e "$INSTALL_DIR" ]]; then
    if [[ "$REINSTALL" == "1" ]]; then
      warn "删除旧目录: $INSTALL_DIR"
      rm -rf "$INSTALL_DIR"
    elif [[ -d "$INSTALL_DIR/.git" ]]; then
      info "目录已是 Git 仓库，执行更新"
      cd "$INSTALL_DIR"
      git pull --ff-only origin "$GIT_BRANCH" || git pull
      return 0
    elif [[ -n "$(ls -A "$INSTALL_DIR" 2>/dev/null)" ]]; then
      error "目标目录非空: $INSTALL_DIR (可设 REINSTALL=1 强制重装)"
    fi
  fi

  info "克隆 $GIT_REPO_URL -> $INSTALL_DIR"
  git clone -b "$GIT_BRANCH" --depth 1 "$GIT_REPO_URL" "$INSTALL_DIR"
  ok "克隆完成"
}

main() {
  require_cmd git
  [[ "${1:-}" == "-h" || "${1:-}" == "--help" ]] && {
    echo "用法: PUBLIC_HOST=IP INSTALL_DIR=/opt/AI_testing_platform $0"
    exit 0
  }

  if [[ "$INSTALL_DIR" != /* ]]; then
    INSTALL_DIR="$(cd "$(dirname "$INSTALL_DIR")" && pwd)/$(basename "$INSTALL_DIR")"
  fi

  info "安装目录: $INSTALL_DIR"
  install_fresh
  cd "$INSTALL_DIR"

  export PUBLIC_HOST WITH_MONITORING INSTALL_DOCKER
  bash linux-deploy.sh up
}

main "$@"
