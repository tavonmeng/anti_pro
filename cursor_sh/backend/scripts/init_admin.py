"""初始化管理员账户脚本

可手动运行: python scripts/init_admin.py
也会在应用启动时自动调用 ensure_admin()
"""

import asyncio
import sys
from pathlib import Path

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.database import async_session_maker, init_db
from app.models.admin import Admin
from app.models.staff_member import StaffMember
from app.utils.security import get_password_hash
from app.utils.validators import generate_id
from app.config import settings


async def ensure_admin():
    """
    确保管理员账户存在且信息完整（幂等操作）。
    
    操作的是 admins 表（独立于 users/staff_members）。
    """
    async with async_session_maker() as session:
        # 在 admins 表中查找
        result = await session.execute(
            select(Admin).where(Admin.username == settings.INIT_ADMIN_USERNAME)
        )
        existing_admin = result.scalar_one_or_none()
        
        if existing_admin:
            # 管理员已存在，检查是否需要补全信息
            updated_fields = []
            
            if not existing_admin.phone and settings.INIT_ADMIN_PHONE:
                existing_admin.phone = settings.INIT_ADMIN_PHONE
                updated_fields.append(f"phone={settings.INIT_ADMIN_PHONE}")
            
            if not existing_admin.email and settings.INIT_ADMIN_EMAIL:
                existing_admin.email = settings.INIT_ADMIN_EMAIL
                updated_fields.append(f"email={settings.INIT_ADMIN_EMAIL}")
            
            if updated_fields:
                await session.commit()
                print(f"  🔧 管理员账户已更新: {', '.join(updated_fields)}")
            else:
                print(f"  ✅ 管理员账户已就绪: {settings.INIT_ADMIN_USERNAME} (手机号: {existing_admin.phone})")
            return
        
        # 创建管理员（到 admins 表）
        admin = Admin(
            id=generate_id("admin"),
            username=settings.INIT_ADMIN_USERNAME,
            password_hash=get_password_hash(settings.INIT_ADMIN_PASSWORD),
            email=settings.INIT_ADMIN_EMAIL,
            phone=settings.INIT_ADMIN_PHONE,
            real_name="系统管理员",
            is_active=True
        )
        
        session.add(admin)
        await session.commit()
        
        print(f"  ✅ 管理员账户创建成功（admins 表）")
        print(f"     用户名: {settings.INIT_ADMIN_USERNAME}")
        print(f"     手机号: {settings.INIT_ADMIN_PHONE}")
        print(f"     密码:   {settings.INIT_ADMIN_PASSWORD}")
        print(f"     邮箱:   {settings.INIT_ADMIN_EMAIL}")


async def create_sample_staff():
    """创建示例负责人账户（到 staff_members 表）"""
    async with async_session_maker() as session:
        sample_staff = [
            {
                "username": "staff1",
                "real_name": "张设计",
                "email": "staff1@example.com",
                "phone": "13800000001"
            },
            {
                "username": "staff2",
                "real_name": "李艺术",
                "email": "staff2@example.com",
                "phone": "13800000002"
            }
        ]
        
        created_count = 0
        for staff_data in sample_staff:
            # 检查是否已存在（在 staff_members 表中）
            result = await session.execute(
                select(StaffMember).where(StaffMember.username == staff_data["username"])
            )
            existing = result.scalar_one_or_none()
            
            if existing:
                continue
            
            staff = StaffMember(
                id=generate_id("staff"),
                username=staff_data["username"],
                password_hash=get_password_hash("123456"),
                email=staff_data["email"],
                phone=staff_data.get("phone"),
                real_name=staff_data["real_name"],
                is_active=True
            )
            
            session.add(staff)
            created_count += 1
        
        await session.commit()
        if created_count > 0:
            print(f"  ✅ 创建了 {created_count} 个示例负责人账户（staff_members 表，默认密码: 123456）")
        else:
            print(f"  ✅ 示例负责人账户已就绪")


async def main():
    """主函数（手动运行时使用）"""
    print("🔧 初始化数据库...")
    
    # 初始化数据库表
    await init_db()
    print("✅ 数据库表创建完成")
    
    # 创建管理员账户（admins 表）
    await ensure_admin()
    
    # 创建示例负责人（staff_members 表）
    await create_sample_staff()
    
    print("\n🎉 数据库初始化完成！")
    print(f"\n📋 数据库表结构:")
    print(f"   admins       → 管理员")
    print(f"   staff_members → 设计师/负责人")
    print(f"   users         → 普通客户")
    print(f"\n📋 管理员登录信息:")
    print(f"   手机号: {settings.INIT_ADMIN_PHONE}")
    print(f"   密码:   {settings.INIT_ADMIN_PASSWORD}")
    print(f"   登录地址: /admin/login")


if __name__ == "__main__":
    asyncio.run(main())
