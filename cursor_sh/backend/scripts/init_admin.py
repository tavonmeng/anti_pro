"""初始化管理员账户脚本

可手动运行: python scripts/init_admin.py
也会在应用启动时自动调用 ensure_admin()
"""

import asyncio
import json
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


def _additional_admin_accounts() -> list[dict]:
    raw = (settings.INIT_ADDITIONAL_ADMINS or "").strip()
    if not raw:
        return []

    try:
        parsed = json.loads(raw)
    except json.JSONDecodeError as exc:
        print(f"  ⚠️  INIT_ADDITIONAL_ADMINS 格式错误，已跳过: {exc}")
        return []

    if not isinstance(parsed, list):
        print("  ⚠️  INIT_ADDITIONAL_ADMINS 必须是 JSON 数组，已跳过")
        return []

    accounts = []
    for index, item in enumerate(parsed, start=1):
        if not isinstance(item, dict):
            print(f"  ⚠️  额外管理员 #{index} 不是对象，已跳过")
            continue

        phone = str(item.get("phone") or "").strip()
        password = str(item.get("password") or "").strip()
        if len(phone) != 11 or not phone.isdigit() or not password:
            print(f"  ⚠️  额外管理员 #{index} 缺少有效手机号或初始密码，已跳过")
            continue

        username = str(item.get("username") or f"admin_{phone}").strip()
        accounts.append({
            "username": username,
            "password": password,
            "email": str(item.get("email") or f"{username}@example.com").strip(),
            "phone": phone,
            "real_name": str(item.get("real_name") or "系统管理员").strip(),
        })

    return accounts


async def _ensure_single_admin(session: AsyncSession, account: dict, *, is_primary: bool = False) -> None:
    result = await session.execute(
        select(Admin).where(
            (Admin.username == account["username"]) | (Admin.phone == account["phone"])
        )
    )
    existing_admin = result.scalar_one_or_none()

    if existing_admin:
        updated_fields = []

        if not existing_admin.phone and account["phone"]:
            existing_admin.phone = account["phone"]
            updated_fields.append(f"phone={account['phone']}")

        if not existing_admin.email and account["email"]:
            existing_admin.email = account["email"]
            updated_fields.append(f"email={account['email']}")

        if not existing_admin.real_name and account["real_name"]:
            existing_admin.real_name = account["real_name"]
            updated_fields.append(f"real_name={account['real_name']}")

        if updated_fields:
            await session.commit()
            print(f"  🔧 管理员账户已更新: {existing_admin.username} ({', '.join(updated_fields)})")
        else:
            label = "主管理员" if is_primary else "额外管理员"
            print(f"  ✅ {label}账户已就绪: {existing_admin.username} (手机号: {existing_admin.phone})")
        return

    admin = Admin(
        id=generate_id("admin"),
        username=account["username"],
        password_hash=get_password_hash(account["password"]),
        email=account["email"],
        phone=account["phone"],
        real_name=account["real_name"],
        is_active=True
    )

    session.add(admin)
    await session.commit()

    label = "主管理员" if is_primary else "额外管理员"
    print(f"  ✅ {label}账户创建成功（admins 表）")
    print(f"     用户名: {account['username']}")
    print(f"     手机号: {account['phone']}")
    print("     密码:   [已隐藏]")
    print(f"     邮箱:   {account['email']}")


async def ensure_admin():
    """
    确保管理员账户存在且信息完整（幂等操作）。
    
    操作的是 admins 表（独立于 users/staff_members）。
    """
    async with async_session_maker() as session:
        await _ensure_single_admin(session, {
            "username": settings.INIT_ADMIN_USERNAME,
            "password": settings.INIT_ADMIN_PASSWORD,
            "email": settings.INIT_ADMIN_EMAIL,
            "phone": settings.INIT_ADMIN_PHONE,
            "real_name": "系统管理员",
        }, is_primary=True)

        for account in _additional_admin_accounts():
            await _ensure_single_admin(session, account)


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
            print(f"  ✅ 创建了 {created_count} 个示例负责人账户（staff_members 表，默认密码已隐藏）")
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
    
    # 创建示例负责人（staff_members 表）。生产环境默认关闭，避免默认密码账号上线。
    if settings.INIT_SAMPLE_STAFF or not settings.is_production:
        await create_sample_staff()
    else:
        print("✅ 生产环境已跳过示例负责人账户创建")
    
    print("\n🎉 数据库初始化完成！")
    print(f"\n📋 数据库表结构:")
    print(f"   admins       → 管理员")
    print(f"   staff_members → 设计师/负责人")
    print(f"   users         → 普通客户")
    print(f"\n📋 管理员登录信息:")
    print(f"   手机号: {settings.INIT_ADMIN_PHONE}")
    print("   密码:   [已隐藏]")
    print(f"   登录地址: /admin/login")


if __name__ == "__main__":
    asyncio.run(main())
