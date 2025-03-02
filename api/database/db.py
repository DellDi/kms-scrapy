"""数据库连接和工具类."""
import os
from contextlib import contextmanager
from typing import Generator

from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import Session, sessionmaker

# 获取当前文件所在目录
BASE_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

# 数据库文件路径
DB_PATH = os.path.join(BASE_DIR, "api.db")

# 创建数据库引擎
engine = create_engine(
    f"sqlite:///{DB_PATH}",
    connect_args={"check_same_thread": False}  # 允许多线程访问
)

# 创建会话工厂
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# 声明基类
Base = declarative_base()

def get_db() -> Generator[Session, None, None]:
    """获取数据库会话.

    This is a FastAPI dependency that yields a database session.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

@contextmanager
def get_db_context() -> Generator[Session, None, None]:
    """获取数据库会话（上下文管理器版本）.

    This is for use with 'with' statements:
        with get_db_context() as db:
            db.query(User).all()
    """
    db = SessionLocal()
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
    # 导入所有模型以确保它们被注册到Base.metadata
    from api.database.models import ApiLog, Task  # 避免循环导入

    # 创建所有表
    Base.metadata.create_all(bind=engine)