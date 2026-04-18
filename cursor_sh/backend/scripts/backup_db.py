"""数据库备份脚本"""

import os
import shutil
from datetime import datetime
from pathlib import Path
import sys

# 添加项目根目录到 Python 路径
sys.path.insert(0, str(Path(__file__).parent.parent))

from app.config import settings


def backup_database():
    """备份数据库"""
    # 从数据库 URL 中提取数据库文件路径
    db_url = settings.DATABASE_URL
    
    # 仅支持 SQLite
    if not db_url.startswith("sqlite"):
        print("⚠️  此脚本仅支持 SQLite 数据库备份")
        return
    
    # 提取数据库文件路径
    db_path = db_url.replace("sqlite+aiosqlite:///", "").replace("sqlite:///", "")
    if db_path.startswith("./"):
        db_path = db_path[2:]
    
    # 转换为绝对路径
    project_root = Path(__file__).parent.parent
    db_file = project_root / db_path
    
    if not db_file.exists():
        print(f"❌ 数据库文件不存在: {db_file}")
        return
    
    # 创建备份目录
    backup_dir = project_root / "backups"
    backup_dir.mkdir(exist_ok=True)
    
    # 生成备份文件名
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"backup_{timestamp}.db"
    
    # 复制数据库文件
    try:
        shutil.copy2(db_file, backup_file)
        file_size = backup_file.stat().st_size / 1024  # KB
        
        print(f"✅ 数据库备份成功")
        print(f"   源文件: {db_file}")
        print(f"   备份文件: {backup_file}")
        print(f"   文件大小: {file_size:.2f} KB")
        
        # 清理旧备份（保留最近 10 个）
        cleanup_old_backups(backup_dir, keep=10)
        
    except Exception as e:
        print(f"❌ 备份失败: {e}")


def cleanup_old_backups(backup_dir: Path, keep: int = 10):
    """清理旧备份文件"""
    backup_files = sorted(
        backup_dir.glob("backup_*.db"),
        key=lambda x: x.stat().st_mtime,
        reverse=True
    )
    
    if len(backup_files) > keep:
        for old_backup in backup_files[keep:]:
            try:
                old_backup.unlink()
                print(f"🗑️  删除旧备份: {old_backup.name}")
            except Exception as e:
                print(f"⚠️  删除失败: {old_backup.name} - {e}")


if __name__ == "__main__":
    print("🔄 开始数据库备份...")
    backup_database()
    print("\n✅ 备份完成！")

