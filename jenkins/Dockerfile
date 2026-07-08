FROM jenkins/jenkins:lts-jdk17

USER root

# 安装 Docker CLI + Compose 插件（通过挂载的 docker.sock 调用宿主机 Docker）
RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        git \
        jq \
        docker.io \
        docker-compose-v2 \
    && rm -rf /var/lib/apt/lists/* \
    && docker --version \
    && docker compose version

RUN usermod -aG docker jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

COPY init.groovy.d/ /usr/share/jenkins/ref/init.groovy.d/

ENV PATH="/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"

USER jenkins
