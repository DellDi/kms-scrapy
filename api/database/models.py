"""数据库模型定义."""
from datetime import datetime

from sqlalchemy import Column, Integer, String, DateTime, Text

from api.database.db import Base

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
        default=datetime.now(),
        comment="创建时间"
    )
    duration_ms = Column(Integer, nullable=True, comment="请求处理时长(毫秒)")
    error_message = Column(Text, nullable=True, comment="错误信息")

    def __repr__(self) -> str:
        """返回日志记录的字符串表示."""
        return (
            f"<ApiLog("
            f"id={self.id}, "
            f"path={self.request_path}, "
            f"method={self.request_method}, "
            f"status={self.response_status}"
            f")>"
        )