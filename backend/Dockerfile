FROM python:3.11-slim

WORKDIR /app

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    PIP_NO_CACHE_DIR=1 \
    TZ=Asia/Shanghai

# 海外 VPS 构建时常见 DNS 解析失败：注入公共 DNS 并重试 apt（不安装 fonts-noto-cjk，PDF 用 reportlab 内置字体）
# nodejs：脚本库调试/执行 JavaScript 前后置脚本用（后端容器无 node，前端只在构建时用）
RUN set -ux; \
    printf 'nameserver 8.8.8.8\nnameserver 1.1.1.1\nnameserver 208.67.222.222\n' > /etc/resolv.conf; \
    apt_ok=0; \
    for i in 1 2 3 4 5; do \
      if apt-get update && apt-get install -y --no-install-recommends tzdata ca-certificates nodejs; then \
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

COPY app ./app
COPY docker/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

RUN mkdir -p /app/logs

EXPOSE 8000

ENTRYPOINT ["/entrypoint.sh"]
