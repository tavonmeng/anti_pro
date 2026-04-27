"""
AI 知识库路径工具
统一管理知识库目录的路径解析，所有 Agent 模块通过此工具获取文件路径。
"""

import os
from app.config import settings

# 知识库/业务数据的默认位置：backend/app/data/
_DEFAULT_KNOWLEDGE_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "data")


def get_knowledge_dir() -> str:
    """获取知识库根目录路径"""
    if settings.KNOWLEDGE_DIR:
        return settings.KNOWLEDGE_DIR
    return _DEFAULT_KNOWLEDGE_DIR


def get_knowledge_file(filename: str) -> str:
    """获取知识库中某个文件的完整路径

    Args:
        filename: 文件名，如 'business_intro.md' 或 'cases.json'

    Returns:
        文件的绝对路径
    """
    return os.path.join(get_knowledge_dir(), filename)
