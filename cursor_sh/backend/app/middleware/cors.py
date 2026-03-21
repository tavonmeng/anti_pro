"""CORS 中间件配置"""

from fastapi.middleware.cors import CORSMiddleware
from app.config import settings


def setup_cors(app):
    """配置 CORS 中间件"""
    # 解析允许的源
    origins = []
    if isinstance(settings.CORS_ORIGINS, str):
        origins = [origin.strip() for origin in settings.CORS_ORIGINS.split(",")]
    elif isinstance(settings.CORS_ORIGINS, list):
        origins = settings.CORS_ORIGINS
    
    app.add_middleware(
        CORSMiddleware,
        allow_origins=origins,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

