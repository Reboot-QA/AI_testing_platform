#!/usr/bin/env bash
# AI质量平台 - 一键部署/启动脚本（前后端）
# 用法:
#   ./deploy.sh          安装依赖并启动开发环境
#   ./deploy.sh install  仅安装依赖
#   ./deploy.sh start    启动前后端
#   ./deploy.sh stop     停止前后端
#   ./deploy.sh restart  重启
#   ./deploy.sh status   查看运行状态
#   ./deploy.sh ensure   检测并自动拉起已挂掉的服务
#   ./deploy.sh logs     查看最近日志
#   ./deploy.sh prod     构建前端并以生产模式启动后端
#   ./deploy.sh update   从 Git 仓库拉取最新代码并更新依赖
#   ./deploy.sh clone [目录]  首次部署：克隆仓库到指定目录
#   ./deploy.sh monitoring start  启动 Grafana + Loki 监控栈
#   ./linux-deploy.sh             Linux Docker 一键部署（推荐）
#   ./deploy.sh docker up         同上（别名）

set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
GIT_REPO_URL="${GIT_REPO_URL:-https://github.com/Reboot-QA/AI_testing_platform.git}"
BACKEND_DIR="$ROOT/backend"
FRONTEND_DIR="$ROOT/frontend"
VENV_DIR="$BACKEND_DIR/venv"
RUN_DIR="$ROOT/.deploy"
LOG_DIR="$RUN_DIR/logs"
PID_DIR="$RUN_DIR/pids"
BACKEND_PID_FILE="$PID_DIR/backend.pid"
FRONTEND_PID_FILE="$PID_DIR/frontend.pid"
BACKEND_LOG="$LOG_DIR/backend.log"
FRONTEND_LOG="$LOG_DIR/frontend.log"

BACKEND_HOST="${BACKEND_HOST:-0.0.0.0}"
BACKEND_PORT="${BACKEND_PORT:-8000}"
FRONTEND_HOST="${FRONTEND_HOST:-0.0.0.0}"
FRONTEND_PORT="${FRONTEND_PORT:-5173}"
PUBLIC_HOST="${PUBLIC_HOST:-}"

MONITORING_DIR="$ROOT/monitoring"
GRAFANA_PORT="${GRAFANA_PORT:-3000}"
LOKI_PORT="${LOKI_PORT:-3100}"
GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
GRAFANA_ADMIN_PASSWORD="${GRAFANA_ADMIN_PASSWORD:-change-me-grafana-password}"

# 运行时 Python（优先使用 backend/venv）
PYTHON=""

run_pip() {
  local py="${PYTHON}"
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    py="$VENV_DIR/bin/python"
  fi
  if [[ -x "$VENV_DIR/bin/pip" ]]; then
    "$VENV_DIR/bin/pip" "$@"
  else
    "$py" -m pip "$@"
  fi
}

bootstrap_venv_pip() {
  PYTHON="$VENV_DIR/bin/python"
  if [[ -x "$VENV_DIR/bin/pip" ]]; then
    return 0
  fi
  if "$PYTHON" -m pip --version >/dev/null 2>&1; then
    return 0
  fi
  info "venv 中缺少 pip，正在 bootstrap..."
  if ! "$PYTHON" -m ensurepip --upgrade >/dev/null 2>&1; then
    error "无法安装 pip，请执行:"
    error "  apt install -y python3-pip python3.12-venv"
    error "  rm -rf backend/venv && ./deploy.sh"
    exit 1
  fi
  ok "pip 已就绪: $(run_pip --version 2>&1 | head -1)"
}

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

info()  { echo -e "${CYAN}[INFO]${NC} $*"; }
ok()    { echo -e "${GREEN}[ OK ]${NC} $*"; }
warn()  { echo -e "${YELLOW}[WARN]${NC} $*"; }
error() { echo -e "${RED}[ERR ]${NC} $*" >&2; }

bootstrap_deploy() {
  if grep -q $'\r' "$0" 2>/dev/null; then
    echo "[ERR] deploy.sh 含有 Windows 换行(CRLF)，Linux 无法执行。" >&2
    echo "  修复: sed -i 's/\\r$//' deploy.sh && chmod +x deploy.sh" >&2
    exit 1
  fi
  info "deploy.sh 开始执行 (命令: ${1:-start})"
}

usage() {
  cat <<EOF
AI质量平台 - 一键部署脚本

用法: $0 [命令]

命令:
  (无) / start    安装依赖（如需）并启动前后端开发服务
  install         仅安装前后端依赖
  stop            停止前后端服务
  restart         重启前后端服务
  status          查看服务状态
  ensure          检测服务，挂掉则自动重启（可配合 cron 定时执行）
  logs [行数]     查看前后端最近日志 (默认 50 行)
  prod            构建前端 + 生产模式启动后端
  update          从仓库拉取最新代码、更新依赖（若服务在运行则自动重启）
  app-rebuild     重建并重启 Docker 版 backend + frontend（自动加载 .env.docker）
  clone [目录]    首次部署：克隆仓库（默认 ../AI_testing_platform）
  monitoring      Grafana + Loki 监控栈 (start|stop|restart|recreate-grafana|fix-auth|fix-logs|fix-dashboard|status|logs|debug)
  docker [子命令]   Docker Compose 部署 (up|down|restart|status|logs|build)

环境变量:
  BACKEND_HOST    后端监听地址 (默认 0.0.0.0)
  BACKEND_PORT    后端端口 (默认 8000)
  FRONTEND_PORT   前端端口 (默认 5173)
  FRONTEND_HOST   前端监听地址 (默认 0.0.0.0)
  PUBLIC_HOST     外网访问地址 (默认自动检测公网 IP，可手动指定)
  DEV_RELOAD      设为 1 时后端启用 --reload（Linux 服务器建议保持 0）
  USE_DOCKER_MYSQL  设为 0 时 deploy.sh 不自动同步/启动 Docker MySQL
  SKIP_MYSQL_CHECK  设为 1 时跳过后端启动前的 MySQL 连接检查
  SKIP_FRONTEND     设为 1 时仅部署后端（无需 Node.js）
  GIT_REPO_URL    Git 仓库地址 (默认 $GIT_REPO_URL)
  GIT_BRANCH      拉取分支 (默认当前分支，否则 main)
  GRAFANA_PORT    Grafana 端口 (默认 3000)
  LOKI_PORT       Loki 端口 (默认 3100)

首次部署示例:
  # 推荐：一键安装脚本（Linux 服务器）
  curl -fsSL https://raw.githubusercontent.com/Reboot-QA/AI_testing_platform/main/install-server.sh | bash
  PUBLIC_HOST=你的公网IP INSTALL_DIR=/opt/AI_testing_platform ./install-server.sh

  git clone $GIT_REPO_URL
  cd AI_testing_platform && ./deploy.sh

  # 或使用 clone 子命令
  ./deploy.sh clone /opt/AI_testing_platform
  cd /opt/AI_testing_platform && ./deploy.sh

访问地址:
  前端  http://127.0.0.1:${FRONTEND_PORT}
  后端  http://127.0.0.1:${BACKEND_PORT}
  文档  http://127.0.0.1:${BACKEND_PORT}/docs
  账号  admin / admin123
EOF
}

is_private_ip() {
  local ip="$1"
  [[ "$ip" =~ ^127\. ]] && return 0
  [[ "$ip" =~ ^10\. ]] && return 0
  [[ "$ip" =~ ^192\.168\. ]] && return 0
  [[ "$ip" =~ ^172\.(1[6-9]|2[0-9]|3[0-1])\. ]] && return 0
  [[ "$ip" =~ ^169\.254\. ]] && return 0
  return 1
}

detect_public_ip() {
  local ip url
  if command -v curl >/dev/null 2>&1; then
    for url in "https://api.ipify.org" "https://ifconfig.me/ip" "http://icanhazip.com"; do
      ip="$(curl -fsS --max-time 3 "$url" 2>/dev/null | tr -d '[:space:]')"
      if [[ "$ip" =~ ^[0-9]+\.[0-9]+\.[0-9]+\.[0-9]+$ ]] && ! is_private_ip "$ip"; then
        echo "$ip"
        return 0
      fi
    done
  fi
  return 1
}

detect_lan_ip() {
  local ip candidate
  if command -v hostname >/dev/null 2>&1; then
    for candidate in $(hostname -I 2>/dev/null); do
      candidate="${candidate%%/*}"
      [[ -z "$candidate" || "$candidate" == "127.0.0.1" ]] && continue
      echo "$candidate"
      return 0
    done
  fi
  if command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="src") { print $(i+1); exit }}')"
    if [[ -n "$ip" && "$ip" != "127.0.0.1" ]]; then
      echo "$ip"
      return 0
    fi
  fi
  return 1
}

detect_public_host() {
  if [[ -n "$PUBLIC_HOST" ]]; then
    echo "$PUBLIC_HOST"
    return 0
  fi
  detect_public_ip
}

detect_access_host() {
  local host
  host="$(detect_public_host 2>/dev/null || true)"
  if [[ -n "$host" ]]; then
    echo "$host"
    return 0
  fi
  host="$(detect_lan_ip 2>/dev/null || true)"
  echo "${host:-127.0.0.1}"
}

print_host_urls() {
  local label="$1"
  local host="$2"
  echo "  ${label}:"
  echo "    前端  http://${host}:${FRONTEND_PORT}"
  echo "    后端  http://${host}:${BACKEND_PORT}"
  echo "    文档  http://${host}:${BACKEND_PORT}/docs"
}

print_access_urls() {
  local public_host lan_host
  public_host="$(detect_public_host 2>/dev/null || true)"
  lan_host="$(detect_lan_ip 2>/dev/null || true)"

  echo "  本机访问:"
  echo "    前端  http://127.0.0.1:${FRONTEND_PORT}"
  echo "    后端  http://127.0.0.1:${BACKEND_PORT}"

  if [[ -n "$public_host" ]]; then
    print_host_urls "公网访问" "$public_host"
  fi

  if [[ -n "$lan_host" && "$lan_host" != "$public_host" ]]; then
    print_host_urls "局域网访问" "$lan_host"
  elif [[ -z "$public_host" && -n "$lan_host" ]]; then
    print_host_urls "局域网访问" "$lan_host"
  fi

  if [[ -z "$public_host" && -z "$lan_host" ]]; then
    warn "未能自动检测公网 IP，请手动指定: PUBLIC_HOST=你的公网IP ./deploy.sh restart"
  fi
}

print_firewall_hint() {
  if [[ "$(detect_access_host)" == "127.0.0.1" ]]; then
    return
  fi
  warn "若外网无法打开页面，请检查云服务器安全组是否放行端口 ${FRONTEND_PORT}、${BACKEND_PORT}"
}

pids_on_port() {
  local port="$1"
  if command -v lsof >/dev/null 2>&1; then
    lsof -ti :"$port" 2>/dev/null || true
    return
  fi
  if command -v fuser >/dev/null 2>&1; then
    fuser "${port}/tcp" 2>/dev/null | tr ' ' '\n' | grep -E '^[0-9]+$' || true
    return
  fi
  if command -v ss >/dev/null 2>&1; then
    ss -tlnp 2>/dev/null | grep -E ":${port}([[:space:]]|$)" \
      | sed -n 's/.*pid=\([0-9]*\).*/\1/p' | sort -u || true
  fi
}

port_listening() {
  local port="$1"
  if command -v ss >/dev/null 2>&1; then
    ss -tln 2>/dev/null | grep -qE ":${port}([[:space:]]|$)"
    return $?
  fi
  if command -v netstat >/dev/null 2>&1; then
    netstat -tln 2>/dev/null | grep -qE ":${port}([[:space:]]|$)"
    return $?
  fi
  [[ -n "$(pids_on_port "$port")" ]]
}

free_port() {
  local port="$1"
  local name="$2"
  local pids
  pids="$(pids_on_port "$port" | tr '\n' ' ' | xargs echo -n 2>/dev/null || true)"
  if [[ -z "$pids" ]]; then
    return 0
  fi
  warn "端口 ${port} 已被占用 (${name})，正在释放进程: ${pids}"
  local pid
  for pid in $pids; do
    kill "$pid" 2>/dev/null || kill -9 "$pid" 2>/dev/null || true
  done
  sleep 1
}

wait_frontend() {
  local url="http://127.0.0.1:${FRONTEND_PORT}/"
  info "等待前端就绪..."
  for _ in $(seq 1 30); do
    if ! is_running "$FRONTEND_PID_FILE"; then
      error "前端进程已退出，请查看日志: $FRONTEND_LOG"
      tail -30 "$FRONTEND_LOG" 2>/dev/null >&2 || true
      return 1
    fi
    if port_listening "$FRONTEND_PORT"; then
      if command -v curl >/dev/null 2>&1 && curl -sf "$url" >/dev/null 2>&1; then
        ok "前端已就绪 (监听 ${FRONTEND_HOST}:${FRONTEND_PORT})"
        return 0
      fi
      ok "前端端口 ${FRONTEND_PORT} 已监听"
      return 0
    fi
    sleep 1
  done
  warn "前端启动超时，请查看日志: $FRONTEND_LOG"
  tail -30 "$FRONTEND_LOG" 2>/dev/null >&2 || true
  return 1
}

require_cmd() {
  if ! command -v "$1" >/dev/null 2>&1; then
    error "未找到命令: $1"
    exit 1
  fi
}

require_git() {
  require_cmd git
}

detect_git_branch() {
  if [[ -n "${GIT_BRANCH:-}" ]]; then
    echo "$GIT_BRANCH"
    return
  fi
  if [[ -d "$ROOT/.git" ]]; then
    local current
    current="$(git -C "$ROOT" rev-parse --abbrev-ref HEAD 2>/dev/null || true)"
    if [[ -n "$current" && "$current" != "HEAD" ]]; then
      echo "$current"
      return
    fi
  fi
  echo "main"
}

ensure_git_remote() {
  cd "$ROOT"
  if [[ ! -d .git ]]; then
    return 1
  fi
  if ! git remote get-url origin >/dev/null 2>&1; then
    info "添加 origin 远程: $GIT_REPO_URL"
    git remote add origin "$GIT_REPO_URL"
  fi
}

pull_latest() {
  require_git
  cd "$ROOT"
  if [[ ! -d .git ]]; then
    error "当前目录不是 Git 仓库"
    error "首次部署: git clone $GIT_REPO_URL && cd AI_testing_platform && ./deploy.sh"
    error "或执行: ./deploy.sh clone [目标目录]"
    exit 1
  fi
  ensure_git_remote || true

  local branch
  branch="$(detect_git_branch)"
  info "从仓库拉取最新代码"
  info "  仓库: $GIT_REPO_URL"
  info "  分支: $branch"

  if [[ -n "$(git status --porcelain 2>/dev/null | grep -v '^??')" ]]; then
    warn "检测到已跟踪文件的本地修改，拉取可能产生冲突"
  fi

  git fetch origin "$branch" || {
    error "git fetch 失败，请检查网络与仓库权限"
    exit 1
  }

  if ! git rev-parse "origin/$branch" >/dev/null 2>&1; then
    error "远程分支 origin/$branch 不存在"
    error "可指定分支: GIT_BRANCH=main ./deploy.sh update"
    exit 1
  fi

  local local_ref remote_ref
  local_ref="$(git rev-parse HEAD)"
  remote_ref="$(git rev-parse "origin/$branch")"

  if [[ "$local_ref" == "$remote_ref" ]]; then
    ok "代码已是最新 ($(git rev-parse --short HEAD))"
    return 0
  fi

  git merge-base --is-ancestor "$local_ref" "$remote_ref" 2>/dev/null || {
    error "本地分支与远程存在分叉，无法快进合并"
    error "请手动处理: git status && git pull origin $branch"
    exit 1
  }

  preserve_local_database_for_pull

  git merge --ff-only "$remote_ref" || {
    error "拉取失败，请手动解决后重试"
    exit 1
  }
  restore_local_database_after_pull
  ok "代码已更新: $(git log -1 --oneline)"
}

preserve_local_database_for_pull() {
  local env_file="$ROOT/backend/.env"
  if [[ -f "$env_file" ]] && grep -qE '^DATABASE_URL=.*mysql' "$env_file" 2>/dev/null; then
    return 0
  fi
  if [[ -f "$env_file" ]] && grep -qE '^DB_HOST=' "$env_file" 2>/dev/null; then
    return 0
  fi

  local db="$ROOT/backend/ai_testcase.db"
  local stash="$ROOT/.deploy/ai_testcase.db.pullbak"
  mkdir -p "$ROOT/.deploy"
  rm -f "$stash"

  if [[ ! -f "$db" ]]; then
    return 0
  fi

  if git ls-files --error-unmatch backend/ai_testcase.db >/dev/null 2>&1 \
    && ! git diff --quiet HEAD -- backend/ai_testcase.db 2>/dev/null; then
    warn "检测到本地数据库变更，更新时将保留本地数据"
    cp "$db" "$stash"
    git checkout HEAD -- backend/ai_testcase.db 2>/dev/null \
      || git restore --source=HEAD -- backend/ai_testcase.db 2>/dev/null \
      || true
  fi
}

restore_local_database_after_pull() {
  local env_file="$ROOT/backend/.env"
  if [[ -f "$env_file" ]] && grep -qE '^DATABASE_URL=.*mysql' "$env_file" 2>/dev/null; then
    return 0
  fi
  if [[ -f "$env_file" ]] && grep -qE '^DB_HOST=' "$env_file" 2>/dev/null; then
    return 0
  fi

  local db="$ROOT/backend/ai_testcase.db"
  local stash="$ROOT/.deploy/ai_testcase.db.pullbak"

  if [[ -f "$stash" ]]; then
    mv "$stash" "$db"
    ok "已恢复本地数据库"
  fi
}

clone_project() {
  local target="${1:-}"
  require_git

  local branch repo_name
  branch="$(detect_git_branch)"
  repo_name="$(basename "${GIT_REPO_URL%.git}")"

  if [[ -z "$target" ]]; then
    target="$(cd "$ROOT/.." && pwd)/$repo_name"
  elif [[ "$target" != /* ]]; then
    target="$(cd "$ROOT" && pwd)/$target"
  fi

  if [[ -d "$target/.git" ]]; then
    warn "目标已是 Git 仓库: $target"
    info "进入目录后执行: cd $target && ./deploy.sh update"
    return 0
  fi

  if [[ -e "$target" && -n "$(ls -A "$target" 2>/dev/null)" ]]; then
    error "目标目录非空: $target"
    exit 1
  fi

  mkdir -p "$(dirname "$target")"
  info "克隆仓库 $GIT_REPO_URL (分支: $branch) -> $target"
  git clone -b "$branch" "$GIT_REPO_URL" "$target"
  ok "克隆完成"
  cat <<EOF

下一步:
  cd $target
  ./deploy.sh

EOF
}

update_project() {
  local was_backend=0 was_frontend=0
  prepare_dirs
  if is_running "$BACKEND_PID_FILE"; then was_backend=1; fi
  if is_running "$FRONTEND_PID_FILE"; then was_frontend=1; fi

  if [[ "$was_backend" == "1" || "$was_frontend" == "1" ]]; then
    info "更新前停止运行中的服务..."
    stop_all
  fi

  pull_latest
  install_all

  if [[ "$was_backend" == "1" || "$was_frontend" == "1" ]]; then
    info "重新启动服务..."
    start_backend
    start_frontend_dev
    print_banner
  else
    ok "更新完成（服务未在运行）。启动请执行: ./deploy.sh start"
  fi
}

detect_node() {
  # 扩展 PATH（nvm、NodeSource 常见路径）
  local nvm_node=""
  if [[ -d "${HOME}/.nvm/versions/node" ]]; then
    nvm_node="$(ls "${HOME}/.nvm/versions/node" 2>/dev/null | tail -1 || true)"
  fi
  if [[ -n "$nvm_node" ]]; then
    export PATH="${HOME}/.nvm/versions/node/${nvm_node}/bin:/usr/local/bin:/usr/bin:/bin:${PATH}"
  else
    export PATH="/usr/local/bin:/usr/bin:/bin:${PATH}"
  fi

  if [[ -n "${NODE_BIN_DIR:-}" && -x "${NODE_BIN_DIR}/node" ]]; then
    export PATH="${NODE_BIN_DIR}:${PATH}"
  fi

  if command -v node >/dev/null 2>&1; then
    if command -v npm >/dev/null 2>&1; then
      ok "Node $(node -v) | npm $(npm -v)"
      return 0
    fi
    warn "已找到 node（$(node -v)），但未找到 npm"
    error "请安装 npm: apt install -y npm   或重新安装 nodejs 包"
    exit 1
  fi

  # 仅加载 nvm（勿 source .bashrc/.profile，set -e 下失败会被静默吞掉）
  local nvm_sh
  for nvm_sh in "${NVM_DIR:-$HOME/.nvm}/nvm.sh" "/root/.nvm/nvm.sh"; do
    if [[ -s "$nvm_sh" ]]; then
      set +e
      # shellcheck source=/dev/null
      source "$nvm_sh"
      local source_status=$?
      set -e
      if (( source_status != 0 )); then
        warn "加载 nvm 失败: $nvm_sh (exit $source_status)"
        continue
      fi
      if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        ok "已加载 nvm: Node $(node -v) | npm $(npm -v)"
        return 0
      fi
    fi
  done

  # 扫描常见安装路径
  local p
  for p in /usr/local/bin/node /usr/bin/node /opt/nodejs/bin/node; do
    if [[ -x "$p" ]]; then
      export PATH="$(dirname "$p"):${PATH}"
      if command -v npm >/dev/null 2>&1; then
        ok "Node $(node -v) | npm $(npm -v)"
        return 0
      fi
    fi
  done

  error "脚本未找到 node 命令（当前 shell 的 PATH 可能与交互式终端不同）"
  warn "诊断信息: PATH=$PATH"
  warn "请在本终端执行: which node && which npm && node -v && npm -v"
  cat <<'EOF' >&2

若 node -v 在终端可用但 deploy.sh 仍报错，请指定路径后重试：
  export NODE_BIN_DIR=$(dirname "$(which node)")
  ./deploy.sh

或先加载 nvm 再执行：
  source ~/.nvm/nvm.sh   # 或 source ~/.bashrc
  ./deploy.sh

缺少 npm 时：
  sudo apt install -y npm

仅部署后端（跳过 Node）：
  SKIP_FRONTEND=1 ./deploy.sh
EOF
  exit 1
}

detect_python() {
  local py=""
  # 优先使用较新的 Python（避免系统默认 python3 为 3.6/3.7）
  for candidate in python3.12 python3.11 python3.10 python3.9 python3.8 python3 python; do
    if command -v "$candidate" >/dev/null 2>&1; then
      py="$candidate"
      break
    fi
  done
  if [[ -z "$py" ]]; then
    error "未找到 Python，请安装 Python 3.8+:"
    error "  apt install python3.10 python3.10-venv python3-pip"
    exit 1
  fi

  PYTHON="$py"
  if [[ -x "$VENV_DIR/bin/python" ]]; then
    PYTHON="$VENV_DIR/bin/python"
    return 0
  fi
}

check_python_version() {
  local py_bin="$1"
  local ver major minor
  ver="$("$py_bin" -c 'import sys; print(f"{sys.version_info.major}.{sys.version_info.minor}")')"
  major="${ver%%.*}"
  minor="${ver##*.}"
  if (( major < 3 || (major == 3 && minor < 8) )); then
    error "Python 版本过低: $("$py_bin" --version 2>&1)"
    error "本项目需要 Python 3.8 及以上（推荐 3.10 / 3.11）"
    cat <<'EOF' >&2

安装 Python 3.10（Ubuntu/Debian）:
  sudo apt update
  sudo apt install -y python3.10 python3.10-venv python3-pip

安装 Python 3.10（CentOS 7/8）:
  sudo yum install -y python3.11 python3.11-pip
  # 或启用 EPEL 后安装 python3.11

验证:
  python3.10 --version
  rm -rf backend/venv && ./deploy.sh
EOF
    exit 1
  fi
}

ensure_backend_venv() {
  detect_python
  check_python_version "$PYTHON"

  if [[ -x "$VENV_DIR/bin/python" ]]; then
    if ! "$VENV_DIR/bin/python" -c 'import sys; exit(0 if sys.version_info >= (3, 8) else 1)' 2>/dev/null; then
      warn "检测到旧版 venv（Python < 3.8），正在重建..."
      rm -rf "$VENV_DIR"
    fi
  fi

  if [[ -x "$VENV_DIR/bin/python" ]]; then
    bootstrap_venv_pip
    return 0
  fi

  info "创建 Python 虚拟环境 backend/venv （$("$PYTHON" --version 2>&1)）..."
  if ! "$PYTHON" -m venv "$VENV_DIR" 2>/dev/null; then
    error "创建虚拟环境失败，请安装: apt install python3.12-venv python3-pip"
    exit 1
  fi
  bootstrap_venv_pip
  PYTHON="$VENV_DIR/bin/python"
  check_python_version "$PYTHON"
  run_pip install -q --upgrade pip setuptools wheel
}

pip_install_requirements() {
  local index="${PIP_INDEX_URL:-https://pypi.org/simple}"
  local mirror="https://pypi.tuna.tsinghua.edu.cn/simple"

  info "升级 pip 并安装后端依赖..."
  bootstrap_venv_pip
  run_pip install -q --upgrade pip setuptools wheel

  if run_pip install -r requirements.txt -q -i "$index"; then
    return 0
  fi

  warn "默认源安装失败，尝试清华镜像..."
  if run_pip install -r requirements.txt -q -i "$mirror"; then
    return 0
  fi

  error "依赖安装失败，请确认 Python >= 3.8: $("$PYTHON" --version 2>&1)"
  error "手动调试: cd backend && source venv/bin/activate && python -m pip install -r requirements.txt -v"
  exit 1
}

sync_db_env_from_docker() {
  local docker_env="$ROOT/.env.docker"
  [[ -f "$docker_env" ]] || return 0
  [[ "${USE_DOCKER_MYSQL:-1}" == "0" ]] && return 0

  detect_python
  ensure_backend_venv
  "$PYTHON" - <<PY
from pathlib import Path

root = Path(${ROOT@Q})
docker_file = root / ".env.docker"
backend_env_path = root / "backend" / ".env"

docker_env = {}
for line in docker_file.read_text(encoding="utf-8").splitlines():
    line = line.strip()
    if not line or line.startswith("#") or "=" not in line:
        continue
    key, value = line.split("=", 1)
    docker_env[key.strip()] = value.strip()

if not backend_env_path.exists():
    backend_env_path.write_text(
        (root / "backend" / ".env.example").read_text(encoding="utf-8"),
        encoding="utf-8",
    )

updates = {
    "DB_HOST": "127.0.0.1",
    "DB_PORT": docker_env.get("MYSQL_PORT", "3306"),
    "DB_USER": docker_env.get("DB_USER", "ai_testcase"),
    "DB_PASSWORD": docker_env.get("DB_PASSWORD", ""),
    "DB_NAME": docker_env.get("DB_NAME", "ai_testcase"),
}

lines = backend_env_path.read_text(encoding="utf-8").splitlines()
seen = set()
out = []
for line in lines:
    if "=" in line and not line.lstrip().startswith("#"):
        key = line.split("=", 1)[0].strip()
        if key in updates:
            out.append(f"{key}={updates[key]}")
            seen.add(key)
            continue
    out.append(line)
for key, value in updates.items():
    if key not in seen:
        out.append(f"{key}={value}")
backend_env_path.write_text("\\n".join(out) + "\\n", encoding="utf-8")
PY
  info "已从 .env.docker 同步 MySQL 配置到 backend/.env"
}

test_mysql_connection() {
  detect_python
  ensure_backend_venv
  cd "$BACKEND_DIR"
  "$PYTHON" - <<'PY'
from pathlib import Path
import pymysql
import sys

def load_env(path: Path) -> dict:
    data = {}
    if not path.exists():
        return data
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        data[key.strip()] = value.strip()
    return data

env = load_env(Path(".env"))
try:
    conn = pymysql.connect(
        host=env.get("DB_HOST", "127.0.0.1"),
        port=int(env.get("DB_PORT", "3306")),
        user=env.get("DB_USER", "root"),
        password=env.get("DB_PASSWORD", ""),
        database=env.get("DB_NAME", "ai_testcase"),
        charset="utf8mb4",
        connect_timeout=3,
    )
    conn.close()
except Exception as exc:
    print(exc, file=sys.stderr)
    raise SystemExit(1)
raise SystemExit(0)
PY
}

start_docker_mysql_if_needed() {
  local docker_env="$ROOT/.env.docker"
  [[ -f "$docker_env" ]] || return 1
  [[ "${USE_DOCKER_MYSQL:-1}" == "0" ]] && return 1
  command -v docker >/dev/null 2>&1 || return 1
  docker compose version >/dev/null 2>&1 || return 1
  [[ -f "$ROOT/docker-compose.yml" ]] || return 1

  info "MySQL 未就绪，正在启动 Docker MySQL 容器..."
  app_compose up -d mysql

  local i
  for i in $(seq 1 60); do
    if app_compose ps mysql 2>/dev/null | grep -q "(healthy)"; then
      ok "Docker MySQL 已就绪"
      return 0
    fi
    sleep 2
  done
  warn "Docker MySQL 启动超时"
  return 1
}

ensure_app_env() {
  local docker_env="$ROOT/.env.docker"
  if [[ ! -f "$docker_env" ]]; then
    error "缺少 $docker_env"
    echo "  首次 Docker 部署请执行: ./linux-deploy.sh init-env && ./linux-deploy.sh up"
    exit 1
  fi
  local missing=()
  for key in MYSQL_ROOT_PASSWORD DB_PASSWORD SECRET_KEY; do
    local val
    val="$(grep -E "^${key}=" "$docker_env" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
    if [[ -z "$val" ]]; then
      missing+=("$key")
    fi
  done
  if ((${#missing[@]} > 0)); then
    error ".env.docker 缺少必填项: ${missing[*]}"
    echo "  请执行: ./linux-deploy.sh init-env"
    echo "  若 MySQL 已在运行且密码不同，请手动编辑 .env.docker 后重试"
    exit 1
  fi
}

app_compose() {
  ensure_app_env
  BUILDX_NO_DEFAULT_ATTESTATIONS=1 docker compose --env-file "$ROOT/.env.docker" -f "$ROOT/docker-compose.yml" "$@"
}

app_rebuild() {
  require_docker
  info "重建 backend + frontend（使用 .env.docker）..."
  export BUILDX_NO_DEFAULT_ATTESTATIONS=1
  export BUILDKIT_PROGRESS=plain
  if ! app_compose build --provenance=false --sbom=false --progress=plain backend frontend; then
    warn "BuildKit 构建失败，改用 DOCKER_BUILDKIT=0..."
    DOCKER_BUILDKIT=0 app_compose build --progress=plain backend frontend
  fi
  app_compose up -d backend frontend
  ok "应用已重建并启动"
}

ensure_mysql_ready() {
  [[ "${SKIP_MYSQL_CHECK:-0}" == "1" ]] && return 0

  sync_db_env_from_docker

  if test_mysql_connection 2>/dev/null; then
    ok "MySQL 连接正常"
    return 0
  fi

  if start_docker_mysql_if_needed; then
    sync_db_env_from_docker
    if test_mysql_connection; then
      ok "MySQL 连接正常（Docker）"
      return 0
    fi
  fi

  error "无法连接 MySQL，后端未启动"
  cat <<'EOF' >&2

修复方式（任选其一）：
  1) Docker 全栈:     bash docker/deploy.sh up
  2) 自动 Docker MySQL: 配置 .env.docker 后直接 ./deploy.sh start（脚本会自动拉起 MySQL）
  3) 宿主机 MySQL:    apt install -y mysql-server && 配置 backend/.env
  4) 跳过检查:        SKIP_MYSQL_CHECK=1 ./deploy.sh start
EOF
  exit 1
}

check_prerequisites() {
  detect_python
  if [[ "${SKIP_FRONTEND:-0}" != "1" ]]; then
    detect_node
  else
    warn "SKIP_FRONTEND=1，跳过 Node.js 检查（仅部署后端）"
  fi

  local py_version
  py_version="$("$PYTHON" -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')"
  if [[ "${SKIP_FRONTEND:-0}" != "1" ]]; then
    info "Python $py_version ($PYTHON) | Node $(node -v) | npm $(npm -v)"
  else
    info "Python $py_version ($PYTHON) | 前端已跳过"
  fi
}

prepare_dirs() {
  mkdir -p "$LOG_DIR" "$PID_DIR"
}

append_log_marker() {
  local name="$1"
  local file="$2"
  mkdir -p "$(dirname "$file")"
  {
    echo ""
    echo "======== $(date '+%Y-%m-%d %H:%M:%S') [$name] 服务启动（追加日志，保留历史） ========"
  } >>"$file"
}

is_running() {
  local pid_file="$1"
  if [[ -f "$pid_file" ]]; then
    local pid
    pid="$(cat "$pid_file")"
    if kill -0 "$pid" 2>/dev/null; then
      return 0
    fi
    rm -f "$pid_file"
  fi
  return 1
}

kill_process_tree() {
  local pid="$1"
  local child
  for child in $(pgrep -P "$pid" 2>/dev/null || true); do
    kill_process_tree "$child"
  done
  kill "$pid" 2>/dev/null || true
}

backend_healthy() {
  is_running "$BACKEND_PID_FILE" || return 1
  port_listening "$BACKEND_PORT" || return 1
  if command -v curl >/dev/null 2>&1; then
    curl -sf "http://127.0.0.1:${BACKEND_PORT}/" >/dev/null 2>&1
    return $?
  fi
  return 0
}

frontend_healthy() {
  is_running "$FRONTEND_PID_FILE" || return 1
  port_listening "$FRONTEND_PORT"
}

show_log_tail() {
  local name="$1"
  local file="$2"
  local lines="${3:-20}"
  if [[ -f "$file" ]]; then
    echo "--- ${name} (最近 ${lines} 行: ${file}) ---"
    tail -n "$lines" "$file" 2>/dev/null || true
    echo
  fi
}

stop_pid_file() {
  local name="$1"
  local pid_file="$2"
  if is_running "$pid_file"; then
    local pid
    pid="$(cat "$pid_file")"
    info "停止 $name (PID $pid)..."
    kill_process_tree "$pid"
    for _ in $(seq 1 10); do
      kill -0 "$pid" 2>/dev/null || break
      sleep 0.5
    done
    if kill -0 "$pid" 2>/dev/null; then
      warn "强制结束 $name (PID $pid)"
      kill -9 "$pid" 2>/dev/null || true
    fi
    ok "$name 已停止"
  fi
  rm -f "$pid_file"
}

install_backend() {
  info "[1/2] 安装后端依赖..."
  ensure_backend_venv
  cd "$BACKEND_DIR"
  if [[ ! -f .env ]]; then
    cp .env.example .env
    warn "已创建 backend/.env，请按需配置 LLM 等参数"
  fi
  sync_db_env_from_docker
  pip_install_requirements
  ok "后端依赖就绪 (venv: $VENV_DIR, $($PYTHON --version 2>&1))"
}

install_frontend() {
  if [[ "${SKIP_FRONTEND:-0}" == "1" ]]; then
    warn "SKIP_FRONTEND=1，跳过前端依赖安装"
    return 0
  fi
  info "[2/2] 安装前端依赖..."
  cd "$FRONTEND_DIR"
  if [[ ! -d node_modules ]]; then
    npm install
  else
    npm install --prefer-offline --no-audit --no-fund
  fi
  # 修复从 Windows 拷贝或 git 检出后 .bin 脚本无执行权限的问题
  if [[ -d node_modules/.bin ]]; then
    chmod +x node_modules/.bin/* 2>/dev/null || true
  fi
  ok "前端依赖就绪"
}

install_all() {
  check_prerequisites
  prepare_dirs
  install_backend
  install_frontend
}

wait_backend() {
  local url="http://127.0.0.1:${BACKEND_PORT}/"
  detect_python
  info "等待后端就绪..."
  for _ in $(seq 1 30); do
    if ! is_running "$BACKEND_PID_FILE"; then
      error "后端进程已退出，请查看日志: $BACKEND_LOG"
      tail -30 "$BACKEND_LOG" 2>/dev/null >&2 || true
      return 1
    fi
    if command -v curl >/dev/null 2>&1 && curl -sf "$url" >/dev/null 2>&1; then
      ok "后端已就绪"
      return 0
    fi
    if "$PYTHON" -c "
import urllib.request
urllib.request.urlopen('${url}', timeout=2)
" 2>/dev/null; then
      ok "后端已就绪"
      return 0
    fi
    sleep 1
  done
  warn "后端启动超时，请查看日志: $BACKEND_LOG"
  tail -30 "$BACKEND_LOG" 2>/dev/null >&2 || true
  return 1
}

start_backend() {
  if backend_healthy; then
    warn "后端已在运行 (PID $(cat "$BACKEND_PID_FILE"))"
    return 0
  fi
  if is_running "$BACKEND_PID_FILE"; then
    warn "后端 PID 存在但服务不可用，正在重启..."
    stop_pid_file "后端" "$BACKEND_PID_FILE"
  fi
  free_port "$BACKEND_PORT" "backend"
  ensure_backend_venv
  ensure_mysql_ready
  info "启动后端 http://${BACKEND_HOST}:${BACKEND_PORT} ..."
  cd "$BACKEND_DIR"
  local -a uvicorn_args=(
    -m uvicorn app.main:app
    --host "$BACKEND_HOST"
    --port "$BACKEND_PORT"
  )
  if [[ "${DEV_RELOAD:-0}" == "1" ]]; then
    uvicorn_args+=(--reload)
  fi
  append_log_marker "backend" "$BACKEND_LOG"
  nohup "$PYTHON" "${uvicorn_args[@]}" >>"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
  if ! wait_backend; then
    stop_pid_file "后端" "$BACKEND_PID_FILE"
    exit 1
  fi
}

start_frontend_dev() {
  if [[ "${SKIP_FRONTEND:-0}" == "1" ]]; then
    warn "SKIP_FRONTEND=1，跳过前端启动"
    return 0
  fi
  if frontend_healthy; then
    warn "前端已在运行 (PID $(cat "$FRONTEND_PID_FILE"))"
    return 0
  fi
  if is_running "$FRONTEND_PID_FILE"; then
    warn "前端 PID 存在但服务不可用，正在重启..."
    stop_pid_file "前端" "$FRONTEND_PID_FILE"
  fi
  free_port "$FRONTEND_PORT" "frontend"
  detect_node
  info "启动前端 ${FRONTEND_HOST}:${FRONTEND_PORT} ..."
  cd "$FRONTEND_DIR"
  local vite_js="node_modules/vite/bin/vite.js"
  if [[ ! -f "$vite_js" ]]; then
    error "未找到 vite，请先执行: ./deploy.sh install"
    exit 1
  fi
  # 用 node 直接启动，避免 node_modules/.bin/vite 无执行权限 (Permission denied)
  append_log_marker "frontend" "$FRONTEND_LOG"
  nohup node "$vite_js" --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
    >>"$FRONTEND_LOG" 2>&1 &
  echo $! >"$FRONTEND_PID_FILE"
  if ! wait_frontend; then
    stop_pid_file "前端" "$FRONTEND_PID_FILE"
    exit 1
  fi
}

start_backend_prod() {
  if is_running "$BACKEND_PID_FILE"; then
    warn "后端已在运行 (PID $(cat "$BACKEND_PID_FILE"))"
    return 0
  fi
  free_port "$BACKEND_PORT" "backend"
  ensure_backend_venv
  ensure_mysql_ready
  info "生产模式启动后端..."
  cd "$BACKEND_DIR"
  append_log_marker "backend-prod" "$BACKEND_LOG"
  nohup "$PYTHON" -m uvicorn app.main:app \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    --workers 2 \
    >>"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
  wait_backend || true
}

build_frontend() {
  info "构建前端静态资源..."
  cd "$FRONTEND_DIR"
  detect_node
  local vite_js="node_modules/vite/bin/vite.js"
  if [[ ! -f "$vite_js" ]]; then
    npm install
  fi
  node "$vite_js" build
  ok "前端构建完成: frontend/dist"
}

start_prod() {
  install_all
  stop_all
  build_frontend
  start_backend_prod
  info "生产模式：请使用 Nginx 托管 frontend/dist，并将 /api 反代至 :${BACKEND_PORT}"
  info "本地预览前端: cd frontend && npm run preview -- --host 0.0.0.0 --port ${FRONTEND_PORT}"
}

start_dev() {
  install_all
  stop_all
  start_backend
  start_frontend_dev
  print_banner
}

stop_all() {
  stop_pid_file "前端" "$FRONTEND_PID_FILE"
  stop_pid_file "后端" "$BACKEND_PID_FILE"
  free_port "$FRONTEND_PORT" "frontend"
  free_port "$BACKEND_PORT" "backend"
}

show_status() {
  detect_python
  local public_host lan_host
  public_host="$(detect_public_host 2>/dev/null || true)"
  lan_host="$(detect_lan_ip 2>/dev/null || true)"
  echo "========================================"
  echo "  AI质量平台 - 服务状态"
  echo "========================================"
  if backend_healthy; then
    ok "后端运行中 PID=$(cat "$BACKEND_PID_FILE")"
    echo "       本机  http://127.0.0.1:${BACKEND_PORT}"
    [[ -n "$public_host" ]] && echo "       公网  http://${public_host}:${BACKEND_PORT}"
    [[ -n "$lan_host" && "$lan_host" != "$public_host" ]] && echo "       局域网 http://${lan_host}:${BACKEND_PORT}"
  elif port_listening "$BACKEND_PORT"; then
    warn "后端 PID 文件缺失，但端口 ${BACKEND_PORT} 仍被占用"
    echo "       占用进程: $(pids_on_port "$BACKEND_PORT" | tr '\n' ' ')"
  else
    warn "后端未运行"
    show_log_tail "后端" "$BACKEND_LOG" 10
  fi
  if frontend_healthy; then
    ok "前端运行中 PID=$(cat "$FRONTEND_PID_FILE")"
    echo "       本机  http://127.0.0.1:${FRONTEND_PORT}"
    [[ -n "$public_host" ]] && echo "       公网  http://${public_host}:${FRONTEND_PORT}"
    [[ -n "$lan_host" && "$lan_host" != "$public_host" ]] && echo "       局域网 http://${lan_host}:${FRONTEND_PORT}"
  elif port_listening "$FRONTEND_PORT"; then
    warn "前端 PID 文件缺失，但端口 ${FRONTEND_PORT} 仍被占用"
    echo "       占用进程: $(pids_on_port "$FRONTEND_PORT" | tr '\n' ' ')"
  else
    warn "前端未运行"
    show_log_tail "前端" "$FRONTEND_LOG" 10
  fi
  echo "Python: $PYTHON"
  echo "日志: $LOG_DIR"
  echo "恢复: ./deploy.sh restart  |  自动巡检: ./deploy.sh ensure"
}

show_logs() {
  local lines="${1:-50}"
  prepare_dirs
  show_log_tail "后端" "$BACKEND_LOG" "$lines"
  show_log_tail "前端" "$FRONTEND_LOG" "$lines"
}

ensure_services() {
  prepare_dirs
  local restarted=0

  if ! backend_healthy; then
    warn "后端未运行或不可用，正在拉起..."
    if is_running "$BACKEND_PID_FILE"; then
      stop_pid_file "后端" "$BACKEND_PID_FILE"
    fi
    free_port "$BACKEND_PORT" "backend"
    start_backend
    restarted=1
  fi

  if [[ "${SKIP_FRONTEND:-0}" != "1" ]] && ! frontend_healthy; then
    warn "前端未运行或不可用，正在拉起..."
    if is_running "$FRONTEND_PID_FILE"; then
      stop_pid_file "前端" "$FRONTEND_PID_FILE"
    fi
    free_port "$FRONTEND_PORT" "frontend"
    start_frontend_dev
    restarted=1
  fi

  if [[ "$restarted" == "0" ]]; then
    ok "前后端服务均正常"
  else
    ok "已尝试恢复异常服务"
  fi
  show_status
}

print_banner() {
  cat <<EOF

========================================
  部署完成！
EOF
  print_access_urls
  cat <<EOF
  账号:  admin / admin123
  停止:  ./deploy.sh stop
  状态:  ./deploy.sh status
  日志:  $LOG_DIR
========================================

EOF
  print_firewall_hint
}

require_docker() {
  if ! command -v docker >/dev/null 2>&1; then
    error "未找到 docker，请先安装 Docker: https://docs.docker.com/engine/install/"
    exit 1
  fi
  if ! docker compose version >/dev/null 2>&1; then
    error "未找到 docker compose 插件，请安装 Docker Compose v2"
    exit 1
  fi
  if ! docker info >/dev/null 2>&1; then
    error "Docker 守护进程未运行，请执行: sudo systemctl start docker"
    exit 1
  fi
}

monitoring_compose() {
  cd "$MONITORING_DIR"
  local files=(-f docker-compose.yml)
  if [[ -n "${DOCKER_APP_LOGS_VOLUME:-}" ]]; then
    files+=(-f docker-compose.docker-volume.yml)
  else
    files+=(-f docker-compose.host-logs.yml)
  fi
  docker compose "${files[@]}" "$@"
}

monitoring_has_running() {
  monitoring_compose ps --status running 2>/dev/null | grep -qE 'loki|grafana|promtail'
}

monitoring_sync_app_env() {
  local docker_env="$ROOT/.env.docker"
  [[ -f "$docker_env" ]] || return 0
  local val
  val="$(grep -E '^GRAFANA_ADMIN_PASSWORD=' "$docker_env" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  [[ -n "$val" ]] && export GRAFANA_ADMIN_PASSWORD="$val"
  val="$(grep -E '^GRAFANA_ADMIN_USER=' "$docker_env" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  [[ -n "$val" ]] && export GRAFANA_ADMIN_USER="$val"
  val="$(grep -E '^HOST_LOG_DIR=' "$docker_env" 2>/dev/null | tail -1 | cut -d= -f2- || true)"
  if [[ -n "$val" ]]; then
    if [[ "$val" != /* ]]; then
      val="$ROOT/$val"
    fi
    if [[ -d "$val" ]]; then
      export HOST_LOG_DIR="$val"
      export LOG_DIR_HOST="$val"
    fi
  fi
}

monitoring_env() {
  local access_host
  access_host="$(detect_public_host 2>/dev/null || detect_lan_ip 2>/dev/null || echo "127.0.0.1")"
  monitoring_sync_app_env
  prepare_dirs
  mkdir -p "$LOG_DIR"
  export LOG_DIR_HOST="$(cd "$LOG_DIR" && pwd)"
  export LOG_DIR_CONTAINER="/var/log/ai-platform"
  export HOST_LOG_DIR="${HOST_LOG_DIR:-$LOG_DIR_HOST}"
  export GRAFANA_PORT
  export LOKI_PORT
  export GRAFANA_ADMIN_USER
  export GRAFANA_ADMIN_PASSWORD
  export GRAFANA_ROOT_URL="${GRAFANA_ROOT_URL:-http://${access_host}:${FRONTEND_PORT}/api/v1/logs/grafana}"
  export GRAFANA_ANONYMOUS_ENABLED="${GRAFANA_ANONYMOUS_ENABLED:-false}"
  monitoring_detect_log_volume
}

monitoring_detect_log_volume() {
  export DOCKER_APP_LOGS_VOLUME=""
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'ai-platform-backend'; then
    return 0
  fi
  local mount_name mount_source mount_type
  mount_type="$(docker inspect ai-platform-backend --format '{{range .Mounts}}{{if eq .Destination "/app/logs"}}{{.Type}}{{end}}{{end}}' 2>/dev/null || true)"
  mount_name="$(docker inspect ai-platform-backend --format '{{range .Mounts}}{{if eq .Destination "/app/logs"}}{{.Name}}{{end}}{{end}}' 2>/dev/null || true)"
  mount_source="$(docker inspect ai-platform-backend --format '{{range .Mounts}}{{if eq .Destination "/app/logs"}}{{.Source}}{{end}}{{end}}' 2>/dev/null || true)"

  if [[ "$mount_type" == "volume" && -n "$mount_name" ]]; then
    export DOCKER_APP_LOGS_VOLUME="$mount_name"
    info "检测到 backend 日志卷: ${DOCKER_APP_LOGS_VOLUME}（Promtail 将挂载同一卷）"
    return 0
  fi

  if [[ -n "$mount_source" && -d "$mount_source" ]]; then
    export LOG_DIR_HOST="$mount_source"
    export HOST_LOG_DIR="$mount_source"
    info "检测到 backend 日志 bind 目录: ${LOG_DIR_HOST}"
  fi
}

monitoring_validate() {
  monitoring_env
  if [[ -n "${DOCKER_APP_LOGS_VOLUME:-}" ]]; then
    return 0
  fi
  if [[ -z "$LOG_DIR_HOST" ]]; then
    error "LOG_DIR_HOST 未设置，请使用: ./deploy.sh monitoring start"
    exit 1
  fi
  if [[ ! -d "$LOG_DIR_HOST" ]]; then
    error "日志目录不存在: $LOG_DIR_HOST"
    error "请先启动应用: ./deploy.sh start"
    exit 1
  fi
  touch "$LOG_DIR_HOST/backend.log" "$LOG_DIR_HOST/frontend.log" 2>/dev/null || true
}

monitoring_wait_grafana() {
  local i base="http://127.0.0.1:${GRAFANA_PORT:-3000}"
  for i in $(seq 1 30); do
    if curl -sf "${base}/api/health" >/dev/null 2>&1; then
      return 0
    fi
    sleep 2
  done
  warn "Grafana 启动超时"
  return 1
}

monitoring_provision_dashboard() {
  local user pass port base dash_file payload http_code
  user="${GRAFANA_ADMIN_USER:-admin}"
  pass="${GRAFANA_ADMIN_PASSWORD:-change-me-grafana-password}"
  port="${GRAFANA_PORT:-3000}"
  base="http://127.0.0.1:${port}"
  dash_file="$ROOT/monitoring/grafana/dashboards/ai-platform-logs.json"

  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'ai-platform-grafana'; then
    warn "Grafana 容器未运行，跳过仪表盘导入"
    return 1
  fi

  monitoring_wait_grafana || return 1

  local force="${1:-}"
  if [[ "$force" != "force" ]]; then
    local meta_url=""
    meta_url="$(curl -sf -u "${user}:${pass}" "${base}/api/dashboards/uid/ai-platform-logs" 2>/dev/null \
      | python3 -c "import sys,json; print(json.load(sys.stdin).get('meta',{}).get('url',''))" 2>/dev/null || true)"
    if [[ "$meta_url" == *"/d/ai-platform-logs/ai-platform-logs"* ]]; then
      ok "仪表盘 ai-platform-logs 已就绪（slug 正确）"
      return 0
    fi
    if [[ -n "$meta_url" ]]; then
      warn "仪表盘 slug 已过期: ${meta_url}"
      info "将强制覆盖导入（英文标题 → slug: ai-platform-logs）"
    fi
  fi

  if [[ ! -f "$dash_file" ]]; then
    warn "找不到仪表盘文件: $dash_file"
    return 1
  fi

  if ! command -v python3 >/dev/null 2>&1; then
    warn "需要 python3 才能导入仪表盘"
    return 1
  fi

  info "导入预置仪表盘「AI Platform Logs」..."
  payload="$(python3 - "$dash_file" <<'PY'
import json
import sys

with open(sys.argv[1], encoding="utf-8") as handle:
    dashboard = json.load(handle)
dashboard["id"] = None
print(json.dumps(
    {"dashboard": dashboard, "overwrite": True, "message": "AI platform provision"},
    ensure_ascii=False,
))
PY
)"
  http_code="$(curl -s -o /tmp/grafana-dash-import.json -w "%{http_code}" \
    -u "${user}:${pass}" \
    -X POST "${base}/api/dashboards/db" \
    -H "Content-Type: application/json" \
    -d "$payload")"
  if [[ "$http_code" == "200" ]]; then
    ok "仪表盘导入成功"
    return 0
  fi
  warn "仪表盘导入失败 (HTTP ${http_code})"
  cat /tmp/grafana-dash-import.json 2>/dev/null || true
  return 1
}

monitoring_verify_loki() {
  local labels query_resp
  if ! curl -sf "http://127.0.0.1:${LOKI_PORT}/ready" >/dev/null 2>&1; then
    warn "Loki 未就绪 (:${LOKI_PORT})"
    return 1
  fi
  labels="$(curl -sf "http://127.0.0.1:${LOKI_PORT}/loki/api/v1/labels" 2>/dev/null || true)"
  if [[ -z "$labels" ]] || ! echo "$labels" | grep -q 'ai-platform'; then
    warn "Loki 暂无日志数据，请检查:"
    echo "  1. 宿主机日志: ls -la $LOG_DIR_HOST"
    echo "  2. 容器内路径: docker exec ai-platform-promtail ls -la /var/log/ai-platform/"
    echo "  3. Promtail 日志: docker logs ai-platform-promtail --tail=50"
    echo "  4. 重置采集: docker compose -f $MONITORING_DIR/docker-compose.yml down -v && ./deploy.sh monitoring start"
    return 1
  fi
  query_resp="$(curl -sf -G "http://127.0.0.1:${LOKI_PORT}/loki/api/v1/query_range" \
    --data-urlencode 'query={job="ai-platform"}' \
    --data-urlencode 'limit=5' \
    --data-urlencode "start=$(($(date +%s) - 86400))000000000" \
    --data-urlencode "end=$(date +%s)000000000" 2>/dev/null || true)"
  if [[ -z "$query_resp" ]] || ! echo "$query_resp" | grep -q '"values"'; then
    warn "Loki 有标签但暂无日志行，请产生一些应用访问后再查看 Grafana"
    return 1
  fi
  ok "Loki 日志采集正常"
  return 0
}

monitoring_write_env() {
  monitoring_env
  cat >"$MONITORING_DIR/.env" <<EOF
LOG_DIR_HOST=${LOG_DIR_HOST}
DOCKER_APP_LOGS_VOLUME=${DOCKER_APP_LOGS_VOLUME:-}
GRAFANA_PORT=${GRAFANA_PORT}
LOKI_PORT=${LOKI_PORT}
GRAFANA_ADMIN_USER=${GRAFANA_ADMIN_USER}
GRAFANA_ADMIN_PASSWORD=${GRAFANA_ADMIN_PASSWORD}
GRAFANA_ROOT_URL=${GRAFANA_ROOT_URL}
GRAFANA_URL=http://host.docker.internal:${GRAFANA_PORT}
LOKI_URL=http://host.docker.internal:${LOKI_PORT}
GRAFANA_ANONYMOUS_ENABLED=${GRAFANA_ANONYMOUS_ENABLED:-false}
EOF
}

monitoring_start() {
  require_docker
  monitoring_validate
  monitoring_write_env
  info "启动 Grafana + Loki + Promtail ..."
  if [[ -n "${DOCKER_APP_LOGS_VOLUME:-}" ]]; then
    info "  日志卷:   ${DOCKER_APP_LOGS_VOLUME} -> ${LOG_DIR_CONTAINER}"
  else
    info "  日志目录: ${LOG_DIR_HOST} -> ${LOG_DIR_CONTAINER}"
  fi
  info "  Grafana:  ${GRAFANA_ROOT_URL}"
  if ! monitoring_compose config --quiet; then
    error "docker-compose 配置无效，请执行: ./deploy.sh monitoring debug"
    exit 1
  fi
  info "拉取镜像（首次可能较慢）..."
  if ! monitoring_compose pull; then
    warn "镜像拉取失败，若服务器在国内请配置 Docker 镜像加速后重试"
    warn "参考: ./deploy.sh monitoring debug"
  fi
  info "执行: docker compose up -d"
  if ! monitoring_compose up -d --remove-orphans; then
    error "监控栈启动失败，详情如下:"
    monitoring_compose ps -a || true
    monitoring_compose logs --tail=50 || true
    exit 1
  fi
  sleep 3
  if ! monitoring_has_running; then
    error "监控容器未正常运行，请查看日志: ./deploy.sh monitoring logs"
    monitoring_compose ps -a || true
    monitoring_compose logs --tail=80 || true
    exit 1
  fi
  monitoring_verify_loki || true
  monitoring_provision_dashboard || true
  ok "监控栈已启动"
  monitoring_status
  warn "Grafana 默认账号: ${GRAFANA_ADMIN_USER} / ${GRAFANA_ADMIN_PASSWORD} （生产环境请修改）"
  warn "安全组需放行端口 ${GRAFANA_PORT}、${LOKI_PORT}（如需外网访问 Grafana）"
}

monitoring_stop() {
  require_docker
  monitoring_write_env
  monitoring_compose down --remove-orphans 2>/dev/null || true
  ok "监控栈已停止"
}

monitoring_fix_logs() {
  require_docker
  monitoring_env
  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'ai-platform-backend'; then
    error "backend 容器未运行，请先启动应用"
    exit 1
  fi
  if [[ -z "${LOG_DIR_HOST:-}" && -z "${DOCKER_APP_LOGS_VOLUME:-}" ]]; then
    error "无法检测 backend 日志位置"
    exit 1
  fi
  monitoring_write_env
  info "重建 Promtail 并挂载 backend 日志..."
  if [[ -n "${DOCKER_APP_LOGS_VOLUME:-}" ]]; then
    info "  使用 Docker 卷: ${DOCKER_APP_LOGS_VOLUME}"
    docker run --rm -v "${DOCKER_APP_LOGS_VOLUME}:/logs:ro" alpine ls -la /logs | head -10 || true
  else
    info "  使用宿主机目录: ${LOG_DIR_HOST}"
  fi
  docker volume rm ai-platform-monitoring_promtail-positions 2>/dev/null || true
  monitoring_compose up -d --force-recreate promtail
  sleep 4
  info "Promtail 挂载内容:"
  if ! docker exec ai-platform-promtail ls -la /var/log/ai-platform/; then
    error "Promtail 无法访问日志目录"
    exit 1
  fi
  if ! docker exec ai-platform-promtail test -f /var/log/ai-platform/backend.log 2>/dev/null; then
    error "Promtail 仍看不到 backend.log"
    echo "Promtail mounts:"
    docker inspect ai-platform-promtail --format '{{json .Mounts}}' 2>/dev/null || true
    exit 1
  fi
  ok "Promtail 已挂载 backend.log"
  info "Backend 日志大小: $(docker exec ai-platform-backend wc -c </app/logs/backend.log 2>/dev/null || echo 未知) bytes"
  info "Promtail 日志大小: $(docker exec ai-platform-promtail wc -c </var/log/ai-platform/backend.log 2>/dev/null || echo 未知) bytes"
  sleep 3
  monitoring_verify_loki || true
}

monitoring_restart() {
  monitoring_stop
  monitoring_start
}

monitoring_recreate_grafana() {
  require_docker
  monitoring_sync_app_env
  monitoring_write_env
  info "重建 Grafana 容器（应用最新配置）..."
  monitoring_compose up -d --force-recreate grafana
  sleep 5
  if [[ -f "$ROOT/.env.docker" ]]; then
    local pass
    pass="$(grep -E '^GRAFANA_ADMIN_PASSWORD=' "$ROOT/.env.docker" | tail -1 | cut -d= -f2- || true)"
    if [[ -n "$pass" ]] && docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'ai-platform-grafana'; then
      docker exec ai-platform-grafana grafana-cli admin reset-admin-password "$pass" >/dev/null 2>&1 || true
    fi
  fi
  monitoring_provision_dashboard || true
  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'ai-platform-backend'; then
    info "重启 backend 以同步 Grafana 配置..."
    app_compose up -d --force-recreate backend 2>/dev/null || true
  fi
  ok "Grafana 已重建: ${GRAFANA_ROOT_URL:-http://127.0.0.1:${GRAFANA_PORT}}"
}

monitoring_fix_dashboard() {
  require_docker
  monitoring_sync_app_env
  monitoring_write_env
  monitoring_provision_dashboard force
}

monitoring_fix_auth() {
  require_docker
  local new_pass="${1:-}"
  if [[ -z "$new_pass" ]]; then
    new_pass="AiPlatform@$(date +%Y)"
  fi
  export GRAFANA_ADMIN_USER="${GRAFANA_ADMIN_USER:-admin}"
  export GRAFANA_ADMIN_PASSWORD="$new_pass"

  if ! docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'ai-platform-grafana'; then
    error "Grafana 容器未运行，请先执行: ./deploy.sh monitoring start"
    exit 1
  fi

  info "重置 Grafana 管理员密码并同步到配置文件..."
  docker exec ai-platform-grafana grafana-cli admin reset-admin-password "$new_pass"
  monitoring_write_env

  local docker_env="$ROOT/.env.docker"
  if [[ -f "$docker_env" ]]; then
    if grep -q '^GRAFANA_ADMIN_PASSWORD=' "$docker_env"; then
      sed -i "s|^GRAFANA_ADMIN_PASSWORD=.*|GRAFANA_ADMIN_PASSWORD=${new_pass}|" "$docker_env"
    else
      echo "GRAFANA_ADMIN_PASSWORD=${new_pass}" >>"$docker_env"
    fi
    if ! grep -q '^GRAFANA_ADMIN_USER=' "$docker_env"; then
      echo "GRAFANA_ADMIN_USER=${GRAFANA_ADMIN_USER}" >>"$docker_env"
    fi
  fi

  if docker ps --format '{{.Names}}' 2>/dev/null | grep -qx 'ai-platform-backend'; then
    info "重启 backend 以加载新密码..."
    app_compose up -d --force-recreate backend
  fi

  info "验证 Grafana 认证..."
  if curl -sf -u "${GRAFANA_ADMIN_USER}:${new_pass}" "http://127.0.0.1:${GRAFANA_PORT}/api/user" >/dev/null; then
    ok "Grafana API 认证通过"
  else
    warn "Grafana API 认证仍失败，请检查 GRAFANA_PORT=${GRAFANA_PORT} 与容器状态"
  fi

  ok "Grafana 认证已修复"
  echo "  用户名: ${GRAFANA_ADMIN_USER}"
  echo "  密码:   ${new_pass}"
  echo "  已同步: monitoring/.env, .env.docker"
  echo "  请刷新平台「日志监控」页面"
}

monitoring_status() {
  require_docker
  monitoring_write_env
  local access_host
  access_host="$(detect_access_host)"
  echo "========================================"
  echo "  Grafana + Loki 监控栈"
  echo "========================================"
  monitoring_compose ps -a
  echo
  local count
  count="$(monitoring_compose ps -a --format '{{.Name}}' 2>/dev/null | grep -c . || echo 0)"
  if [[ "$count" -eq 0 ]]; then
    warn "未发现任何监控容器（尚未启动或已被删除）"
    echo "  请执行: PUBLIC_HOST=你的公网IP ./deploy.sh monitoring start"
    echo
  fi
  if port_listening "$GRAFANA_PORT"; then
    ok "Grafana  http://${access_host}:${GRAFANA_PORT}"
  else
    warn "Grafana 未监听 :${GRAFANA_PORT}"
  fi
  if port_listening "$LOKI_PORT"; then
    ok "Loki     http://${access_host}:${LOKI_PORT}"
  else
    warn "Loki 未监听 :${LOKI_PORT}"
  fi
  echo "仪表盘: ${GRAFANA_ROOT_URL:-http://${access_host}:${GRAFANA_PORT}}/d/ai-platform-logs"
}

monitoring_logs() {
  require_docker
  monitoring_write_env
  if [[ "$(monitoring_compose ps -a --format '{{.Name}}' 2>/dev/null | grep -c . || echo 0)" -eq 0 ]]; then
    error "没有监控容器，请先执行: ./deploy.sh monitoring start"
    exit 1
  fi
  monitoring_compose logs --tail="${1:-100}" -f
}

monitoring_debug() {
  require_docker
  monitoring_write_env
  echo "========================================"
  echo "  监控栈诊断"
  echo "========================================"
  echo "目录: $MONITORING_DIR"
  echo "Docker: $(docker --version 2>/dev/null || echo 未知)"
  echo "Compose: $(docker compose version 2>/dev/null || echo 未知)"
  echo
  echo "--- monitoring/.env ---"
  cat "$MONITORING_DIR/.env" 2>/dev/null || echo "(无 .env 文件)"
  echo
  if [[ -n "${DOCKER_APP_LOGS_VOLUME:-}" ]]; then
    echo "--- Docker 日志卷 ---"
    echo "DOCKER_APP_LOGS_VOLUME=${DOCKER_APP_LOGS_VOLUME}"
    docker run --rm -v "${DOCKER_APP_LOGS_VOLUME}:/logs:ro" alpine ls -la /logs 2>&1 || true
  else
    echo "--- 日志目录 ---"
    ls -la "$LOG_DIR_HOST" 2>/dev/null || warn "目录不存在: $LOG_DIR_HOST"
  fi
  echo
  echo "--- docker compose config ---"
  monitoring_compose config 2>&1 || true
  echo
  echo "--- docker compose ps -a ---"
  monitoring_compose ps -a 2>&1 || true
  echo
  echo "--- 容器内日志目录 ---"
  docker exec ai-platform-promtail ls -la /var/log/ai-platform/ 2>&1 || true
  echo
  echo "--- Loki labels ---"
  curl -sf "http://127.0.0.1:${LOKI_PORT}/loki/api/v1/labels" 2>&1 || true
  echo
  echo "--- Promtail 最近日志 ---"
  docker logs ai-platform-promtail --tail=30 2>&1 || true
  echo
  echo "若镜像拉取失败，请配置 /etc/docker/daemon.json 镜像加速后: systemctl restart docker"
}

monitoring_main() {
  local action="${1:-}"
  if [[ -z "$action" ]]; then
    require_docker
    monitoring_write_env
    cd "$MONITORING_DIR"
    if monitoring_has_running; then
      monitoring_status
    else
      warn "监控栈未运行，正在自动启动..."
      monitoring_start
    fi
    return
  fi
  case "$action" in
    start) monitoring_start ;;
    stop) monitoring_stop ;;
    restart) monitoring_restart ;;
    recreate-grafana) monitoring_recreate_grafana ;;
    fix-auth) monitoring_fix_auth "${2:-}" ;;
    fix-logs) monitoring_fix_logs ;;
    fix-dashboard) monitoring_fix_dashboard ;;
    status) monitoring_status ;;
    logs) monitoring_logs "${2:-100}" ;;
    debug) monitoring_debug ;;
    *)
      error "未知 monitoring 子命令: $action"
      echo "用法: $0 monitoring [start|stop|restart|recreate-grafana|fix-auth [密码]|fix-logs|fix-dashboard|status|logs|debug]"
      exit 1
      ;;
  esac
}

main() {
  local cmd="${1:-start}"
  case "$cmd" in
    -h|--help|help)
      usage
      ;;
    install)
      install_all
      ok "依赖安装完成"
      ;;
    start|"")
      start_dev
      ;;
    stop)
      prepare_dirs
      stop_all
      ok "所有服务已停止"
      ;;
    restart)
      prepare_dirs
      stop_all
      start_backend
      start_frontend_dev
      print_banner
      ;;
    ensure)
      ensure_services
      ;;
    logs)
      show_logs "${2:-50}"
      ;;
    status)
      prepare_dirs
      show_status
      ;;
    prod)
      start_prod
      ;;
    update)
      update_project
      ;;
    app-rebuild)
      app_rebuild
      ;;
    clone)
      clone_project "${2:-}"
      ;;
    monitoring)
      monitoring_main "${2:-}"
      ;;
    docker)
      shift
      if [[ $# -eq 0 ]]; then
        set -- up
      fi
      bash "$ROOT/linux-deploy.sh" "$@"
      ;;
    *)
      error "未知命令: $cmd"
      usage
      exit 1
      ;;
  esac
}

bootstrap_deploy "${1:-start}"
main "${1:-start}"
