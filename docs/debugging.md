# Debug 与日志排查指南

这份文档用于线上/本地排查问题时快速定位日志位置、查找 Trace-ID、判断问题属于前端、网关、后端业务、外部服务还是数据库审计日志。

## 1. 先看哪里

遇到问题时按这个顺序查：

1. 浏览器 DevTools Network
   - 看接口 URL、HTTP 状态码、响应体。
   - 重点复制响应头里的 `X-Trace-ID`，后端日志会用同一个 trace id 关联请求。

2. Docker 或 systemd 进程日志
   - Docker 部署：`docker compose logs -f backend`
   - 裸机部署：`journalctl -fu order-api`
   - 裸机 stdout/stderr：`/var/log/order-api/stdout.log`、`/var/log/order-api/stderr.log`

3. 后端业务日志目录
   - 本地开发：`cursor_sh/backend/logs/`
   - Docker 容器内：`/app/logs/`
   - 根目录 `docker-compose.yml` 使用 volume：`backend-logs:/app/logs`
   - `cursor_sh/backend/docker-compose.yml` 使用 bind mount：`cursor_sh/backend/logs:/app/logs`
   - 裸机脚本部署时后端工作目录是 `cursor_sh/backend`，默认 `LOG_DIR=./logs`，因此业务日志在 `cursor_sh/backend/logs/`

4. 网关/前端容器日志
   - 前端 Nginx 容器：`docker compose logs -f frontend`
   - 裸机 Nginx：`/var/log/nginx/access.log`、`/var/log/nginx/error.log`
   - 当前生产 HTTPS 入口如使用宿主机 Caddy：优先查 `journalctl -fu caddy`，再查宿主机 Caddy 日志目录。

## 2. 后端日志目录结构

后端日志由 `cursor_sh/backend/app/utils/log_setup.py` 初始化，根目录由 `.env` 中的 `LOG_DIR` 控制，默认是：

```env
LOG_DIR=./logs
```

目录结构：

```text
logs/
  auth/
    auth_YYYY-MM-DD.log
  workspace/
    workspace_YYYY-MM-DD.log
  order/
    order_YYYY-MM-DD.log
  ai/
    ai_YYYY-MM-DD.log
  staff/
    staff_YYYY-MM-DD.log
  notification/
    notification_YYYY-MM-DD.log
  contractor/
    contractor_YYYY-MM-DD.log
  system/
    system_YYYY-MM-DD.log
  error/
    error_YYYY-MM-DD.log
  crash/
    crash_YYYY-MM-DD.log
  ai_sessions/
    <user_id>/<session_id>.json
```

说明：

- `auth/`：登录、注册、短信验证码、鉴权相关请求。
- `workspace/`：前端交互日志 `/api/logs`。
- `order/`：订单、上传、预览、订单状态流转。
- `ai/`：AI 聊天、语音识别、客户资料、人工转接、Memory 相关。
- `staff/`：员工/负责人相关。
- `notification/`：通知创建、已读、删除。
- `contractor/`：承包商、交付物、工作流配置。
- `system/`：健康检查、公告、企业认证、无法归类请求、启动/退出信息。
- `error/`：汇总所有 `ERROR` 及以上日志。
- `crash/`：仅记录 `CRITICAL`，用于未捕获异常或严重崩溃。
- `ai_sessions/`：AI 聊天 JSON 归档，不是普通日志文件。

## 3. 日志配置

配置在 `cursor_sh/backend/.env`，示例见 `cursor_sh/backend/.env.example`：

```env
LOG_ENABLED=True
LOG_LEVEL=INFO
LOG_DIR=./logs
LOG_ROTATION=50 MB
LOG_RETENTION=30 days
LOG_COMPRESSION=gz
LOG_DB_ENABLED=True
LOG_DB_METHODS=POST,PUT,DELETE
LOG_DB_QUEUE_SIZE=1000
LOG_DB_WORKERS=2
LOG_SANITIZE_FIELDS=password,oldPassword,newPassword,old_password,new_password,token,secret,sms_code,captcha,invite_token
LOG_MAX_PAYLOAD_SIZE=4096
LOG_MODULES=Auth,Workspace,Order,AI,Staff,Notification,Contractor,System
```

常用调整：

- 临时深度排查：把 `LOG_LEVEL=INFO` 改成 `LOG_LEVEL=DEBUG`，重启后端。
- 控制日志大小：调整 `LOG_ROTATION`，例如 `50 MB` 或 `00:00`。
- 控制保留时间：调整 `LOG_RETENTION`，例如 `7 days`、`30 days`。
- 关闭数据库审计入库：`LOG_DB_ENABLED=False`。文件日志仍会写。

生产建议：

- 不要长期使用 `LOG_LEVEL=DEBUG`。
- 不要关闭 `LOG_SANITIZE_FIELDS`。
- `LOG_DB_ENABLED=True` 时，生产审计库建议使用 MySQL/RDS，不要和主业务高频写入互相影响。

## 4. 一条请求如何追踪

后端审计中间件会给每个请求生成 8 位 `trace_id`，并写入响应头：

```text
X-Trace-ID: ab12cd34
```

日志格式大致如下：

```text
2026-06-06 10:30:12.345 | INFO | [ab12cd34] [order] | POST /api/orders | 200 | 120ms | user=demo(user_xxx) | ip=1.2.3.4 | payload={...}
```

拿到 trace id 后直接查：

```bash
cd cursor_sh/backend
rg "ab12cd34" logs
```

线上 Docker 容器内查：

```bash
docker exec -it anti-pro-backend sh
cd /app
rg "ab12cd34" logs
```

如果容器内没有 `rg`，用：

```bash
grep -R "ab12cd34" /app/logs
```

## 5. 常用排查命令

查看后端实时日志：

```bash
docker compose logs -f backend
```

查看前端 Nginx 容器日志：

```bash
docker compose logs -f frontend
```

查看全部容器状态：

```bash
docker compose ps
```

进入后端容器：

```bash
docker exec -it anti-pro-backend bash
```

查看最近错误：

```bash
cd cursor_sh/backend
tail -100 logs/error/error_$(date +%F).log
```

按模块看当天日志：

```bash
cd cursor_sh/backend
tail -100 logs/order/order_$(date +%F).log
tail -100 logs/ai/ai_$(date +%F).log
tail -100 logs/system/system_$(date +%F).log
```

全局搜索错误关键词：

```bash
cd cursor_sh/backend
rg "ERROR|CRITICAL|failed|异常|失败|timeout|Timeout|502|500" logs
```

按订单查：

```bash
cd cursor_sh/backend
rg 'order_id="order_' logs
rg 'order_number="UV' logs
```

查外部服务失败：

```bash
cd cursor_sh/backend
rg "oss_.*failed|sms_.*failed|email_.*failed|ai_.*failed|_provider_call_failed|retrying" logs
```

裸机 systemd：

```bash
journalctl -fu order-api
journalctl -xeu order-api --no-pager -n 50
tail -f /var/log/order-api/stdout.log
tail -f /var/log/order-api/stderr.log
```

裸机 Nginx：

```bash
nginx -t
tail -f /var/log/nginx/access.log
tail -f /var/log/nginx/error.log
```

宿主机 Caddy：

```bash
journalctl -fu caddy
```

## 6. 数据库审计日志

后端会把写操作异步写入审计库表：

```text
operation_logs
```

字段包括：

- `trace_id`
- `user_id`
- `username`
- `type`：`api_call` 或 `frontend_action`
- `module`
- `action`
- `ip_address`
- `user_agent`
- `payload`
- `response_status`
- `duration_ms`
- `created_at`

触发入库的方法由 `LOG_DB_METHODS` 控制，默认：

```env
LOG_DB_METHODS=POST,PUT,DELETE
```

如果是 SQLite 审计库，可以在后端目录查：

```bash
cd cursor_sh/backend
sqlite3 audit.db "select created_at, trace_id, module, action, response_status, duration_ms from operation_logs order by created_at desc limit 20;"
```

如果生产使用 MySQL/RDS，以 `.env` 里的 `AUDIT_DATABASE_URL` 为准，用数据库客户端查询 `operation_logs`。

## 7. 前端交互日志

前端工具位于：

```text
cursor_sh/src/utils/logger.ts
```

它会把用户交互批量发送到：

```text
POST /api/logs
POST /api/logs/batch
```

后端接收 API 位于：

```text
cursor_sh/backend/app/api/logs.py
```

前端日志会写两处：

- 文件日志：`logs/workspace/workspace_YYYY-MM-DD.log`
- 审计库：`operation_logs`，`type=frontend_action`

注意：

- 未登录时前端日志不会发送。
- `sendBeacon` 不能带自定义 Authorization header，页面卸载时的日志可能不会全部入库；关键业务动作仍应以后端 API 日志为准。

## 8. 如何在代码里加日志

后端业务代码使用：

```python
from app.utils.log_setup import get_module_logger
from app.utils.business_log import log_business_event

logger = get_module_logger("order")

log_business_event(
    logger,
    "order_status_updated",
    order_id=order.id,
    status_from=old_status,
    status_to=new_status,
)
```

推荐规则：

- 业务状态变化使用稳定的 `event=...` 名称。
- 状态流转必须带 `status_from`、`status_to`。
- 跨角色交接带上关键 id：`order_id`、`assignment_id`、`deliverable_id`、`user_id`、`contractor_id`、`admin_id`。
- 外部服务失败最终态使用 `*_failed`，重试中使用 `*_retrying`。
- 不要记录密码、验证码、token、secret、完整手机号、完整邮箱用户名。
- 大 payload 只记录 id、数量、状态、文件名、大小等摘要。

前端代码使用：

```ts
import { logger } from '@/utils/logger'

logger.logAction('Order', 'click_submit_order', {
  orderId,
  status,
})
```

## 9. 常见问题定位

### 登录失败

先查：

```bash
cd cursor_sh/backend
tail -100 logs/auth/auth_$(date +%F).log
rg "POST /api/auth|sms|captcha|login" logs/auth logs/error
```

再看浏览器 Network 里的响应码和 `X-Trace-ID`。

### 订单创建/提交失败

```bash
cd cursor_sh/backend
tail -100 logs/order/order_$(date +%F).log
rg "order_created|order_updated|order_status_updated|POST /api/orders" logs/order logs/error
```

### AI 聊天失败

```bash
cd cursor_sh/backend
tail -100 logs/ai/ai_$(date +%F).log
rg "ai_.*failed|_provider_call_failed|retrying|timeout|Timeout" logs/ai logs/error
```

如果需要看聊天 JSON 归档：

```bash
cd cursor_sh/backend
find logs/ai_sessions -type f | tail
```

### 上传/文件访问失败

```bash
cd cursor_sh/backend
rg "POST /api/upload|oss_.*failed|upload|preview_uploaded" logs/order logs/system logs/error
```

同时确认：

- 本地文件模式：`UPLOAD_DIR` 是否可写。
- OSS 模式：`OSS_ENABLED`、bucket、endpoint、access key 是否正确。

### 前端页面打不开或 API 502

```bash
docker compose ps
docker compose logs -f frontend
docker compose logs -f backend
curl -i http://127.0.0.1:8080/api/health
```

裸机再查：

```bash
nginx -t
journalctl -fu order-api
journalctl -fu caddy
```

## 10. Debug 结束后的恢复

排查结束后确认：

- `LOG_LEVEL` 从 `DEBUG` 改回 `INFO`。
- 临时加入的高频日志已删除或降级。
- 没有把真实 `.env`、token、手机号、验证码、客户资料内容贴到文档或提交到 Git。
- 如果改过部署配置，重启后确认健康检查通过：

```bash
docker compose ps
curl -i http://127.0.0.1:8080/api/health
```

## 11. 每次上线检查清单

上线前先确认发布范围：

- `git status --short`：看清楚本次会发布哪些未提交/已修改文件。
- 数据库迁移：确认新增 Alembic migration 是否必须上线，生产发布必须执行 `alembic upgrade head`。
- 环境变量：确认 external/internal 使用的 env 文件路径正确，真实 `.env*` 不通过 rsync 覆盖。
- 业务知识目录：确认 `cursor_sh/hermes_skills/` 仍然在服务器保留，并且发布脚本排除了该目录。
- 外部服务：短信、OSS、AI/Hermes 等关键配置只检查 key 名、endpoint、模板号、开关状态，不把密钥写进文档或日志。
- 回退准备：确认发布脚本会先生成远端备份包，且 `scripts/rollback.sh list production` 能看到最近备份。

发布命令：

```bash
CONFIRM_PRODUCTION=production bash scripts/release.sh production
```

发布过程中重点看：

- external 先发布并执行数据库迁移。
- internal 后发布，不重复跑迁移。
- `docker compose build` 必须成功。
- `docker compose up -d --remove-orphans` 后健康检查必须成功。
- 如果刚重启时出现 `Recv failure: Connection reset by peer`，等待重试结果；最终 `/api/health` 成功才算通过。

发布后两台机器都要检查：

```bash
ssh -o ConnectTimeout=10 root@8.141.111.94 'cd /root/service/anti_pro && docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" && curl -fsS http://127.0.0.1:8080/api/health'
ssh -o ConnectTimeout=10 root@101.201.58.68 'cd /root/service/anti_pro && docker ps --format "table {{.Names}}\t{{.Status}}\t{{.Ports}}" && curl -fsS http://127.0.0.1:8080/api/health'
```

数据库版本检查：

```bash
ssh -o ConnectTimeout=10 root@8.141.111.94 'cd /root/service/anti_pro && BACKEND_ENV_FILE=./cursor_sh/backend/.env.production.external docker compose run --rm backend alembic current'
ssh -o ConnectTimeout=10 root@101.201.58.68 'cd /root/service/anti_pro && BACKEND_ENV_FILE=./cursor_sh/backend/.env.internal docker compose run --rm backend alembic current'
```

当前期望版本：

```text
0004 (head)
```

Creative Agent / Hermes 检查：

```bash
ssh -o ConnectTimeout=10 root@101.201.58.68 'cd /root/service/anti_pro && docker exec anti-pro-backend python -c "import asyncio; from app.services.creative_agent_service import get_hermes_status; data=asyncio.run(get_hermes_status()); print({k:data.get(k) for k in [\"enabled\", \"healthy\", \"model\", \"creative_profile\", \"skills_dir\"]}); print(data.get(\"providers\"))"'
```

期望结果：

- `enabled=True`
- `healthy=True`
- `creative_profile=creative-orchestrator`
- `skills_dir=./hermes_skills`
- `hermes` 的 `available=True`、`default=True`
- `direct_ai` 可用但不是默认，作为兜底。

skills 目录检查：

```bash
ssh -o ConnectTimeout=10 root@101.201.58.68 'cd /root/service/anti_pro && find cursor_sh/hermes_skills -maxdepth 2 -type f | head -20'
```

至少应能看到：

```text
cursor_sh/hermes_skills/creative-orchestrator/SKILL.md
cursor_sh/hermes_skills/creative-iteration-loop/SKILL.md
cursor_sh/hermes_skills/creative-rubric-evaluator/SKILL.md
```

短信链路检查：

- 不默认发真实短信，避免浪费和打扰用户。
- 如果本次改了短信代码、模板、签名或 env，再用明确授权的手机号做一次发送 + 验证闭环。
- 成功日志里 provider 应是新链路：`aliyun_dysmsapi`。
- 验证码只能用于当次测试，不要写进提交、文档或长期日志。

回退检查：

```bash
bash scripts/rollback.sh list production
```

确认 external/internal 都有本次发布前的备份包，例如：

```text
YYYYMMDD-HHMMSS-production_external.tar.gz
YYYYMMDD-HHMMSS-production_internal.tar.gz
```

需要代码回退时：

```bash
CONFIRM_PRODUCTION=production bash scripts/rollback.sh production
```

注意：

- 回退脚本回退代码和服务文件，不自动降数据库版本。
- 如果本次发布包含不可逆数据库结构变化，回退前要先确认旧代码能兼容当前数据库。
- 回退后仍要重新跑容器状态、`/api/health`、Hermes 状态和关键业务链路检查。
