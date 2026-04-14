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


class Settings(BaseSettings):
    """应用配置类"""
    
    # 应用配置
    APP_NAME: str = "AI设计任务管理系统"
    APP_VERSION: str = "1.0.0"
    DEBUG: bool = True
    SECRET_KEY: str = "dev-secret-key-change-in-production"
    
    # 服务器配置
    HOST: str = "0.0.0.0"
    PORT: int = 8000
    
    # 数据库配置
    DATABASE_URL: str = "sqlite+aiosqlite:///./app.db"
    
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
    MAX_FILE_SIZE: int = 52428800  # 50MB
    ALLOWED_FILE_TYPES: str = "image/jpeg,image/png,image/gif,video/mp4,application/zip,application/pdf"
    
    # 阿里云 OSS 配置
    OSS_ENABLED: bool = False
    OSS_ACCESS_KEY_ID: str = ""
    OSS_ACCESS_KEY_SECRET: str = ""
    OSS_BUCKET_NAME: str = ""
    OSS_ENDPOINT: str = ""
    
    # 阿里云号码认证服务（Dypnsapi - 短信验证码）配置
    SMS_ENABLED: bool = True
    SMS_ACCESS_KEY_ID: str = ""      # 可与 OSS 共用
    SMS_ACCESS_KEY_SECRET: str = ""
    SMS_SIGN_NAME: str = ""          # 短信签名 (如: "速通互联验证码")
    SMS_TEMPLATE_CODE: str = ""      # 模板CODE (如: "100001")
    SMS_CODE_LENGTH: int = 6         # 验证码长度
    SMS_VALID_TIME: int = 300        # 验证码有效期（秒）
    
    # 邮件配置
    SMTP_HOST: str = "smtp.qq.com"
    SMTP_PORT: int = 465
    SMTP_USER: str = ""
    SMTP_PASSWORD: str = ""
    SMTP_FROM: str = ""
    SMTP_FROM_NAME: str = "AI设计任务管理系统"
    
    # API 限流配置
    RATE_LIMIT_ENABLED: bool = True
    RATE_LIMIT_PER_MINUTE: int = 60
    
    # 初始管理员账户
    INIT_ADMIN_USERNAME: str = "admin"
    INIT_ADMIN_PASSWORD: str = "123456"
    INIT_ADMIN_EMAIL: str = "admin@example.com"
    
    class Config:
        env_file = ".env"
        case_sensitive = True


# 创建全局配置实例
settings = Settings()

