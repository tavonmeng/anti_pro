"""给 users 表添加 phone 列的迁移脚本"""

import sqlite3
import sys
import os

def migrate():
    # 找到数据库文件
    db_path = os.path.join(os.path.dirname(__file__), '..', 'app.db')
    db_path = os.path.abspath(db_path)
    
    if not os.path.exists(db_path):
        print(f"数据库文件不存在: {db_path}")
        print("首次启动时会自动创建包含 phone 列的新表，无需迁移。")
        return
    
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    # 检查 phone 列是否已存在
    cursor.execute("PRAGMA table_info(users)")
    columns = [col[1] for col in cursor.fetchall()]
    
    if 'phone' in columns:
        print("✅ phone 列已存在，无需迁移。")
        conn.close()
        return
    
    # 添加 phone 列
    try:
        cursor.execute("ALTER TABLE users ADD COLUMN phone VARCHAR(20)")
        conn.commit()
        print("✅ 成功添加 phone 列到 users 表")
    except Exception as e:
        print(f"❌ 迁移失败: {e}")
        conn.rollback()
    finally:
        conn.close()

if __name__ == "__main__":
    migrate()
