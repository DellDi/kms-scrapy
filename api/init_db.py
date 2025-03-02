"""初始化数据库脚本."""
import os
import sqlite3
from pathlib import Path

from api.database.db import init_db, DB_PATH

def init_database():
    """初始化数据库."""
    # 如果数据库文件已存在，先删除
    if os.path.exists(DB_PATH):
        print(f"删除已存在的数据库文件: {DB_PATH}")
        os.remove(DB_PATH)

    print(f"创建新的数据库文件: {DB_PATH}")

    # 初始化数据库表
    init_db()
    print("数据库表创建成功！")

    # 验证表是否创建成功
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()

    # 获取所有表
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()

    print("\n已创建的表:")
    for table in tables:
        table_name = table[0]
        print(f"\n表 {table_name} 的结构:")
        cursor.execute(f"PRAGMA table_info({table_name});")
        columns = cursor.fetchall()
        for col in columns:
            print(f"- {col[1]}: {col[2]}")

    cursor.close()
    conn.close()

if __name__ == "__main__":
    print("开始初始化数据库...")
    init_database()
    print("\n数据库初始化完成！")