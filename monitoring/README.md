# Grafana + Loki 日志监控栈

将 `.deploy/logs/` 下的应用日志采集到 Loki，并通过 Grafana 可视化查询。

## 前置条件

- 已安装 [Docker](https://docs.docker.com/engine/install/) 与 Docker Compose 插件
- 应用日志目录存在（先执行 `./deploy.sh start`）

## 快速启动

```bash
# 在项目根目录（必须用 deploy.sh，不要直接 docker compose）
./deploy.sh start
./deploy.sh monitoring start
./deploy.sh monitoring status
```

> 若手动执行 `docker compose`，需先设置绝对路径：
> `export LOG_DIR_HOST=/opt/AI_testing_platform/.deploy/logs`

## 访问地址

| 服务 | 默认地址 | 默认账号 |
|------|----------|----------|
| Grafana | http://服务器IP:3000 | admin / admin123 |
| Loki API | http://服务器IP:3100 | 无认证（内网使用） |

预置仪表盘：**AI质量平台日志** (`uid: ai-platform-logs`)

Explore 示例 LogQL：

```logql
{job="ai-platform"}
{job="ai-platform", source="backend"}
{job="ai-platform"} |~ "error|exception"
```

## 环境变量

可在项目根目录创建 `monitoring/.env` 或通过 shell 导出：

```bash
export GRAFANA_PORT=3000
export LOKI_PORT=3100
export GRAFANA_ADMIN_PASSWORD=your-password
export GRAFANA_ROOT_URL=http://你的公网IP:3000
export LOG_DIR_HOST=/opt/AI_testing_platform/.deploy/logs
```

`deploy.sh monitoring start` 会自动设置 `LOG_DIR_HOST` 与 `GRAFANA_ROOT_URL`。

## 故障排查

容器列表为空或端口未监听时：

```bash
cd /opt/AI_testing_platform
git pull
./deploy.sh monitoring restart
./deploy.sh monitoring logs
```

常见原因：
- 未用 `./deploy.sh monitoring start` 导致 `LOG_DIR_HOST` 为空
- 镜像拉取失败（检查网络 / Docker 镜像加速）
- 安全组未放行 3000、3100 端口

手动检查：

```bash
cd /opt/AI_testing_platform/monitoring
cat .env
docker compose ps -a
docker compose logs loki --tail=50
```

## 常用命令

```bash
./deploy.sh monitoring start    # 启动 Loki + Promtail + Grafana
./deploy.sh monitoring stop     # 停止
./deploy.sh monitoring restart  # 重启
./deploy.sh monitoring status   # 查看容器状态
./deploy.sh monitoring logs     # 查看监控栈日志
```

## 平台内嵌入口

管理员登录 → **系统管理 → 日志监控 → Grafana Loki** 页签，可查看状态并跳转 Grafana。

后端配置（`backend/.env`）：

```env
GRAFANA_ENABLED=true
GRAFANA_URL=http://127.0.0.1:3000
LOKI_URL=http://127.0.0.1:3100
GRAFANA_EMBED=true
```

## 安全建议

- 生产环境修改 Grafana 默认密码
- 安全组仅对运维 IP 开放 3000/3100 端口
- 不要将 Loki/Grafana 直接暴露公网而不设认证
