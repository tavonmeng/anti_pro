"""自定义验证器"""

import os
from fastapi import HTTPException, status
from app.config import settings


def validate_file_size(file_size: int) -> bool:
    """验证文件大小"""
    if file_size > settings.MAX_FILE_SIZE:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"文件大小超过限制（最大 {settings.MAX_FILE_SIZE / 1024 / 1024}MB）"
        )
    return True


def validate_file_type(mime_type: str) -> bool:
    """验证文件类型"""
    allowed_types = settings.ALLOWED_FILE_TYPES.split(",")
    if mime_type not in allowed_types:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"不支持的文件类型。允许的类型: {', '.join(allowed_types)}"
        )
    return True


def generate_order_number() -> str:
    """生成订单编号"""
    from datetime import datetime
    import random
    import string
    
    date = datetime.now().strftime("%Y%m%d")
    random_code = ''.join(random.choices(string.ascii_uppercase + string.digits, k=4))
    
    return f"ORD-{date}-{random_code}"


def generate_id(prefix: str = "") -> str:
    """生成唯一 ID"""
    from datetime import datetime
    import random
    
    timestamp = int(datetime.now().timestamp() * 1000)
    random_suffix = random.randint(1000, 9999)
    
    if prefix:
        return f"{prefix}-{timestamp}{random_suffix}"
    return f"{timestamp}{random_suffix}"

