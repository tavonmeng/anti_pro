"""应用配置"""

try:
    from pydantic_settings import BaseSettings
except ImportError:
    from pydantic import BaseSettings
from typing import List, Union
try:
    from pydantic import field_validator
    def compat_validator(field):
        return field_validator(field, mode='before')
except ImportError:
    from pydantic import validator
    def compat_validator(field):
        return validator(field, pre=True)

import json
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用配置
    APP_NAME: str = "Unique Vision AI"
    APP_VERSION: str = "1.0.0"
    ENVIRONMENT: str = "development"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    API_DOCS_ENABLED: bool = False

    @compat_validator('DEBUG')
    @classmethod
    def parse_debug(cls, v):
        """兼容 DEBUG=release/prod/production 这类部署值。"""
        if isinstance(v, bool):
            return v
        if isinstance(v, str):
            value = v.strip().lower()
            if value in ("true", "1", "yes", "y", "on", "debug", "dev", "development"):
                return True
            if value in ("false", "0", "no", "n", "off", "release", "prod", "production"):
                return False
        return v
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 方式1: 直接指定完整连接串（优先级最高）
    #   SQLite:  sqlite+aiosqlite:///./app.db
    #   MySQL:   mysql+aiomysql://user:pass@host:3306/dbname
    DATABASE_URL: str = ""
    
    # 审计日志独立库，与主业务库物理隔离
    AUDIT_DATABASE_URL: str = "sqlite+aiosqlite:///./audit.db"
    
    # 方式2: 通过结构化字段自动拼接连接串（当 DATABASE_URL 为空时生效）
    DB_TYPE: str = "sqlite"              # sqlite / mysql
    DB_HOST: str = "localhost"           # RDS 内网地址，如: rm-xxxxx.mysql.rds.aliyuncs.com
    DB_PORT: int = 3306                  # MySQL 默认端口
    DB_NAME: str = "app"                 # 数据库名，SQLite 模式下为文件名(不含.db)
    DB_USER: str = ""                    # RDS 用户名
    DB_PASSWORD: str = ""                # RDS 密码
    DB_CHARSET: str = "utf8mb4"          # MySQL 字符集
    
    # 连接池配置（MySQL RDS 专用）
    DB_POOL_SIZE: int = 5                # 连接池常驻连接数
    DB_MAX_OVERFLOW: int = 10            # 最大溢出连接数
    DB_POOL_TIMEOUT: int = 30            # 获取连接超时（秒）
    DB_POOL_RECYCLE: int = 1800          # 连接回收时间（秒），RDS 推荐 1800
    DB_POOL_PRE_PING: bool = True        # 连接健康检查，防止 RDS 闲置断开
    AUTO_CREATE_TABLES: bool = False     # 生产环境应使用 Alembic，开发环境仍自动建表
    
    @property
    def database_url(self) -> str:
        """获取最终的数据库连接串"""
        # 优先使用直接指定的 DATABASE_URL
        if self.DATABASE_URL:
            return self.DATABASE_URL
        
        # 根据 DB_TYPE 自动拼接
        if (self.DB_TYPE or "").strip().lower() == "mysql":
            user = quote_plus(self.DB_USER)
            password = quote_plus(self.DB_PASSWORD)
            charset = quote_plus(self.DB_CHARSET or "utf8mb4")
            return (
                f"mysql+aiomysql://{user}:{password}"
                f"@{self.DB_HOST}:{self.DB_PORT}/{self.DB_NAME}"
                f"?charset={charset}"
            )
        else:
            # 默认 SQLite
            return f"sqlite+aiosqlite:///./{self.DB_NAME}.db"

    @property
    def audit_database_url(self) -> str:
        """获取审计日志数据库连接串。"""
        return self.AUDIT_DATABASE_URL or "sqlite+aiosqlite:///./audit.db"
    
    @property
    def is_mysql(self) -> bool:
        """判断当前是否使用 MySQL"""
        return self.database_url.startswith("mysql")

    @property
    def is_audit_mysql(self) -> bool:
        """判断审计日志库是否使用 MySQL/RDS。"""
        return self.audit_database_url.startswith("mysql")

    @property
    def deploy_mode(self) -> str:
        return (self.DEPLOYMENT_MODE or "all").strip().lower()

    @property
    def is_production(self) -> bool:
        return self.ENVIRONMENT.strip().lower() in ("prod", "production") or self.deploy_mode in ("external", "internal")

    @property
    def docs_enabled(self) -> bool:
        return self.API_DOCS_ENABLED or not self.is_production

    def validate_startup_config(self) -> None:
        """Fail fast when production-like deployments still use development settings."""
        if not self.is_production:
            return

        problems: list[str] = []
        weak_values = {
            "",
            "dev-secret-key-change-in-production",
            "dev-jwt-secret-key-change-in-production",
            "your-secret-key-change-in-production",
            "your-jwt-secret-key-change-in-production",
            "123456",
        }

        if self.DEBUG:
            problems.append("DEBUG must be false")
        if not self.is_mysql:
            problems.append("DB_TYPE/DATABASE_URL must use MySQL/RDS")
        if not self.DATABASE_URL and (self.DB_TYPE or "").strip().lower() == "mysql":
            if not all([self.DB_HOST, self.DB_NAME, self.DB_USER, self.DB_PASSWORD]):
                problems.append("DB_HOST/DB_NAME/DB_USER/DB_PASSWORD are required for MySQL/RDS")
        if self.LOG_DB_ENABLED and not self.is_audit_mysql:
            problems.append("AUDIT_DATABASE_URL must use MySQL/RDS when LOG_DB_ENABLED=true")
        if self.SECRET_KEY in weak_values or len(self.SECRET_KEY) < 32:
            problems.append("SECRET_KEY must be a strong non-default value")
        if self.JWT_SECRET_KEY in weak_values or len(self.JWT_SECRET_KEY) < 32:
            problems.append("JWT_SECRET_KEY must be a strong non-default value")
        if self.deploy_mode == "internal" and self.INIT_ADMIN_PASSWORD in weak_values:
            problems.append("INIT_ADMIN_PASSWORD must not be a default value")
        if self.SMS_ENABLED and not all([
            self.SMS_ACCESS_KEY_ID,
            self.SMS_ACCESS_KEY_SECRET,
            self.SMS_SIGN_NAME,
            self.SMS_TEMPLATE_CODE,
        ]):
            problems.append("SMS_ENABLED=true requires complete SMS credentials")
        if self.OSS_ENABLED and not all([
            self.OSS_ACCESS_KEY_ID,
            self.OSS_ACCESS_KEY_SECRET,
            self.OSS_BUCKET_NAME,
            self.OSS_ENDPOINT,
        ]):
            problems.append("OSS_ENABLED=true requires complete OSS credentials")
        if self.deploy_mode in ("all", "external") and not self.AI_API_KEY:
            problems.append("AI_API_KEY is required for production user-facing AI routes")
        origins = self.CORS_ORIGINS if isinstance(self.CORS_ORIGINS, list) else []
        if "*" in origins:
            problems.append("CORS_ORIGINS must not contain '*' in production")

        if problems:
            raise RuntimeError("Production configuration is unsafe: " + "; ".join(problems))
    
    # JWT 配置
    JWT_SECRET_KEY: str = "dev-jwt-secret-key-change-in-production"
    JWT_ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = 1440  # 24小时
    
    # CORS 配置
    CORS_ORIGINS: Union[List[str], str] = ["http://localhost:5173", "http://localhost:3000"]
    
    @compat_validator('CORS_ORIGINS')
    @classmethod
    def parse_cors_origins(cls, v):
        """解析 CORS_ORIGINS，支持 JSON 格式和逗号分隔的字符串"""
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            # 尝试解析 JSON
            try:
                return json.loads(v)
            except (json.JSONDecodeError, TypeError):
                # 如果不是 JSON，按逗号分隔
                return [origin.strip() for origin in v.split(',') if origin.strip()]
        return v
    
    # 文件上传配置
    UPLOAD_DIR: str = "./uploads"
    KNOWLEDGE_DIR: str = ""                   # AI 知识库目录（留空则自动使用 backend/app/knowledge/）
    MAX_FILE_SIZE: int = 209715200  # 200MB
    ALLOWED_FILE_TYPES: str = "image/jpeg,image/png,image/gif,video/mp4,application/zip,application/pdf"
    
    # 阿里云 OSS 配置
    OSS_ENABLED: bool = False
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_ENDPOINT: str = ""               # 如: oss-cn-hangzhou.aliyuncs.com
    OSS_PUBLIC_ENDPOINT: str = ""        # 浏览器访问用；留空则从 OSS_ENDPOINT 去掉 -internal
    OSS_SIGNED_URL_EXPIRES: int = 3600   # 签名 URL 有效期（秒），默认 1 小时
    
    # 阿里云短信服务（Dysmsapi - 短信验证码）配置
    SMS_ENABLED: bool = True
    SMS_ACCESS_KEY_ID: str = ""      # 可与 OSS 共用
    SMS_ACCESS_KEY_SECRET: str = ""
    SMS_SIGN_NAME: str = ""          # 短信签名 (如: "速通互联验证码")
    SMS_TEMPLATE_CODE: str = ""      # 模板CODE (如: "100001")
    SMS_REGION_ID: str = "cn-qingdao"
    SMS_CODE_LENGTH: int = 6         # 验证码长度
    SMS_VALID_TIME: int = 300        # 验证码有效期（秒）5分钟
    
    # 邮件配置
    SMTP_HOST: str = "smtp.qiye.aliyun.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "Unique Vision AI"
    SMTP_TIMEOUT: float = 20.0

    # 外部服务重试配置
    EXTERNAL_API_RETRY_ATTEMPTS: int = 3
    EXTERNAL_API_RETRY_INITIAL_DELAY: float = 0.5
    EXTERNAL_API_RETRY_MAX_DELAY: float = 3.0
    OSS_RETRY_ATTEMPTS: int = 3
    SMS_RETRY_ATTEMPTS: int = 2
    EMAIL_RETRY_ATTEMPTS: int = 2
    AI_RETRY_ATTEMPTS: int = 2
    
    # API 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # 日志配置
    LOG_ENABLED: bool = True                  # 总开关：是否启用日志系统
    LOG_LEVEL: str = "INFO"                   # 日志级别：DEBUG / INFO / WARNING / ERROR
    LOG_DIR: str = "./logs"                   # 日志文件根目录
    LOG_ROTATION: str = "50 MB"              # 单文件轮转阈值（支持 "50 MB" / "00:00" 每天零点）
    LOG_RETENTION: str = "30 days"           # 日志保留时长，超期自动删除
    LOG_COMPRESSION: str = "gz"              # 归档压缩格式：gz / zip / None
    LOG_DB_ENABLED: bool = True              # 是否将审计日志写入数据库
    LOG_DB_METHODS: str = "POST,PUT,DELETE"  # 哪些 HTTP Method 触发数据库记录
    LOG_DB_QUEUE_SIZE: int = 1000            # 审计日志入库队列上限，避免后台任务无限堆积

    # 初始化脚本配置
    INIT_SAMPLE_STAFF: bool = False          # 仅开发/演示环境开启，生产环境不要创建默认密码示例账号
    LOG_DB_WORKERS: int = 2                  # 每个进程内审计日志入库 worker 数
    LOG_SANITIZE_FIELDS: str = "password,oldPassword,newPassword,old_password,new_password,token,secret,sms_code,captcha,invite_token"
    LOG_MAX_PAYLOAD_SIZE: int = 4096         # payload 字段最大字符数（超出截断）
    LOG_MODULES: str = "Auth,Workspace,Order,AI,Staff,Notification,Contractor,System"
    
    # 初始管理员账户
    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str = "123456"
    INIT_ADMIN_EMAIL: str = "admin@example.com"
    INIT_ADMIN_PHONE: str = "13800000000"  # 管理员登录手机号
    INIT_ADDITIONAL_ADMINS: str = ""       # JSON 数组: [{"username":"admin2","phone":"138...","password":"...","email":"..."}]
    
    # 大模型 API 配置 
    AI_API_KEY: str = ""
    AI_BASE_URL: str = "https://api.openai.com/v1"
    AI_RESPONSES_BASE_URL: str = ""
    AI_MODEL_NAME: str = "gpt-3.5-turbo"
    AI_HTTP_TIMEOUT: float = 120.0
    AI_REQUIREMENT_TEMPERATURE: float = 0.3
    AI_CREATIVE_DIRECTION_TIMEOUT: float = 120.0
    AI_CREATIVE_DIRECTION_RETRY_ATTEMPTS: int = 1
    DOCUMENT_EXTRACT_MODEL: str = "qwen3.7-max"
    DOCUMENT_EXTRACT_TIMEOUT: float = 180.0
    DOCUMENT_EXTRACT_CHUNK_CHARS: int = 18000
    DOCUMENT_EXTRACT_MAX_TOTAL_CHARS: int = 120000
    AI_PREFER_RESPONSES_API: bool = False
    AI_ENABLE_THINKING: bool = False
    AI_MAX_CONCURRENT_REQUESTS: int = 4
    AI_REQUEST_QUEUE_TIMEOUT: float = 5.0
    AI_BACKGROUND_MAX_CONCURRENT: int = 2
    AI_CRAWL_MAX_CONCURRENT: int = 1
    AI_CRAWL_PENDING_TTL_SECONDS: int = 1800
    STARTUP_DB_LOCK_TIMEOUT: int = 60

    # Hermes Agent API Server（管理员创意工作台使用）
    # 需要在 Hermes 侧启用 API_SERVER_ENABLED=true，并启动 `hermes gateway`。
    HERMES_AGENT_ENABLED: bool = False
    HERMES_API_BASE_URL: str = "http://127.0.0.1:8642/v1"
    HERMES_API_KEY: str = ""
    HERMES_HTTP_TIMEOUT: float = 180.0
    HERMES_CREATIVE_PROFILE: str = "creative-orchestrator"
    HERMES_CREATIVE_MODEL: str = ""
    HERMES_CREATIVE_SKILLS_DIR: str = "./hermes_skills"
    HERMES_CREATIVE_REQUIRED_TOOLSETS: str = "skills,code_execution,memory,session_search"
    HERMES_CREATIVE_BACKGROUND_TIMEOUT: float = 1200.0
    HERMES_CREATIVE_POLL_INTERVAL: float = 2.0
    
    # 部署模式：all = 全量（开发用）, external = 用户端, internal = 内部系统
    DEPLOYMENT_MODE: str = "all"
    
    # 承包商端基础 URL（用于生成邀请链接）
    CONTRACTOR_BASE_URL: str = "https://contractor.uniquevisionx.com"

    # 用户端官网基础 URL（用于生成普通用户邀请链接）
    USER_SITE_BASE_URL: str = "https://www.uniquevisionx.com"

    # 内测阶段默认关闭开放注册；设为 true 时普通用户无需邀请 token 也可注册。
    ALLOW_OPEN_USER_REGISTRATION: bool = False
    
    # Agent 模式切换：brand（品牌方需求收集）/ media（媒体方需求收集）
    AGENT_MODE: str = "media"
    
    class Config:
        env_file = ".env"
        case_sensitive = True
        extra = "ignore"  # 忽略 .env 中未声明的字段（如 LOG_* 等）


# 创建全局配置实例
settings = Settings()
