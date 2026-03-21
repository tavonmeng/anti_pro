"""初始化管理员账户脚本"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import async_session_maker, init_db
from app.models.user import User, UserRole
from app.utils.security import get_password_hash
from app.utils.validators import generate_id
from app.config import settings


async def create_admin():
    """创建管理员账户"""
    async with async_session_maker() as session:
        # 检查管理员是否已存在
        result = await session.execute(
            select(User).where(
                User.username == settings.INIT_ADMIN_USERNAME,
                User.role == UserRole.ADMIN
            )
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            print(f"⚠️  管理员账户已存在: {settings.INIT_ADMIN_USERNAME}")
            return
        
        # 创建管理员
        admin = User(
            id=generate_id("admin"),
            username=settings.INIT_ADMIN_USERNAME,
            password_hash=get_password_hash(settings.INIT_ADMIN_PASSWORD),
            email=settings.INIT_ADMIN_EMAIL,
            role=UserRole.ADMIN,
            real_name="系统管理员",
            is_active=True
        )
        
        session.add(admin)
        await session.commit()
        
        print(f"✅ 管理员账户创建成功")
        print(f"   用户名: {settings.INIT_ADMIN_USERNAME}")
        print(f"   密码: {settings.INIT_ADMIN_PASSWORD}")
        print(f"   邮箱: {settings.INIT_ADMIN_EMAIL}")


async def create_sample_staff():
    """创建示例负责人账户"""
    async with async_session_maker() as session:
        sample_staff = [
            {
                "username": "staff1",
                "real_name": "张设计",
                "email": "staff1@example.com"
            },
            {
                "username": "staff2",
                "real_name": "李艺术",
                "email": "staff2@example.com"
            }
        ]
        
        for staff_data in sample_staff:
            # 检查是否已存在
            result = await session.execute(
                select(User).where(User.username == staff_data["username"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                continue
            
            staff = User(
                id=generate_id("staff"),
                username=staff_data["username"],
                password_hash=get_password_hash("123456"),
                email=staff_data["email"],
                real_name=staff_data["real_name"],
                role=UserRole.STAFF,
                is_active=True
            )
            
            session.add(staff)
        
        await session.commit()
        print(f"✅ 示例负责人账户创建完成（默认密码: 123456）")


async def main():
    """主函数"""
    print("🔧 初始化数据库...")
    
    # 初始化数据库表
    await init_db()
    print("✅ 数据库表创建完成")
    
    # 创建管理员账户
    await create_admin()
    
    # 创建示例负责人
    await create_sample_staff()
    
    print("\n🎉 数据库初始化完成！")


if __name__ == "__main__":
    asyncio.run(main())

