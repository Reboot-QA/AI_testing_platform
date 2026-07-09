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
| Grafana | http://服务器IP:3000 | 平台内打开免登录（只读）；管理配置见 `.env.docker` |
| Loki API | http://服务器IP:3100 | 无认证（内网使用） |

预置仪表盘：**AI质量平台日志** (`uid: ai-platform-logs`)

Explore 示例 LogQL：

```logql
{job="ai-platform", source="backend"} |~ "HTTP [45][0-9]{2}|-> HTTP"
{job="ai-platform", source="backend", level="WARNING"}
{job="ai-platform"} |~ "error|exception|traceback"
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

**Grafana 显示 No data**：

```bash
cd /opt/AI_testing_platform
./deploy.sh start
ls -la .deploy/logs/
PUBLIC_HOST=38.12.6.230 ./deploy.sh monitoring restart
./deploy.sh monitoring debug
```

验证 Loki 是否有日志：

```bash
curl -s http://127.0.0.1:3100/loki/api/v1/labels
curl -G -s 'http://127.0.0.1:3100/loki/api/v1/query' \
  --data-urlencode 'query={job="ai-platform"}' --data-urlencode 'limit=5'
```

仍无数据时重置 Promtail 采集进度：

```bash
cd monitoring && docker compose down
docker volume rm ai-platform-monitoring_promtail-positions 2>/dev/null || true
cd .. && PUBLIC_HOST=38.12.6.230 ./deploy.sh monitoring start
```

Grafana 时间范围选 **Last 6 hours** 或 **Last 24 hours**。

**容器列表为空** 通常表示尚未执行 `start`（仅 `status` 也会生成 `.env`，但不会启动容器）。

```bash
cd /opt/AI_testing_platform
git pull
./deploy.sh start
PUBLIC_HOST=38.12.6.230 ./deploy.sh monitoring start
# 或直接（未运行时会自动 start）：
PUBLIC_HOST=38.12.6.230 ./deploy.sh monitoring
```

诊断命令：

```bash
./deploy.sh monitoring debug
./deploy.sh monitoring logs
```

常见原因：
- 只执行了 `./deploy.sh monitoring status`，未执行 `start`
- 镜像拉取失败（国内服务器需配置 Docker 镜像加速）
- Docker 未启动：`sudo systemctl start docker`
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
./deploy.sh monitoring debug    # 诊断（配置、镜像、容器）
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

- 生产环境修改 Grafana 管理员密码（`GRAFANA_ADMIN_PASSWORD`）
- 匿名访问为只读（Viewer），仅用于平台内查看日志
- 安全组仅对运维 IP 开放 3000/3100 端口
- 不要将 Loki/Grafana 直接暴露公网而不设访问控制
