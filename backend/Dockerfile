FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    NODE_PATH=/app/script_libs/node_modules \
    TZ=Asia/Shanghai

# 海外 VPS 构建时常见 DNS 解析失败：注入公共 DNS 并重试 apt（不安装 fonts-noto-cjk，PDF 用 reportlab 内置字体）
# nodejs/npm：脚本库调试/执行 JavaScript 前后置脚本用（后端容器无 node，前端只在构建时用）
RUN set -ux; \
    printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\nnameserver 208.67.222.222\n' > /etc/resolv.conf; \
    apt_ok=0; \
    for i in 1 2 3 4 5; do \
      if apt-get update && apt-get install -y --no-install-recommends tzdata ca-certificates nodejs npm; then \
        apt_ok=1; \
        break; \
      fi; \
      sleep 3; \
    done; \
    if [ "$apt_ok" -ne 1 ]; then echo "[WARN] apt install skipped (network/DNS issue), continue build"; fi; \
    rm -rf /var/lib/apt/lists/* || true

COPY requirements.txt .
RUN pip install --upgrade pip setuptools wheel \
    && pip install --retries 5 --timeout 120 -r requirements.txt

# JS 脚本预置库（对齐 Postman 内置库：CryptoJS/lodash/moment/uuid/ajv/cheerio/xml2js/chai/tv4）
# 经 NODE_PATH 供脚本 require/全局使用。装失败仿 apt：警告并继续，不阻断整体部署
COPY script_libs/package.json script_libs/package-lock.json ./script_libs/
RUN set -ux; \
    cd /app/script_libs; \
    libs_ok=0; \
    for i in 1 2 3; do \
      if npm install --omit=dev --no-audit --no-fund; then libs_ok=1; break; fi; \
      sleep 3; \
    done; \
    if [ "$libs_ok" -ne 1 ]; then echo "[WARN] script_libs npm 安装失败，JS 预置库将不可用，继续构建"; fi

COPY app ./app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/logs

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
