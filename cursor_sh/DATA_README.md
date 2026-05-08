# Data README

This document describes where system data is stored, what is in the database, and the simplest ways to migrate the whole system.

## Storage Map

| Data | Storage | Default location / service | Notes |
| --- | --- | --- | --- |
| Business data | Main SQL database | SQLite `backend/app.db` by default, or MySQL/RDS when `DB_TYPE=mysql` or `DATABASE_URL` is set | Users, orders, files metadata, assignments, workflow, notifications, AI chat records, memory, security events |
| Audit logs | Separate SQL database | SQLite `backend/audit.db` by default, controlled by `AUDIT_DATABASE_URL` | Operation logs are physically separated from the business DB |
| Uploaded files | Local filesystem or Aliyun OSS | Local: `backend/uploads`; OSS: configured bucket | Database stores file metadata and URL/object key, not the binary content |
| Runtime logs | Local filesystem | `backend/logs`, controlled by `LOG_DIR` | Rotated application logs; useful for debugging, not required for business recovery |
| Environment/config secrets | Env files | `backend/.env`, `.env.external`, `.env.internal` | Contains DB credentials, JWT secrets, OSS/SMS/AI keys; must be migrated securely |
| Frontend browser state | Browser localStorage/sessionStorage | User's browser | Tokens, cached user info, mock data in dev mode, AI draft/session history cache |
| Built frontend assets | Docker image / `dist` | Built into `anti_pro-frontend` image | Rebuildable from source; not primary data |

## Configuration That Decides Storage

Important backend env keys:

- `DATABASE_URL`: full DB connection string. Highest priority.
- `DB_TYPE`: `sqlite` or `mysql` when `DATABASE_URL` is empty.
- `DB_NAME`, `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_CHARSET`: used to build MySQL/RDS URL.
- `AUDIT_DATABASE_URL`: audit database URL. Default is `sqlite+aiosqlite:///./audit.db`.
- `UPLOAD_DIR`: local upload directory. Default `./uploads`.
- `OSS_ENABLED`: when `true`, upload APIs write files to Aliyun OSS instead of local disk.
- `OSS_BUCKET_NAME`, `OSS_ENDPOINT`, `OSS_ACCESS_KEY_ID`, `OSS_ACCESS_KEY_SECRET`: OSS connection.
- `LOG_DIR`: runtime log directory. Default `./logs`.

The Docker compose file mounts backend file data:

```yaml
volumes:
  - ./uploads:/app/uploads
  - ./logs:/app/logs
```

So local uploads/logs persist outside the container. SQLite DB files also live in the backend working directory when SQLite mode is used.

## Main Database

The main database uses SQLAlchemy models under `backend/app/models`. In development it is SQLite; in production it can be MySQL/RDS.

### `users`

Customer accounts and enterprise verification.

Columns:

- `id`: primary key.
- `username`: unique login name.
- `password_hash`: hashed password.
- `email`, `phone`: contact fields; `phone` is unique when supported by the DB.
- `role`: usually `user`.
- `real_name`, `company`, `address`, `avatar`.
- `is_active`.
- `enterprise_status`: `none`, `pending`, `approved`, `rejected`.
- `enterprise_name`, `business_license_url`, `enterprise_reject_reason`.
- `enterprise_submitted_at`, `enterprise_reviewed_at`.
- `register_ip`, `register_user_agent`, `last_login_at`, `last_login_ip`.
- `created_at`, `updated_at`.

### `admins`

Admin accounts.

Columns:

- `id`, `username`, `password_hash`.
- `email`, `phone`, `real_name`, `avatar`.
- `is_active`.
- `created_at`, `updated_at`.

### `staff_members`

Designer/staff accounts.

Columns:

- `id`, `username`, `password_hash`.
- `email`, `phone`, `real_name`, `company`, `avatar`.
- `is_active`.
- `created_at`, `updated_at`.

### `contractors`

Contractor accounts.

Columns:

- `id`, `username`, `password_hash`.
- `email`, `phone`, `real_name`, `company`, `address`.
- `specialty`, `expertise`.
- `showcase_cases`: JSON list of showcase videos/cases.
- `avatar`, `is_active`.
- `created_at`, `updated_at`.

### `contractor_invitations`

One-time contractor registration invitation links.

Columns:

- `id`.
- `token`: unique invitation token.
- `created_by`: admin ID.
- `used_by`: contractor ID after registration.
- `is_used`.
- `note`.
- `expires_at`.
- `created_at`.

### `orders`

Order header plus order-specific JSON payload.

Columns:

- `id`.
- `order_number`: unique business order number.
- `order_type`: `video_purchase`, `ai_3d_custom`, `digital_art`.
- `status`: `draft`, `pending_assign`, `pending_contract`, `in_production`, `pending_review`, `preview_ready`, `review_rejected`, `revision_needed`, `final_preview`, `completed`, `cancelled`.
- `user_id`: customer ID.
- `revision_count`.
- `order_data`: JSON payload for the selected order type.
- `design_plan`: JSON/text design-plan payload written before assignment.
- `created_at`, `updated_at`.

`order_data` contains fields such as brand/media requirements, `scenePhotos`, preview metadata, digital-art materials, and video-purchase parameters. File binaries are not stored in this JSON; only metadata and URLs are.

### `order_assignees`

Many-to-many mapping between orders and staff.

Columns:

- `order_id`.
- `assignee_id`: staff member ID.
- `created_at`.

Primary key: `(order_id, assignee_id)`.

### `files`

File metadata attached to orders.

Columns:

- `id`.
- `order_id`.
- `file_type`: `scene_photo`, `material`, `preview`.
- `name`.
- `size`.
- `mime_type`.
- `url`: local upload URL or OSS URL/object reference depending on mode.
- `uploaded_at`.

The actual file is in `backend/uploads` when `OSS_ENABLED=false`, or in OSS when `OSS_ENABLED=true`.

### `feedbacks`

Customer feedback on orders or contractor deliverables.

Columns:

- `id`.
- `order_id`.
- `deliverable_id`: optional link to `contractor_deliverables`.
- `content`.
- `type`: `approval` or `revision`.
- `created_by`: customer user ID.
- `created_at`.

### `workflow_stage_configs`

Global workflow stage configuration.

Columns:

- `id`.
- `name`.
- `default_days`.
- `display_order`.
- `review_items`: JSON list of self-review items.
- `is_active`.
- `created_at`, `updated_at`.

### `contractor_assignments`

Assignment records from admin to contractor.

Columns:

- `id`.
- `order_id`.
- `contractor_id`.
- `assigned_by`: admin ID.
- `status`: `pending`, `accepted`, `rejected`, `in_progress`, `completed`, `cancelled`.
- `reject_reason`.
- `schedule`: JSON stage schedule generated from workflow config.
- `current_stage_order`.
- `assigned_at`, `responded_at`, `completed_at`.

### `contractor_deliverables`

Contractor deliverables for each workflow stage, including version history.

Columns:

- `id`.
- `assignment_id`.
- `stage_config_id`.
- `stage_name`.
- `stage_order`.
- `version`.
- `parent_id`.
- `files`: JSON list of uploaded deliverable files.
- `description`.
- `self_review_checks`: JSON object.
- `status`: `draft`, `submitted`, `admin_approved`, `admin_rejected`.
- `admin_review_note`, `admin_reviewed_by`, `admin_reviewed_at`.
- `is_published_to_user`.
- `published_note`, `published_at`, `published_by`.
- `admin_comments`: JSON list of admin comments.
- `created_at`, `updated_at`.

### `notifications`

In-app notifications for customers, admins, staff, and contractors.

Columns:

- `id`.
- `user_id`: ID of recipient. It may point to users/admins/staff/contractors depending on ID prefix and route.
- `order_id`: optional related order.
- `type`: notification type, such as `order_status_changed`, `contractor_assignment`, `deliverable_submitted`, `system_notice`.
- `title`.
- `content`.
- `is_read`.
- `created_at`.
- `read_at`.

### `announcements`

System announcements.

Columns:

- `id`.
- `title`.
- `content`.
- `is_active`.
- `created_at`.
- `updated_at`.
- `created_by`: admin ID.

### `homepage_bars`

Public homepage top marketing bar configuration.

Columns:

- `id`: singleton config ID, normally `homepage_top_bar`.
- `title`: bar copy shown on the public homepage.
- `button_text`: CTA button text.
- `pdf_url`: local URL in local mode, or OSS object key in OSS mode. API responses sign it before returning.
- `pdf_name`: display name of the uploaded PDF.
- `pdf_object_key`: OSS object key for the PDF when OSS is enabled.
- `image_url`: optional local image URL in local mode, or OSS object key in OSS mode. API responses sign it before returning.
- `image_object_key`: OSS object key for the thumbnail/image when OSS is enabled.
- `is_active`: whether the bar should be shown.
- `created_by`: admin ID.
- `created_at`, `updated_at`.

### `security_events`

Registration/login/security telemetry.

Columns:

- `id`.
- `event_type`: `register_success`, `register_fail`, `register_bot_blocked`, `login_success`, `login_fail`, `password_reset`, `sms_sent`.
- `user_id`, `phone`, `username`.
- `client_ip`, `user_agent`.
- `behavior_data`: JSON timing/fingerprint data.
- `block_reason`.
- `fail_reason`.
- `created_at`.

### `user_memories`

AI agent cross-session memory per customer.

Columns:

- `id`.
- `user_id`: unique customer ID.
- `company_info`: JSON company profile from crawl/LLM.
- `screen_resources`: JSON screen/media resources.
- `project_preferences`: JSON preference summary.
- `past_projects`: JSON order/project summaries.
- `interaction_stats`: JSON counters/timestamps.
- `agent_notes`: free-form notes.
- `created_at`, `updated_at`.

### `ai_chat_sessions`

AI chat session metadata.

Columns:

- `id`: session ID.
- `user_id`.
- `username`.
- `session_type`: `requirement`, `order`, `general`, etc.
- `business_type`: `ai_3d_custom`, `video_purchase`, `digital_art`, etc.
- `title`.
- `message_count`.
- `created_at`, `updated_at`.

### `ai_chat_messages`

AI chat message records.

Columns:

- `id`: autoincrement integer.
- `session_id`.
- `role`: `user`, `assistant`, `system`.
- `content`.
- `metadata_json`: JSON extra metadata.
- `created_at`.

## Audit Database

The audit DB is configured by `AUDIT_DATABASE_URL`; default is `backend/audit.db`.

### `operation_logs`

Operation audit records.

Columns:

- `id`.
- `trace_id`.
- `user_id`, `username`.
- `type`: `api_call` or `frontend_action`.
- `module`: `Auth`, `Order`, `Workspace`, `AI`, etc.
- `action`.
- `ip_address`.
- `user_agent`.
- `payload`: sanitized JSON string.
- `response_status`.
- `duration_ms`.
- `created_at`.

## File Storage

### Local upload mode

When `OSS_ENABLED=false`, files are written under:

- `backend/uploads/site_photos/{user_id}/...`
- `backend/uploads/deliverables/{user_id}/...`
- `backend/uploads/showcase_cases/{user_id}/...`
- `backend/uploads/enterprise/{user_id}/...`

The backend mounts `/uploads` statically only in local mode.

### OSS mode

When `OSS_ENABLED=true`, upload APIs write to Aliyun OSS and return:

- `url`: signed URL or file URL.
- `file_url`: compatibility alias.
- `object_key`: stable OSS object key.
- `filename`, `size`, `uploadedAt`.

The database stores metadata and references. The OSS bucket stores the actual file bytes. When migrating to a new OSS bucket/account, copy the objects and keep `object_key` paths stable if possible.

## Runtime Logs

Runtime logs live under `backend/logs` by module:

- `auth`
- `order`
- `notification`
- `workspace`
- `ai`
- `staff`
- `contractor`
- `system`
- `error`
- `crash`

Logs are useful for troubleshooting but are not required for business-data restoration. Audit logs in `audit.db` are the structured compliance/audit data.

## Frontend Browser Storage

Frontend browser storage is client-side and not part of server migration.

Known keys:

- `token`: JWT access token.
- `user`: cached current user object.
- `last_read_announcement_id`: announcement read marker.
- `ai_draft_order`: temporary AI order draft in `sessionStorage`.
- AI chat history key generated by `AIChatAssistant.getHistoryKey()`.
- Dev/mock mode keys: `mockUsers`, `mockTasks`, `mockOrders`, `mockStaff`, `mockFiles`, `auth`.

Production business data should live on the backend, not in browser storage.

## Migration Strategy

### Easiest full-system migration: copy the deployment directory

This is the simplest path when the backend uses SQLite and local uploads.

On the old server:

```bash
cd /root/service
docker compose -f /root/service/anti_pro/docker-compose.yml down
tar czf /root/anti_pro_full_$(date +%Y%m%d_%H%M%S).tgz anti_pro
```

Copy the archive to the new server:

```bash
scp /root/anti_pro_full_YYYYMMDD_HHMMSS.tgz root@NEW_SERVER:/root/service/
```

On the new server:

```bash
cd /root/service
tar xzf anti_pro_full_YYYYMMDD_HHMMSS.tgz
cd anti_pro
docker compose up -d
docker compose ps
curl -sS http://127.0.0.1/api/health || curl -sS http://127.0.0.1:8080/api/health
```

This preserves:

- source/deployment files;
- `.env` files;
- SQLite DB files (`app.db`, `audit.db`);
- local uploads;
- logs;
- compose configuration.

Adjust the compose path if the target server stores `docker-compose.yml` under `cursor_sh/backend`.

### Production migration when using MySQL/RDS and OSS

If the production environment uses RDS and OSS, most persistent data is outside the ECS server.

To migrate ECS only:

1. Copy source/deployment files and `.env`.
2. Rebuild or copy Docker images.
3. Keep `DB_*`/`DATABASE_URL` pointing to the same RDS.
4. Keep `OSS_*` pointing to the same bucket.
5. Run `docker compose up -d`.

To migrate everything to a new RDS/OSS:

1. Dump and import MySQL:

```bash
mysqldump -h OLD_RDS_HOST -u USER -p --single-transaction --routines --triggers DB_NAME > anti_pro.sql
mysql -h NEW_RDS_HOST -u USER -p NEW_DB_NAME < anti_pro.sql
```

2. Copy OSS objects with `ossutil` or Aliyun bucket replication. Keep object keys the same when possible.
3. Update `.env` with the new RDS and OSS settings.
4. Deploy containers and run a health check.

### Current Online Storage Check

Last verified environment:

- External server: `47.114.118.52`
- Internal server: `116.62.88.121`
- Main DB: Aliyun RDS MySQL, database `unique_video_test`
- Audit DB: Aliyun RDS MySQL, database `unique_video_audit`
- OSS: enabled, bucket `uv-test`, endpoint `oss-cn-hangzhou.aliyuncs.com`
- Local uploads on both ECS servers: only `.gitkeep`; no real uploaded files.
- Local online `app.db`: not used as the active data source.

Observed RDS row counts at verification time:

```text
MAIN.admins=1
MAIN.ai_chat_messages=105
MAIN.ai_chat_sessions=9
MAIN.announcements=0
MAIN.contractor_assignments=1
MAIN.contractor_deliverables=1
MAIN.contractor_invitations=1
MAIN.contractors=1
MAIN.feedbacks=0
MAIN.files=2
MAIN.notifications=9
MAIN.order_assignees=0
MAIN.orders=4
MAIN.security_events=5
MAIN.staff_members=0
MAIN.user_memories=3
MAIN.users=4
MAIN.workflow_stage_configs=5
AUDIT.operation_logs=414
```

Known caveat:

- `files_total=2`
- `files_local_url=2`
- `orders_with_local_upload_ref=2`

Those two file records still point to `/uploads/...` legacy local paths:

- `ComfyUI_00004_sqlnb_1770019932.png`
- `WechatIMG203.jpeg`

The files do not exist in the online ECS `uploads` directories, so they are likely old test/legacy references. Before migrating to a new Aliyun account, either clean these records if they are test data, or find the original files, upload them to OSS, and update the DB references.

## Migration To Another Aliyun Account

This section is the recommended runbook when moving the whole production system to a different Aliyun account.

Target resources to prepare:

- New ECS servers, or one new ECS if the deployment is being consolidated.
- New RDS MySQL instance.
- Two databases on the new RDS:
  - `unique_video_test` or a new chosen main DB name.
  - `unique_video_audit` or a new chosen audit DB name.
- New OSS bucket.
- New RAM AccessKey with enough permissions for OSS upload/signing and any SMS/NLS services that remain enabled.
- Security group and RDS whitelist allowing the new ECS to connect to the new RDS.

### 1. Freeze Writes

To avoid data drifting during migration, stop old containers or put the system into a short maintenance window.

On each old ECS:

```bash
cd /root/service/anti_pro
docker compose down
```

If the effective compose file is under `cursor_sh/backend`, use:

```bash
cd /root/service/anti_pro/cursor_sh/backend
docker compose down
```

### 2. Confirm Current Storage Mode

Run on each old ECS. These commands print only storage-related config and avoid secrets.

External:

```bash
ssh root@47.114.118.52 '
cd /root/service/anti_pro/cursor_sh/backend
printf "ENV_STORAGE_KEYS:\n"
awk -F= '"'"'
NF && $1 !~ /^#/ && $1 ~ /^(DB_TYPE|DB_HOST|DB_NAME|DATABASE_URL|AUDIT_DATABASE_URL|OSS_ENABLED|OSS_BUCKET_NAME|OSS_ENDPOINT|UPLOAD_DIR|LOG_DIR|DEPLOYMENT_MODE)$/ {
  if ($1=="DATABASE_URL" || $1=="AUDIT_DATABASE_URL") print $1"=<set>";
  else print $1"="$2
}
'"'"' .env | sort
printf "LOCAL_DATA_FILES:\n"
find . -maxdepth 2 \( -name "*.db" -o -name "uploads" -o -name "logs" \) -print -exec du -sh {} \; 2>/dev/null
'
```

Internal:

```bash
ssh -i /path/to/ssh.pem root@116.62.88.121 '
cd /root/service/anti_pro/cursor_sh/backend
printf "ENV_STORAGE_KEYS:\n"
awk -F= '"'"'
NF && $1 !~ /^#/ && $1 ~ /^(DB_TYPE|DB_HOST|DB_NAME|DATABASE_URL|AUDIT_DATABASE_URL|OSS_ENABLED|OSS_BUCKET_NAME|OSS_ENDPOINT|UPLOAD_DIR|LOG_DIR|DEPLOYMENT_MODE)$/ {
  if ($1=="DATABASE_URL" || $1=="AUDIT_DATABASE_URL") print $1"=<set>";
  else print $1"="$2
}
'"'"' .env | sort
printf "LOCAL_DATA_FILES:\n"
find . -maxdepth 2 \( -name "*.db" -o -name "uploads" -o -name "logs" \) -print -exec du -sh {} \; 2>/dev/null
'
```

Expected production result:

- `DB_TYPE=mysql`
- `DATABASE_URL=<set>` or MySQL fields point to RDS.
- `AUDIT_DATABASE_URL=<set>` and points to MySQL/RDS, not SQLite.
- `OSS_ENABLED=True`
- Local `uploads` has no real files except `.gitkeep`.

### 3. Export Old RDS Databases

Run from a machine that can access the old RDS. Prefer the old ECS or a temporary migration host inside the same VPC.

Main DB:

```bash
mysqldump \
  -h OLD_RDS_HOST \
  -P 3306 \
  -u OLD_DB_USER \
  -p \
  --single-transaction \
  --routines \
  --triggers \
  --default-character-set=utf8mb4 \
  unique_video_test \
  > unique_video_test.sql
```

Audit DB:

```bash
mysqldump \
  -h OLD_RDS_HOST \
  -P 3306 \
  -u OLD_DB_USER \
  -p \
  --single-transaction \
  --routines \
  --triggers \
  --default-character-set=utf8mb4 \
  unique_video_audit \
  > unique_video_audit.sql
```

Optional compression:

```bash
gzip -9 unique_video_test.sql
gzip -9 unique_video_audit.sql
```

### 4. Create New RDS Databases

On the new RDS, create the target databases with `utf8mb4`.

```sql
CREATE DATABASE unique_video_test CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
CREATE DATABASE unique_video_audit CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

Create or grant a DB user:

```sql
CREATE USER 'anti_pro_user'@'%' IDENTIFIED BY 'CHANGE_ME_STRONG_PASSWORD';
GRANT ALL PRIVILEGES ON unique_video_test.* TO 'anti_pro_user'@'%';
GRANT ALL PRIVILEGES ON unique_video_audit.* TO 'anti_pro_user'@'%';
FLUSH PRIVILEGES;
```

Use a stronger user/host restriction in production if possible.

### 5. Import Into New RDS

If dumps are compressed:

```bash
gunzip unique_video_test.sql.gz
gunzip unique_video_audit.sql.gz
```

Import:

```bash
mysql \
  -h NEW_RDS_HOST \
  -P 3306 \
  -u NEW_DB_USER \
  -p \
  --default-character-set=utf8mb4 \
  unique_video_test \
  < unique_video_test.sql

mysql \
  -h NEW_RDS_HOST \
  -P 3306 \
  -u NEW_DB_USER \
  -p \
  --default-character-set=utf8mb4 \
  unique_video_audit \
  < unique_video_audit.sql
```

### 6. Copy OSS Objects

Recommended: use Aliyun OSS cross-account bucket replication if available. It is safer for large buckets.

For a scriptable copy, install and configure `ossutil` profiles for both accounts, then run one of the following patterns.

Same region, copy bucket to bucket:

```bash
ossutil64 cp \
  oss://OLD_BUCKET/ \
  oss://NEW_BUCKET/ \
  -r \
  --update
```

If using named config files:

```bash
ossutil64 -c old-account-config ls oss://OLD_BUCKET/
ossutil64 -c new-account-config ls oss://NEW_BUCKET/
```

When copying between accounts with one command is not practical, sync via local temporary storage:

```bash
mkdir -p /tmp/anti_pro_oss
ossutil64 -c old-account-config cp oss://OLD_BUCKET/ /tmp/anti_pro_oss/ -r --update
ossutil64 -c new-account-config cp /tmp/anti_pro_oss/ oss://NEW_BUCKET/ -r --update
```

Important:

- Preserve object key paths.
- If object keys stay the same, database `object_key` references continue to work.
- If object keys change, update DB references in fields such as `files.url`, `orders.order_data`, `users.business_license_url`, `contractor_deliverables.files`, and `contractors.showcase_cases`.

### 7. Check Legacy Local File References

Before cutover, check whether any DB records still reference `/uploads/...`.

Run inside an old or new backend container that points to the target DB:

```bash
docker exec -i anti-pro-backend python - <<'PY'
import asyncio
from sqlalchemy import text
from app.database import engine

queries = [
    ("files_total", "SELECT COUNT(*) FROM files"),
    ("files_local_url", "SELECT COUNT(*) FROM files WHERE url LIKE '/uploads/%'"),
    ("users_license_local", "SELECT COUNT(*) FROM users WHERE business_license_url LIKE '/uploads/%'"),
    ("orders_with_local_upload_ref", "SELECT COUNT(*) FROM orders WHERE CAST(order_data AS CHAR) LIKE '%/uploads/%'"),
    ("deliverables_with_local_upload_ref", "SELECT COUNT(*) FROM contractor_deliverables WHERE CAST(files AS CHAR) LIKE '%/uploads/%'"),
    ("contractors_with_local_upload_ref", "SELECT COUNT(*) FROM contractors WHERE CAST(showcase_cases AS CHAR) LIKE '%/uploads/%'"),
]

async def main():
    async with engine.connect() as conn:
        for label, sql in queries:
            value = (await conn.execute(text(sql))).scalar()
            print(f"{label}={value}")
        rows = (await conn.execute(text("""
            SELECT file_type, name, url
            FROM files
            WHERE url LIKE '/uploads/%'
            ORDER BY uploaded_at DESC
        """))).fetchall()
        for row in rows:
            print("local_file_ref=" + "|".join(str(x) for x in row))

asyncio.run(main())
PY
```

Expected ideal result:

```text
files_local_url=0
users_license_local=0
orders_with_local_upload_ref=0
deliverables_with_local_upload_ref=0
contractors_with_local_upload_ref=0
```

If local references are test data, delete or update those records. If they are real business files, upload the original files to OSS first and then update their URL/object references.

### 8. Update New ECS `.env`

On the new ECS, update `backend/.env` for each deployment mode.

Main DB:

```env
DB_TYPE=mysql
DB_HOST=NEW_RDS_HOST
DB_PORT=3306
DB_NAME=unique_video_test
DB_USER=NEW_DB_USER
DB_PASSWORD=NEW_DB_PASSWORD
DB_CHARSET=utf8mb4
```

Audit DB:

```env
AUDIT_DATABASE_URL=mysql+aiomysql://NEW_DB_USER:NEW_DB_PASSWORD@NEW_RDS_HOST:3306/unique_video_audit?charset=utf8mb4
```

OSS:

```env
OSS_ENABLED=True
OSS_BUCKET_NAME=NEW_BUCKET
OSS_ENDPOINT=oss-cn-hangzhou.aliyuncs.com
OSS_ACCESS_KEY_ID=NEW_ACCESS_KEY_ID
OSS_ACCESS_KEY_SECRET=NEW_ACCESS_KEY_SECRET
```

Keep or reset these deliberately:

- `SECRET_KEY`
- `JWT_SECRET_KEY`
- `SMS_*`
- `AI_*`
- `SMTP_*`
- `DEPLOYMENT_MODE`
- `CONTRACTOR_BASE_URL`

If you reset `JWT_SECRET_KEY`, all existing browser login tokens become invalid, which is usually acceptable during migration.

### 9. Deploy On New ECS

Copy code or use the existing local Docker build/deploy flow.

Manual compose startup:

```bash
cd /root/service/anti_pro
docker compose up -d
docker compose ps
```

If compose lives under `cursor_sh/backend`:

```bash
cd /root/service/anti_pro/cursor_sh/backend
docker compose up -d
docker compose ps
```

Health check:

```bash
curl -sS http://127.0.0.1/api/health || curl -sS http://127.0.0.1:8080/api/health
```

Expected:

```json
{"status":"ok","app":"AI设计任务管理系统"}
```

### 10. Confirm New RDS Row Counts

Run inside the new backend container:

```bash
docker exec -i anti-pro-backend python - <<'PY'
import asyncio
from sqlalchemy import text
from app.database import engine
from app.audit_database import audit_engine

async def dump(label, eng):
    async with eng.connect() as conn:
        rows = (await conn.execute(text(
            "SELECT table_name FROM information_schema.tables "
            "WHERE table_schema = DATABASE() ORDER BY table_name"
        ))).fetchall()
        tables = [r[0] for r in rows]
        print(label + "_TABLES=" + ",".join(tables))
        for table in tables:
            safe = "".join(ch for ch in table if ch.isalnum() or ch == "_")
            count = (await conn.execute(text("SELECT COUNT(*) FROM " + safe))).scalar()
            print(f"{label}.{safe}={count}")

async def main():
    await dump("MAIN", engine)
    await dump("AUDIT", audit_engine)

asyncio.run(main())
PY
```

Compare the output with the old RDS row counts before cutover. Counts should match unless new writes happened after the old dump.

### 11. Confirm Runtime Storage Settings

Run inside the new backend container:

```bash
docker exec anti-pro-backend python - <<'PY'
from app.config import settings

def mask_url(url):
    if not url:
        return "<empty>"
    if url.startswith("mysql") and "@" in url:
        return "mysql://<redacted>@" + url.split("@", 1)[1]
    if url.startswith("sqlite"):
        return "sqlite"
    return "<set>"

print("DB_IS_MYSQL=" + str(settings.is_mysql))
print("DATABASE_URL=" + mask_url(settings.database_url))
print("AUDIT_DATABASE_URL=" + mask_url(settings.AUDIT_DATABASE_URL))
print("OSS_ENABLED=" + str(settings.OSS_ENABLED))
print("OSS_BUCKET_NAME=" + settings.OSS_BUCKET_NAME)
print("OSS_ENDPOINT=" + settings.OSS_ENDPOINT)
print("UPLOAD_DIR=" + settings.UPLOAD_DIR)
print("LOG_DIR=" + settings.LOG_DIR)
print("DEPLOYMENT_MODE=" + settings.DEPLOYMENT_MODE)
PY
```

Expected:

- `DB_IS_MYSQL=True`
- `DATABASE_URL` points to the new RDS host.
- `AUDIT_DATABASE_URL` points to the new RDS host.
- `OSS_ENABLED=True`
- `OSS_BUCKET_NAME` is the new bucket.

### 12. Confirm Uploads Go To New OSS

Use the UI to upload a small test image/file, then check:

```bash
docker exec -i anti-pro-backend python - <<'PY'
import asyncio
from sqlalchemy import text
from app.database import engine

async def main():
    async with engine.connect() as conn:
        rows = (await conn.execute(text("""
            SELECT id, name, url
            FROM files
            ORDER BY uploaded_at DESC
            LIMIT 5
        """))).fetchall()
        for row in rows:
            print("|".join(str(x) for x in row))

asyncio.run(main())
PY
```

The newest file should not use `/uploads/...`. It should contain an OSS-style URL/object reference, depending on the upload path and response handling.

Also check the new bucket:

```bash
ossutil64 -c new-account-config ls oss://NEW_BUCKET/ -r | tail
```

### 13. Cut Over DNS / Entry Points

After validation:

1. Point DNS or load balancer to the new ECS public IP.
2. Confirm HTTP/HTTPS routes.
3. Re-test login, order list, order detail, file preview, AI chat, contractor/admin flows.
4. Keep the old RDS/OSS/ECS read-only for a rollback window.

### 14. Rollback Plan

Before DNS cutover, rollback is simply:

- keep DNS pointing to old ECS;
- keep old RDS/OSS untouched;
- restart old containers if they were stopped.

After DNS cutover:

- point DNS back to old ECS;
- stop new containers;
- investigate any writes that happened on the new RDS during the partial cutover.

For a clean rollback window, avoid allowing writes on both old and new systems at the same time.

### SQLite to MySQL/RDS migration

There is an existing script:

```bash
cd backend
python scripts/migrate_to_rds.py
```

However, this script currently migrates only an early subset of tables:

- `users`
- `orders`
- `order_assignees`
- `files`
- `feedbacks`
- `notifications`

It does not cover newer tables such as admins, staff, contractors, workflow, deliverables, AI chat, user memory, announcements, security events, and audit logs. Do not use it for full-system migration unless it is updated first.

For a full SQLite to MySQL migration, prefer one of:

- update `scripts/migrate_to_rds.py` to include all current tables in dependency order;
- use a tested SQLite-to-MySQL migration tool and then verify row counts table by table;
- keep SQLite and use the full-directory migration method above.

### Minimal backup set

If time is tight, back up at least:

- `backend/.env`, `.env.external`, `.env.internal`;
- `backend/app.db` if using SQLite;
- `backend/audit.db` if using SQLite audit DB;
- `backend/uploads` if `OSS_ENABLED=false`;
- RDS dump if `DB_TYPE=mysql`;
- OSS bucket objects if `OSS_ENABLED=true`;
- `backend/logs` if operational history is needed.

## Quick Verification After Migration

Run:

```bash
docker compose ps
curl -sS http://127.0.0.1/api/health || curl -sS http://127.0.0.1:8080/api/health
```

Then verify in the UI:

- customer login;
- admin login;
- staff/contractor login if enabled;
- order list and order detail;
- uploaded file links;
- AI chat and order draft creation;
- notifications;
- enterprise license image display.

## Notes

- Do not commit `.env`, DB files, uploads, or logs. They are intentionally ignored.
- Do not rely on Docker images as the only backup. Images contain code/runtime, not database contents or external OSS/RDS data.
- If two ECS servers are deployed separately, repeat the backup/migration check on both External and Internal servers. They may have different `.env` and `DEPLOYMENT_MODE` values.
