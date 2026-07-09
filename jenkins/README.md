# Jenkins CI/CD - AI测试平台自动部署

通过 Jenkins 在代码推送到 GitHub 后，自动拉取最新代码并重建 Docker 中的**前端**与**后端**服务。

## 架构

```
GitHub (push main)
    │
    ▼ Webhook / 轮询 SCM
Jenkins (Docker 容器，挂载 docker.sock)
    │
    ▼ jenkins/scripts/deploy.sh
git pull → docker compose up -d --build (backend + frontend)
    │
    ▼
ai-platform-frontend / ai-platform-backend / ai-platform-mysql
```

与项目现有脚本的关系：

| 脚本 | 作用 |
|------|------|
| `jenkins/scripts/deploy.sh` | Jenkins 专用：拉代码 + 选择性重建前后端 + 健康检查 |
| `update.sh` | 手动一键更新（等价逻辑） |
| `linux-deploy.sh update` | Linux 部署机手动更新 |

## 前置条件

- Linux 服务器（推荐与 `linux-deploy.sh` 同机部署）
- Docker 20.10+、Docker Compose v2
- 应用已通过 `./linux-deploy.sh up` 首次部署
- 已配置 `$APP_DIR/.env.docker`（含数据库密码等，**勿提交 Git**）
- 服务器可访问 GitHub（拉取代码）

默认路径：

| 变量 | 默认值 |
|------|--------|
| `APP_DIR` | `/opt/AI_testing_platform` |
| `ENV_FILE` | `/opt/AI_testing_platform/.env.docker` |
| Jenkins 端口 | `8080` |

## 一键安装

在部署服务器上：

```bash
cd /opt/AI_testing_platform
git pull   # 确保包含 jenkins/ 目录
chmod +x jenkins/install.sh jenkins/scripts/deploy.sh
sudo APP_DIR=/opt/AI_testing_platform ./jenkins/install.sh
```

安装脚本会：

1. 确认/克隆应用仓库到 `APP_DIR`
2. 构建 Jenkins 镜像（含 Docker CLI、Git、常用插件）
3. 启动 `ai-platform-jenkins` 容器
4. 挂载宿主机 Docker Socket，使 Jenkins 能执行 `docker compose`

查看 Jenkins 日志：

```bash
docker logs -f ai-platform-jenkins
```

## 登录认证（重要）

默认安装会**跳过 Jenkins 初始化向导**，若未配置安全策略，会出现**无需账号即可访问**的情况。

已内置 JCasC 配置，启用 **本地账号 + 禁止匿名访问**：

| 变量 | 说明 |
|------|------|
| `JENKINS_ADMIN_USER` | 管理员用户名（默认 `admin`） |
| `JENKINS_ADMIN_PASSWORD` | 管理员密码（**必填强密码**） |

### 为已安装的 Jenkins 启用登录

```bash
cd /opt/AI_testing_platform
git pull
chmod +x jenkins/enable-auth.sh
sudo bash jenkins/enable-auth.sh
```

脚本会生成 `jenkins/.env`、设置密码并重启 Jenkins。完成后用输出的用户名密码登录。

手动设置密码：

```bash
cd /opt/AI_testing_platform/jenkins
cp .env.example .env
vi .env   # 修改 JENKINS_ADMIN_PASSWORD
docker compose --env-file .env up -d --build
```

> GitHub Webhook（`POST /github-webhook/`）仍可匿名触发构建，不受登录限制。

## 配置 Jenkins 任务（只执行 update.sh 发版）

Jenkins **不再拉取 workspace 代码**，只会在服务器上执行：

```bash
cd /opt/AI_testing_platform && bash ./update.sh
```

`update.sh` 会自动：`git pull` → `linux-deploy.sh update` → 重建前后端 Docker。

### 方式一：Pipeline 脚本直接写（最简单，推荐）

1. 新建/打开任务 **ai-testing-platform-deploy** → **Configure**
2. **General**：不用勾 parameterized
3. **Triggers**：勾选 **GitHub hook trigger for GITScm polling**
4. **Pipeline**：
   - Definition: **Pipeline script**（不是 from SCM）
   - 脚本内容：

```groovy
pipeline {
    agent any
    options {
        disableConcurrentBuilds()
        timeout(time: 45, unit: 'MINUTES')
        skipDefaultCheckout(true)
    }
    environment {
        APP_DIR = '/opt/AI_testing_platform'
        ENV_FILE = '/opt/AI_testing_platform/.env.docker'
    }
    triggers { githubPush() }
    stages {
        stage('一键发版') {
            steps {
                sh '''
                    set -e
                    APP_DIR="${APP_DIR:-/opt/AI_testing_platform}"
                    UPDATE_SCRIPT="${APP_DIR}/update.sh"
                    DEPLOY_SCRIPT="${APP_DIR}/jenkins/scripts/deploy.sh"
                    git config --global --add safe.directory "${APP_DIR}" 2>/dev/null || true
                    if [ ! -f "${UPDATE_SCRIPT}" ] && [ -d "${APP_DIR}/.git" ]; then
                      git -C "${APP_DIR}" pull --ff-only || git -C "${APP_DIR}" pull || true
                    fi
                    if [ -f "${UPDATE_SCRIPT}" ]; then
                      bash "${UPDATE_SCRIPT}"
                    elif [ -f "${DEPLOY_SCRIPT}" ]; then
                      bash "${DEPLOY_SCRIPT}"
                    else
                      echo "缺少发版脚本，请执行: cd ${APP_DIR} && git pull"
                      exit 1
                    fi
                '''
            }
        }
    }
}
```

5. **Save** → **Build Now**

### 方式二：Pipeline from SCM（Jenkinsfile 在 Git 里维护）

1. **Pipeline** → Definition: **Pipeline script from SCM**
2. Git URL: `https://github.com/Reboot-QA/AI_testing_platform.git`
3. Branch: `*/main`
4. Script Path: `jenkins/Jenkinsfile`
5. **Triggers**：勾选 GitHub hook trigger

> 首次需 `git pull` 把最新 `jenkins/Jenkinsfile` 拉到服务器；或先用方式一直接发版。

## 配置 GitHub Webhook

1. GitHub 仓库 → **Settings** → **Webhooks** → **Add webhook**
2. 填写：

| 项 | 值 |
|----|-----|
| Payload URL | `http://你的服务器IP:8080/github-webhook/` |
| Content type | `application/json` |
| Secret | 安装时输出的 `GITHUB_WEBHOOK_SECRET` |
| 事件 | **Just the push event** |

3. 若 Jenkins 在 NAT/防火墙后，需放行 **8080** 端口，或使用内网穿透 / 反向代理。

> 安全建议：生产环境请为 Jenkins 配置 HTTPS + 强密码，并将 Webhook 仅暴露给 GitHub IP 段。

## 发版流程说明

Jenkins 执行 `update.sh`，等价于你在服务器手动运行：

```bash
cd /opt/AI_testing_platform
./update.sh
```

步骤：`git pull` → `linux-deploy.sh update` → `docker compose up -d --build`

手动发版（不经过 Jenkins）：

```bash
cd /opt/AI_testing_platform && ./update.sh
```

## 环境变量

Jenkins 容器内可通过 `jenkins/docker-compose.yml` 覆盖：

```yaml
environment:
  APP_DIR: /opt/AI_testing_platform
  ENV_FILE: /opt/AI_testing_platform/.env.docker
  GITHUB_WEBHOOK_SECRET: your-secret
```

宿主机手动测试部署脚本：

```bash
export APP_DIR=/opt/AI_testing_platform
export ENV_FILE=/opt/AI_testing_platform/.env.docker
bash /opt/AI_testing_platform/jenkins/scripts/deploy.sh
```

## 常见问题

### 1. Jenkins 构建失败：`./update.sh: No such file or directory`

服务器上的代码过旧，还没有 `update.sh`。在服务器执行一次：

```bash
cd /opt/AI_testing_platform
git pull
chmod +x update.sh linux-deploy.sh jenkins/scripts/deploy.sh
sudo bash jenkins/fix-app-permissions.sh
```

然后在 Jenkins 任务里把 Pipeline 脚本更新为 `jenkins/Jenkinsfile` 中的最新版本（支持自动 `git pull` 和回退 `jenkins/scripts/deploy.sh`）。

### 2. Jenkins 构建失败：缺少 .env.docker

在应用目录创建环境文件：

```bash
cd /opt/AI_testing_platform
cp .env.docker.example .env.docker
./linux-deploy.sh init-env
```

### 2. docker permission denied

确保 Jenkins 容器以 root 启动（`docker-compose.yml` 中 `user: root`），或已将 jenkins 用户加入 docker 组。

### 3. git pull 失败

在 `APP_DIR` 检查：

```bash
cd /opt/AI_testing_platform
git status
git pull origin main
```

### 4. 后端启动超时

```bash
docker logs ai-platform-backend --tail=80
./linux-deploy.sh diagnose
```

### 6. Permission denied: /var/jenkins_home

数据卷曾被 `root` 创建，Jenkins 进程（UID 1000）无法写入。执行：

```bash
cd /opt/AI_testing_platform
chmod +x jenkins/fix-permissions.sh
sudo bash jenkins/fix-permissions.sh
```

或手动：

```bash
docker compose -f jenkins/docker-compose.yml down
docker run --rm -v jenkins_jenkins-data:/var/jenkins_home busybox chown -R 1000:1000 /var/jenkins_home
export DOCKER_GID=$(getent group docker | cut -d: -f3)
docker compose -f jenkins/docker-compose.yml up -d
```

若无需保留 Jenkins 配置，可清空数据卷重建：

```bash
docker compose -f jenkins/docker-compose.yml down -v
docker compose -f jenkins/docker-compose.yml up -d --build
```


- 确认 GitHub Webhook 最近投递返回 200
- Jenkins 任务已勾选 **GitHub hook trigger for GITScm polling**
- 可依赖 SCM 轮询（Jenkinsfile 已配置每 5 分钟）

## 停止 / 卸载 Jenkins

```bash
cd /opt/AI_testing_platform/jenkins
docker compose down
# 删除数据卷（会清除 Jenkins 配置）:
# docker volume rm jenkins_jenkins-data
```

应用本身（MySQL / 前后端）不受影响。

## 文件说明

```
jenkins/
├── Dockerfile              # Jenkins 镜像（Docker CLI + 插件）
├── docker-compose.yml      # Jenkins 服务编排
├── casc.yaml               # Jenkins 基础配置 (JCasC)
├── plugins.txt             # 预装插件列表
├── Jenkinsfile             # Pipeline 定义
├── install.sh              # 一键安装
├── scripts/
│   └── deploy.sh           # 实际部署逻辑
└── README.md               # 本文档
```
