#!/usr/bin/env bash
# AI质量平台 - 一键更新（git pull + Docker 重新部署）
#
# 用法:
#   bash update.sh
#   ./update.sh          # 需 chmod +x update.sh
#
# 环境变量:
#   ENV_FILE=.env.docker  指定 Docker 环境文件

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$ROOT"

ENV_FILE="${ENV_FILE:-$ROOT/.env.docker}"

info()  { echo -e "\033[0;36m[INFO]\033[0m $*"; }
ok()    { echo -e "\033[0;32m[ OK ]\033[0m $*"; }
warn()  { echo -e "\033[1;33m[WARN]\033[0m $*"; }
error() { echo -e "\033[0;31m[ERR ]\033[0m $*" >&2; exit 1; }

fix_scripts() {
  local f
  for f in update.sh linux-deploy.sh deploy.sh; do
    [[ -f "$ROOT/$f" ]] || continue
    if grep -q $'\r' "$ROOT/$f" 2>/dev/null; then
      warn "修复 $f 的 Windows 换行(CRLF)..."
      sed -i 's/\r$//' "$ROOT/$f"
    fi
    chmod +x "$ROOT/$f" 2>/dev/null || true
  done
}

ensure_git_safe_directory() {
  # root / jenkins 用户操作 ubuntu 拥有的目录时，Git 2.35+ 会拒绝（dubious ownership）
  git config --global --add safe.directory "$ROOT" 2>/dev/null || true
}

pull_latest() {
  [[ -d "$ROOT/.git" ]] || error "当前目录不是 git 仓库，无法拉取代码"

  ensure_git_safe_directory
  info "拉取 GitHub 最新代码..."
  if git pull --ff-only 2>/dev/null; then
    ok "代码已更新: $(git log -1 --oneline)"
    return 0
  fi

  warn "git pull 失败，尝试丢弃部署脚本的本地修改后重试..."
  git checkout -- linux-deploy.sh update.sh deploy.sh 2>/dev/null || true
  git pull --ff-only || error "git pull 仍失败。若为 dubious ownership，请执行: git config --global --add safe.directory $ROOT"
  ok "代码已更新: $(git log -1 --oneline)"
}

deploy_docker() {
  [[ -f "$ENV_FILE" ]] || error "缺少 $ENV_FILE，请先: cp .env.docker.example .env.docker"

  if [[ -x "$ROOT/linux-deploy.sh" ]] || [[ -f "$ROOT/linux-deploy.sh" ]]; then
    info "使用 linux-deploy.sh 重新部署..."
    if bash "$ROOT/linux-deploy.sh" help 2>/dev/null | grep -qE 'update|pull'; then
      bash "$ROOT/linux-deploy.sh" update
      return 0
    fi
    bash "$ROOT/linux-deploy.sh" up
    return 0
  fi

  command -v docker >/dev/null 2>&1 || error "未安装 Docker"
  docker compose version >/dev/null 2>&1 || error "未安装 docker compose"

  info "重新构建并启动 Docker 服务..."
  docker compose --env-file "$ENV_FILE" -f "$ROOT/docker-compose.yml" up -d --build

  info "等待后端就绪..."
  local i url
  url="http://127.0.0.1:8000/health"
  for i in $(seq 1 90); do
    if curl -sf "$url" >/dev/null 2>&1; then
      ok "更新完成，后端已就绪"
      docker compose --env-file "$ENV_FILE" -f "$ROOT/docker-compose.yml" ps
      return 0
    fi
    sleep 2
  done
  error "后端启动超时，请查看: docker logs ai-platform-backend --tail=50"
}

main() {
  echo "========================================"
  echo "  AI质量平台 - 一键更新"
  echo "========================================"
  fix_scripts
  pull_latest
  deploy_docker
  echo "========================================"
}

main "$@"
