"""初始化数据库脚本."""
import os
import sqlite3
from datetime import datetime, timedelta
from uuid import uuid4
from pathlib import Path

from api.database.db import init_db, DB_PATH, SessionLocal
from api.database.models import Task

def init_database(add_test_data: bool = True):
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

    # 添加测试数据
    if add_test_data:
        print("\n添加测试数据...")
        db = SessionLocal()
        try:
            # 创建一些测试任务
            test_tasks = [
                {
                    "id": uuid4(),
                    "status": "completed",
                    "jql": "project = DEMO",
                    "output_dir": "/tmp/test1",
                    "start_time": (datetime.now() - timedelta(hours=2)).timestamp(),
                    "end_time": (datetime.now() - timedelta(hours=1)).timestamp(),
                    "message": "Task completed successfully",
                    "total_issues": 100,
                    "successful_exports": 98,
                    "duration_seconds": 3600
                },
                {
                    "id": uuid4(),
                    "status": "running",
                    "jql": "project = TEST",
                    "output_dir": "/tmp/test2",
                    "start_time": datetime.now().timestamp(),
                    "message": "Crawler is running",
                },
                {
                    "id": uuid4(),
                    "status": "failed",
                    "jql": "project = ERROR",
                    "output_dir": "/tmp/test3",
                    "start_time": (datetime.now() - timedelta(minutes=30)).timestamp(),
                    "end_time": (datetime.now() - timedelta(minutes=25)).timestamp(),
                    "message": "Task failed",
                    "error": "Connection error",
                    "duration_seconds": 300
                }
            ]

            for task_data in test_tasks:
                task = Task(**task_data)
                db.add(task)

            db.commit()
            print(f"添加了 {len(test_tasks)} 个测试任务")

        except Exception as e:
            print(f"添加测试数据时出错: {e}")
            db.rollback()
        finally:
            db.close()

if __name__ == "__main__":
    print("开始初始化数据库...")
    init_database()
    print("\n数据库初始化完成！")
    print("\n你现在可以：")
    print("1. 启动API服务: uv run -m api.api_service")
    print("2. 访问API文档: http://localhost:8000/api/redoc")
    print("3. 查看任务列表: http://localhost:8000/api/tasks")
    print("4. 查看日志记录: http://localhost:8000/api/logs")