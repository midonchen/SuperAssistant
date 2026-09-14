# SuperAssistant Staging 部署方案

## 1. 部署架构

直接复用 `infra/docker/docker-compose.yml` 的 5 容器拓扑：

| 容器 | 角色 | 资源画像 |
|------|------|---------|
| api | FastAPI + uvicorn（:8000） | CPU 突发型，内存 ~300MB |
| worker | Celery worker（衰减/提醒/重放任务） | 常驻，内存 ~200MB |
| beat | Celery beat 定时调度 | 极轻，内存 ~100MB |
| postgres | PostgreSQL 16 | 常驻 ~200MB，磁盘随数据增长 |
| redis | Redis 7（broker + 离线队列 + AI 配额计数） | 常驻 ~50MB |

## 2. 服务器配置建议

### 推荐（单虚拟机方案，staging 首选）

| 项 | 规格 | 说明 |
|----|------|------|
| 实例 | 2 vCPU / 4 GB RAM / 40 GB SSD | 阿里云 ecs.u1-c1m2、腾讯云 SA2、AWS t3.medium 同级 |
| 操作系统 | Ubuntu 22.04 LTS / 24.04 LTS | Docker 官方源支持最好 |
| 带宽 | 3–5 Mbps 按量或固定带宽 | 流量以 API JSON + 出站 AI 调用为主，无大文件 |
| 地域 | 离目标用户最近；若用中国大陆机房+域名需 ICP 备案，staging 可选香港免备案 | — |
| 参考月成本 | 约 ¥60–120/月（新客活动价更低） | — |

### 最低可用（预算敏感）

2 vCPU / 2 GB RAM / 40 GB SSD。需加 2 GB swap，且 compose 各服务无内存 limit 时要观察 OOM。仅建议短期验证用。

### 生产预留（后续 v1.5 再考虑）

4 vCPU / 8 GB，或保持 2C4G + 托管 PostgreSQL/Redis（云厂商基础版各约 ¥50–150/月）。生产环境数据库务必迁出容器卷，使用托管实例并开启自动备份。

## 3. 域名与 HTTPS

灰度门禁要求非本地 `API_BASE_URL`，移动端真机调试也要求 HTTPS：

1. 解析一个子域名（如 `api-staging.example.com`）A 记录到服务器 IP
2. 前置 Caddy（自动签发 Let's Encrypt 证书）或 Nginx + certbot
3. 反代规则：`https://api-staging.example.com/` → `http://127.0.0.1:8000/`
4. Caddy 单容器最简配置示例：
   ```
   api-staging.example.com {
       reverse_proxy 127.0.0.1:8000
   }
   ```

防火墙/安全组：仅放行 22（SSH，建议限源 IP）、80、443。8000/5432/6379 不对外。

## 4. 环境变量（.env）

在仓库根目录创建 `.env`（已在 .gitignore 中，禁止提交）。模板见 `infra/docker/.env.example`，关键项：

| 变量 | staging 值 |
|------|-----------|
| DATABASE_URL | `postgresql+psycopg://superassistant:<强口令>@postgres:5432/superassistant` |
| CELERY_BROKER_URL / CELERY_RESULT_BACKEND | `redis://redis:6379/0` / `redis://redis:6379/1` |
| OFFLINE_QUEUE_REDIS_URL | `redis://redis:6379/2` |
| AI_QUOTA_REDIS_URL | `redis://redis:6379/3` |
| STT_PROVIDER | `local`（MVP 语音走本地 STT，后续再开 Whisper） |
| LLM_PROVIDER | `deepseek` |
| DEEPSEEK_API_KEY | **真实密钥仅存在服务器 .env 中，绝不入库** |
| DEEPSEEK_MODEL | `deepseek-chat` |
| SUPERASSISTANT_ADMIN_PHONES | 管理员手机号（逗号分隔） |
| SUPERASSISTANT_AUDITOR_PHONES | 审核员手机号 |
| SUPERASSISTANT_MAX_ACTIVE_SESSIONS | `3` |
| POSTGRES_PASSWORD | 强口令（compose 引用） |

AI 成本护栏默认值即可：`AI_PROVIDER_QPS_PER_MINUTE` / `AI_PROVIDER_TOKEN_PER_MINUTE` / `AI_PROVIDER_TOKEN_PER_DAY` / 熔断器参数，超限时自动降级到本地启发式解析。

## 5. 部署步骤

```bash
# 1) 服务器初始化（Ubuntu）
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
sudo usermod -aG docker $USER   # 重新登录生效

# 2) 拉取代码
git clone git@github.com:midonchen/SuperAssistant.git
cd SuperAssistant

# 3) 配置环境（真实密钥在此步写入）
cp infra/docker/.env.example .env && vim .env

# 4) 启动依赖并执行迁移
docker compose -f infra/docker/docker-compose.yml up -d postgres redis
docker compose -f infra/docker/docker-compose.yml run --rm api alembic upgrade head

# 5) 全量启动
docker compose -f infra/docker/docker-compose.yml up --build -d

# 6) 冒烟验证
curl https://api-staging.example.com/healthz        # 200
```

compose 引用根目录 `.env` 时加 `--env-file .env` 参数。

## 6. 上线窗口动作（补齐非本地灰度证据）

staging 冒烟通过后，在本地执行（这是 phase6-window-gate-live 唯一缺的一环）：

```bash
make phase6-wave-exec WAVE=10  API_BASE_URL=https://api-staging.example.com/api/v1
make phase6-wave-exec WAVE=50  API_BASE_URL=https://api-staging.example.com/api/v1
make phase6-wave-exec-final WAVE=100 API_BASE_URL=https://api-staging.example.com/api/v1 REQUIRE_NON_LOCAL_WAVES=1
make phase6-window-gate-live   # 应转为 PASS
make phase6-handoff-pack       # 生成最终交接包
```

## 7. 运维基线

- 备份：每日 `pg_dump` 到对象存储（crontab 一行即可）；staging 可放宽到每周
- 日志：`docker compose logs -f api worker`；建议加 `--log-opt max-size=50m` 防止写爆磁盘
- 监控：先靠 `/healthz` + 云厂商基础监控；`infra/monitoring/` 后续再接 Prometheus
- 更新流程：本地 gate 全过 → push main → 服务器 `git pull && docker compose up --build -d` → `alembic upgrade head`

## 8. 明确不在本期范围

- FCM/APNs 真实推送（功能稳定后单独接入）
- 真实短信验证码通道（当前 /auth/sms/send 为模拟实现，staging 沿用）
- 托管数据库/多副本高可用（生产阶段再评估）
