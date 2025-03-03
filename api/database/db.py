"""数据库连接和工具类."""
import os
from contextlib import contextmanager
from typing import Generator

from sqlmodel import Session, SQLModel, create_engine

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据库文件路径
DB_PATH = os.path.join(BASE_DIR, "api.db")

# 创建数据库引擎
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False},  # 允许多线程访问
    echo=False  # 设置为True可以查看SQL语句
)

# 创建会话工厂
SessionLocal = Session

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话.

    这个函数被设计为FastAPI的依赖项，用于提供数据库会话。
    使用Generator类型提示告诉FastAPI这是一个yield依赖项。
    """
    db = Session(engine)
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """获取数据库会话上下文管理器.

    这个函数用于需要在with语句中使用数据库会话的场景。
    例如：
        with get_db_context() as db:
            db.query(User).all()
    """
    db = Session(engine)
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()

def init_db() -> None:
    """初始化数据库."""
    # SQLModel会自动导入所有继承自SQLModel的模型
    from api.database.models import ApiLog, Task  # noqa: F401

    # 创建所有表
    SQLModel.metadata.create_all(engine)
