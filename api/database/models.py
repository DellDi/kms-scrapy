"""数据库模型定义."""

from datetime import datetime
from typing import Optional, Dict, Any
from uuid import UUID

from sqlmodel import Field, SQLModel
from sqlalchemy import JSON, Column


class ApiLog(SQLModel, table=True):
    """API请求日志模型."""

    __tablename__ = "api_logs"

    id: Optional[int] = Field(default=None, primary_key=True)
    client_ip: str = Field(..., description="客户端IP")
    request_path: str = Field(..., description="请求路径")
    request_method: str = Field(..., description="请求方法")
    request_params: Optional[str] = Field(None, description="请求参数")
    request_body: Optional[str] = Field(None, description="请求体")
    response_status: int = Field(..., description="响应状态码")
    response_body: Optional[str] = Field(None, description="响应内容")
    user_agent: Optional[str] = Field(None, description="User Agent")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    duration_ms: Optional[int] = Field(None, description="请求处理时长(毫秒)")
    error_message: Optional[str] = Field(None, description="错误信息")


class Task(SQLModel, table=True):
    """爬虫任务模型."""

    __tablename__ = "tasks"

    id: UUID = Field(..., primary_key=True, description="任务ID")
    task_mode: str = Field(default="jira", description="任务模式(jira/kms)")
    status: str = Field(default="pending", description="任务状态(pending/running/completed/failed)")
    jql: str = Field(
        description="JQL查询条件",
        default="assignee = currentUser() AND resolution = Unresolved order by updated DESC",
    )
    output_dir: str = Field( description="输出目录", default="output-jira")
    start_time: float = Field(..., description="开始时间(Unix时间戳)")
    end_time: Optional[float] = Field(None, description="结束时间(Unix时间戳)")
    message: Optional[str] = Field(None, description="状态消息")
    error: Optional[str] = Field(None, description="错误信息")
    total_issues: int = Field(default=0, description="总问题数")
    successful_exports: int = Field(default=0, description="成功导出数")
    duration_seconds: Optional[float] = Field(None, description="执行时长(秒)")
    callback_url: Optional[str] = Field(None, description="回调URL")
    created_at: datetime = Field(default_factory=datetime.now, description="创建时间")
    updated_at: datetime = Field(
        default_factory=datetime.now,
        sa_column_kwargs={"onupdate": datetime.now},
        description="更新时间",
    )
    # 使用sa_column指定SQLAlchemy的JSON类型
    extra_data: Optional[Dict[str, Any]] = Field(
        default=None, sa_column=Column(JSON), description="额外数据"
    )

    class Config:
        """模型配置."""

        json_encoders = {datetime: lambda v: v.isoformat() if v else None}