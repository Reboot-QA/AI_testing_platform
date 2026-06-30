#!/usr/bin/env bash
# AI质量平台 - 一键部署/启动脚本（前后端）
# 用法:
#   ./deploy.sh          安装依赖并启动开发环境
#   ./deploy.sh install  仅安装依赖
#   ./deploy.sh start    启动前后端
#   ./deploy.sh stop     停止前后端
#   ./deploy.sh restart  重启
#   ./deploy.sh status   查看运行状态
#   ./deploy.sh prod     构建前端并以生产模式启动后端
#   ./deploy.sh update   从 Git 仓库拉取最新代码并更新依赖
#   ./deploy.sh clone [目录]  首次部署：克隆仓库到指定目录

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
  prod            构建前端 + 生产模式启动后端
  update          从仓库拉取最新代码、更新依赖（若服务在运行则自动重启）
  clone [目录]    首次部署：克隆仓库（默认 ../AI_testing_platform）

环境变量:
  BACKEND_HOST    后端监听地址 (默认 0.0.0.0)
  BACKEND_PORT    后端端口 (默认 8000)
  FRONTEND_PORT   前端端口 (默认 5173)
  FRONTEND_HOST   前端监听地址 (默认 0.0.0.0，允许外网访问)
  PUBLIC_HOST     外网访问地址 (默认自动检测本机 IP)
  SKIP_FRONTEND   设为 1 时仅部署后端（无需 Node.js）
  GIT_REPO_URL    Git 仓库地址 (默认 $GIT_REPO_URL)
  GIT_BRANCH      拉取分支 (默认当前分支，否则 main)

首次部署示例:
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

detect_access_host() {
  if [[ -n "$PUBLIC_HOST" ]]; then
    echo "$PUBLIC_HOST"
    return
  fi
  local ip=""
  if command -v hostname >/dev/null 2>&1; then
    ip="$(hostname -I 2>/dev/null | awk '{print $1}')"
  fi
  if [[ -z "$ip" ]] && command -v ip >/dev/null 2>&1; then
    ip="$(ip -4 route get 1.1.1.1 2>/dev/null | awk '{for (i=1; i<=NF; i++) if ($i=="src") { print $(i+1); exit }}')"
  fi
  echo "${ip:-127.0.0.1}"
}

print_access_urls() {
  local access_host
  access_host="$(detect_access_host)"
  echo "  本机访问:"
  echo "    前端  http://127.0.0.1:${FRONTEND_PORT}"
  echo "    后端  http://127.0.0.1:${BACKEND_PORT}"
  if [[ "$access_host" != "127.0.0.1" ]]; then
    echo "  外网/局域网访问 (请用服务器 IP，不要用 127.0.0.1):"
    echo "    前端  http://${access_host}:${FRONTEND_PORT}"
    echo "    后端  http://${access_host}:${BACKEND_PORT}"
    echo "    文档  http://${access_host}:${BACKEND_PORT}/docs"
  fi
}

print_firewall_hint() {
  if [[ "$(detect_access_host)" == "127.0.0.1" ]]; then
    return
  fi
  warn "若外网无法打开页面，请检查云服务器安全组/防火墙是否放行端口 ${FRONTEND_PORT}、${BACKEND_PORT}"
  warn "  ufw:        sudo ufw allow ${FRONTEND_PORT}/tcp && sudo ufw allow ${BACKEND_PORT}/tcp"
  warn "  firewalld:  sudo firewall-cmd --add-port=${FRONTEND_PORT}/tcp --add-port=${BACKEND_PORT}/tcp --permanent && sudo firewall-cmd --reload"
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
  return 1
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

  git merge --ff-only "$remote_ref" || {
    error "拉取失败，请手动解决后重试"
    exit 1
  }
  ok "代码已更新: $(git log -1 --oneline)"
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
  export PATH="/usr/local/bin:/usr/bin:/bin:${HOME}/.nvm/versions/node/$(ls "${HOME}/.nvm/versions/node" 2>/dev/null | tail -1)/bin:${PATH}"

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

  # 尝试加载 nvm
  for nvm_sh in "${NVM_DIR:-$HOME/.nvm}/nvm.sh" "/root/.nvm/nvm.sh" "$HOME/.bashrc" "$HOME/.profile"; do
    if [[ -s "$nvm_sh" ]]; then
      # shellcheck source=/dev/null
      source "$nvm_sh" 2>/dev/null || true
      if command -v node >/dev/null 2>&1 && command -v npm >/dev/null 2>&1; then
        ok "已加载环境: Node $(node -v) | npm $(npm -v)"
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

stop_pid_file() {
  local name="$1"
  local pid_file="$2"
  if is_running "$pid_file"; then
    local pid
    pid="$(cat "$pid_file")"
    info "停止 $name (PID $pid)..."
    kill "$pid" 2>/dev/null || true
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
  return 1
}

start_backend() {
  if is_running "$BACKEND_PID_FILE"; then
    warn "后端已在运行 (PID $(cat "$BACKEND_PID_FILE"))"
    return 0
  fi
  ensure_backend_venv
  info "启动后端 http://${BACKEND_HOST}:${BACKEND_PORT} ..."
  cd "$BACKEND_DIR"
  nohup "$PYTHON" -m uvicorn app.main:app \
    --reload \
    --host "$BACKEND_HOST" \
    --port "$BACKEND_PORT" \
    >>"$BACKEND_LOG" 2>&1 &
  echo $! >"$BACKEND_PID_FILE"
  wait_backend || true
}

start_frontend_dev() {
  if [[ "${SKIP_FRONTEND:-0}" == "1" ]]; then
    warn "SKIP_FRONTEND=1，跳过前端启动"
    return 0
  fi
  if is_running "$FRONTEND_PID_FILE"; then
    warn "前端已在运行 (PID $(cat "$FRONTEND_PID_FILE"))"
    return 0
  fi
  info "启动前端 ${FRONTEND_HOST}:${FRONTEND_PORT} ..."
  cd "$FRONTEND_DIR"
  if [[ -x node_modules/.bin/vite ]]; then
    nohup node_modules/.bin/vite --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
      >>"$FRONTEND_LOG" 2>&1 &
  else
    nohup npm run dev -- --host "$FRONTEND_HOST" --port "$FRONTEND_PORT" \
      >>"$FRONTEND_LOG" 2>&1 &
  fi
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
  ensure_backend_venv
  info "生产模式启动后端..."
  cd "$BACKEND_DIR"
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
  npm run build
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
}

show_status() {
  detect_python
  local access_host
  access_host="$(detect_access_host)"
  echo "========================================"
  echo "  AI质量平台 - 服务状态"
  echo "========================================"
  if is_running "$BACKEND_PID_FILE"; then
    ok "后端运行中 PID=$(cat "$BACKEND_PID_FILE")"
    echo "       本机  http://127.0.0.1:${BACKEND_PORT}"
    if [[ "$access_host" != "127.0.0.1" ]]; then
      echo "       外网  http://${access_host}:${BACKEND_PORT}"
    fi
  else
    warn "后端未运行"
  fi
  if is_running "$FRONTEND_PID_FILE"; then
    ok "前端运行中 PID=$(cat "$FRONTEND_PID_FILE")"
    echo "       本机  http://127.0.0.1:${FRONTEND_PORT}"
    if [[ "$access_host" != "127.0.0.1" ]]; then
      echo "       外网  http://${access_host}:${FRONTEND_PORT}"
    fi
  else
    warn "前端未运行"
    if [[ -f "$FRONTEND_LOG" ]]; then
      echo "       日志: $FRONTEND_LOG"
      tail -5 "$FRONTEND_LOG" 2>/dev/null || true
    fi
  fi
  echo "Python: $PYTHON"
  echo "日志: $LOG_DIR"
  print_firewall_hint
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
    clone)
      clone_project "${2:-}"
      ;;
    *)
      error "未知命令: $cmd"
      usage
      exit 1
      ;;
  esac
}

main "${1:-start}"
