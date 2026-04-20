"""
数据迁移脚本：将 users 表中的 admin/staff 记录迁移到独立表

运行方式: python scripts/migrate_split_tables.py

该脚本执行以下操作：
1. 创建 admins 和 staff_members 新表（如果不存在）
2. 将 users 表中 role=ADMIN 的记录复制到 admins 表
3. 将 users 表中 role=STAFF 的记录复制到 staff_members 表
4. 更新 order_assignees 中的引用（assignee_id 不变，数据已在新表）
5. 从 users 表中删除已迁移的 admin/staff 记录
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text, delete

from app.database import async_session_maker, init_db
from app.models.user import User, UserRole
from app.models.admin import Admin
from app.models.staff_member import StaffMember


async def migrate():
    """执行迁移"""
    print("🔧 开始分表迁移...")
    
    # 1. 确保新表已创建
    await init_db()
    print("  ✅ 数据库表结构已更新（admins, staff_members 表已创建）")
    
    async with async_session_maker() as session:
        # 2. 迁移 admin 用户
        admin_result = await session.execute(
            select(User).where(User.role == UserRole.ADMIN)
        )
        admins = admin_result.scalars().all()
        
        migrated_admin_count = 0
        for user in admins:
            # 检查是否已在 admins 表中
            existing = await session.execute(
                select(Admin).where(Admin.id == user.id)
            )
            if existing.scalar_one_or_none():
                print(f"  ⏭️  管理员 '{user.username}' 已在 admins 表中，跳过")
                continue
            
            # 也检查 username 是否冲突
            existing_by_name = await session.execute(
                select(Admin).where(Admin.username == user.username)
            )
            if existing_by_name.scalar_one_or_none():
                print(f"  ⏭️  管理员用户名 '{user.username}' 已存在于 admins 表，跳过")
                continue
            
            admin = Admin(
                id=user.id,
                username=user.username,
                password_hash=user.password_hash,
                email=user.email,
                phone=user.phone,
                real_name=user.real_name,
                avatar=user.avatar,
                is_active=user.is_active
            )
            session.add(admin)
            migrated_admin_count += 1
            print(f"  ✅ 迁移管理员: {user.username} (id: {user.id})")
        
        # 3. 迁移 staff 用户
        staff_result = await session.execute(
            select(User).where(User.role == UserRole.STAFF)
        )
        staff_users = staff_result.scalars().all()
        
        migrated_staff_count = 0
        for user in staff_users:
            # 检查是否已在 staff_members 表中
            existing = await session.execute(
                select(StaffMember).where(StaffMember.id == user.id)
            )
            if existing.scalar_one_or_none():
                print(f"  ⏭️  设计师 '{user.username}' 已在 staff_members 表中，跳过")
                continue
            
            existing_by_name = await session.execute(
                select(StaffMember).where(StaffMember.username == user.username)
            )
            if existing_by_name.scalar_one_or_none():
                print(f"  ⏭️  设计师用户名 '{user.username}' 已存在于 staff_members 表，跳过")
                continue
            
            staff = StaffMember(
                id=user.id,
                username=user.username,
                password_hash=user.password_hash,
                email=user.email,
                phone=user.phone,
                real_name=user.real_name,
                company=getattr(user, 'company', None),
                avatar=user.avatar,
                is_active=user.is_active
            )
            session.add(staff)
            migrated_staff_count += 1
            print(f"  ✅ 迁移设计师: {user.username} (id: {user.id})")
        
        await session.commit()
        
        # 4. 从 users 表中删除已迁移的 admin/staff 记录
        if migrated_admin_count > 0 or migrated_staff_count > 0:
            # 先删除 admin
            admin_ids = [u.id for u in admins]
            if admin_ids:
                await session.execute(
                    delete(User).where(User.id.in_(admin_ids))
                )
            
            # 再删除 staff
            staff_ids = [u.id for u in staff_users]
            if staff_ids:
                await session.execute(
                    delete(User).where(User.id.in_(staff_ids))
                )
            
            await session.commit()
            print(f"\n  🗑️  已从 users 表中移除 {len(admin_ids)} 个 admin 和 {len(staff_ids)} 个 staff 记录")
        
        # 5. 验证结果
        admin_count = (await session.execute(select(Admin))).scalars()
        staff_count = (await session.execute(select(StaffMember))).scalars()
        user_count = (await session.execute(select(User))).scalars()
        
        print(f"\n📊 迁移结果:")
        print(f"   admins 表:        {len(list(admin_count))} 条记录")
        print(f"   staff_members 表: {len(list(staff_count))} 条记录")
        print(f"   users 表:         {len(list(user_count))} 条记录（仅客户）")
    
    print("\n🎉 分表迁移完成！")


if __name__ == "__main__":
    asyncio.run(migrate())
