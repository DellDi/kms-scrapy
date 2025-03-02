"""数据库模型定义."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from sqlalchemy import Column, Integer, String, Float, Text, DateTime, JSON
from sqlalchemy.dialects.sqlite import JSON as SQLiteJSON
from sqlalchemy.types import TypeDecorator

from api.database.db import Base

class UUIDType(TypeDecorator):
    """自定义UUID类型，用于SQLite."""

    impl = String
    cache_ok = True

    def process_bind_param(self, value, dialect):
        if value is None:
            return None
        return str(value)

    def process_result_value(self, value, dialect):
        if value is None:
            return None
        return UUID(value)

class ApiLog(Base):
    """API请求日志模型."""

    __tablename__ = "api_logs"

    id = Column(Integer, primary_key=True, index=True)
    client_ip = Column(String(50), nullable=False, comment="客户端IP")
    request_path = Column(String(255), nullable=False, comment="请求路径")
    request_method = Column(String(10), nullable=False, comment="请求方法")
    request_params = Column(Text, nullable=True, comment="请求参数")
    request_body = Column(Text, nullable=True, comment="请求体")
    response_status = Column(Integer, nullable=False, comment="响应状态码")
    response_body = Column(Text, nullable=True, comment="响应内容")
    user_agent = Column(String(255), nullable=True, comment="User Agent")
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.now,
        comment="创建时间"
    )
    duration_ms = Column(Integer, nullable=True, comment="请求处理时长(毫秒)")
    error_message = Column(Text, nullable=True, comment="错误信息")

class Task(Base):
    """爬虫任务模型."""

    __tablename__ = "tasks"

    id = Column(UUIDType, primary_key=True, index=True, comment="任务ID")
    status = Column(
        String(20),
        nullable=False,
        default="pending",
        comment="任务状态(pending/running/completed/failed)"
    )
    jql = Column(Text, nullable=False, comment="JQL查询条件")
    output_dir = Column(String(255), nullable=False, comment="输出目录")
    start_time = Column(Float, nullable=False, comment="开始时间(Unix时间戳)")
    end_time = Column(Float, nullable=True, comment="结束时间(Unix时间戳)")
    message = Column(Text, nullable=True, comment="状态消息")
    error = Column(Text, nullable=True, comment="错误信息")
    total_issues = Column(Integer, default=0, comment="总问题数")
    successful_exports = Column(Integer, default=0, comment="成功导出数")
    duration_seconds = Column(Float, nullable=True, comment="执行时长(秒)")
    callback_url = Column(String(255), nullable=True, comment="回调URL")
    created_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        comment="创建时间"
    )
    updated_at = Column(
        DateTime,
        nullable=False,
        default=datetime.utcnow,
        onupdate=datetime.utcnow,
        comment="更新时间"
    )
    extra_data = Column(
        SQLiteJSON,
        nullable=True,
        comment="额外数据"
    )

    def to_dict(self) -> dict:
        """转换为字典."""
        return {
            "task_id": self.id,
            "status": self.status,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "message": self.message,
            "total_issues": self.total_issues,
            "successful_exports": self.successful_exports,
            "duration_seconds": self.duration_seconds,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None,
        }