"""初始化数据库脚本."""
import os
from datetime import datetime, timedelta
from uuid import uuid4

from api.database.db import engine, Session
from api.database.models import Task, SQLModel

def init_database(add_test_data: bool = True):
    """初始化数据库."""
    # 如果数据库文件已存在，先删除
    db_path = str(engine.url).replace("sqlite:///", "")
    if os.path.exists(db_path):
        print(f"删除已存在的数据库文件: {db_path}")
        os.remove(db_path)

    print(f"创建新的数据库文件: {db_path}")

    # 初始化数据库表
    SQLModel.metadata.create_all(engine)
    print("数据库表创建成功！")

    # 显示创建的表结构
    print("\n已创建的表:")
    for table in SQLModel.metadata.tables.values():
        print(f"\n表 {table.name} 的结构:")
        for column in table.columns:
            print(f"- {column.name}: {column.type}")

    # 添加测试数据
    if add_test_data:
        print("\n添加测试数据...")
        with Session(engine) as db:
            try:
                # 创建一些测试任务
                test_tasks = [
                    Task(
                        id=uuid4(),
                        status="completed",
                        jql="project = DEMO",
                        output_dir="/tmp/test1",
                        start_time=(datetime.now() - timedelta(hours=2)).timestamp(),
                        end_time=(datetime.now() - timedelta(hours=1)).timestamp(),
                        message="Task completed successfully",
                        total_issues=100,
                        successful_exports=98,
                        duration_seconds=3600
                    ),
                    Task(
                        id=uuid4(),
                        status="running",
                        jql="project = TEST",
                        output_dir="/tmp/test2",
                        start_time=datetime.now().timestamp(),
                        message="Crawler is running",
                    ),
                    Task(
                        id=uuid4(),
                        status="failed",
                        jql="project = ERROR",
                        output_dir="/tmp/test3",
                        start_time=(datetime.now() - timedelta(minutes=30)).timestamp(),
                        end_time=(datetime.now() - timedelta(minutes=25)).timestamp(),
                        message="Task failed",
                        error="Connection error",
                        duration_seconds=300
                    )
                ]

                for task in test_tasks:
                    db.add(task)
                db.commit()

                print(f"添加了 {len(test_tasks)} 个测试任务")

            except Exception as e:
                print(f"添加测试数据时出错: {e}")
                db.rollback()

if __name__ == "__main__":
    print("开始初始化数据库...")
    init_database()
    print("\n数据库初始化完成！")
    print("\n你现在可以：")
    print("启动API服务: uv run -m api.api_service")