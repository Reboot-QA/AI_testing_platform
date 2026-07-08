FROM jenkins/jenkins:lts-jdk17

USER root

# Jenkins 基础镜像是 Debian，不能用 Ubuntu 的 docker-compose-v2 包
# 改为下载 Docker 官方静态 CLI + Compose 插件（通过 docker.sock 调用宿主机 Docker）
ARG DOCKER_VERSION=27.3.1
ARG COMPOSE_VERSION=2.32.4

RUN set -eux; \
    apt-get update; \
    apt-get install -y --no-install-recommends ca-certificates curl git jq; \
    rm -rf /var/lib/apt/lists/*; \
    ARCH="$(uname -m)"; \
    case "$ARCH" in \
      x86_64)  DOCKER_ARCH=x86_64;  COMPOSE_ARCH=x86_64 ;; \
      aarch64) DOCKER_ARCH=aarch64; COMPOSE_ARCH=aarch64 ;; \
      arm64)   DOCKER_ARCH=aarch64; COMPOSE_ARCH=aarch64 ;; \
      *) echo "unsupported arch: $ARCH" >&2; exit 1 ;; \
    esac; \
    curl -fsSL "https://download.docker.com/linux/static/stable/${DOCKER_ARCH}/docker-${DOCKER_VERSION}.tgz" \
      | tar xz -C /tmp; \
    mv /tmp/docker/docker /usr/local/bin/docker; \
    mkdir -p /usr/local/lib/docker/cli-plugins; \
    curl -fsSL "https://github.com/docker/compose/releases/download/v${COMPOSE_VERSION}/docker-compose-linux-${COMPOSE_ARCH}" \
      -o /usr/local/lib/docker/cli-plugins/docker-compose; \
    chmod +x /usr/local/bin/docker /usr/local/lib/docker/cli-plugins/docker-compose; \
    docker --version; \
    docker compose version

RUN usermod -aG docker jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/

ENV PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

USER jenkins
