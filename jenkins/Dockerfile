FROM jenkins/jenkins:lts-jdk17

USER root

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
        ca-certificates \
        curl \
        docker.io \
        git \
        jq \
    && rm -rf /var/lib/apt/lists/*

# Jenkins 用户可调用宿主机 Docker（通过挂载 /var/run/docker.sock）
RUN usermod -aG docker jenkins

COPY plugins.txt /usr/share/jenkins/ref/plugins.txt
RUN jenkins-plugin-cli --plugin-file /usr/share/jenkins/ref/plugins.txt

USER jenkins
