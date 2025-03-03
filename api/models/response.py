"""响应模型定义."""

from typing import Optional, Dict, Any, List, Annotated
from uuid import UUID

from typing import List, Type
from pydantic import BaseModel, Field, create_model


class TaskStatus(BaseModel):
    """任务状态响应."""

    task_id: UUID = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态(pending/running/completed/failed)")
    start_time: float = Field(..., description="开始时间(Unix时间戳)")
    end_time: Optional[float] = Field(None, description="结束时间(Unix时间戳)")
    message: Optional[str] = Field(None, description="状态消息")


class TaskResponse(BaseModel):
    """任务创建响应."""

    task_id: UUID = Field(..., description="任务ID")
    message: str = Field(..., description="状态消息")


class TaskList(BaseModel):
    """任务列表响应."""

    tasks: List[TaskStatus] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过数")
    limit: int = Field(..., description="限制数")


class FileDownloadResponse(BaseModel):
    file_name: str = Field(..., description="文件名")
    file_size: int = Field(..., description="文件大小")
    download_url: str = Field(..., description="下载URL")


class BinaryFileSchema(BaseModel):
    """仅用于API文档展示的二进制文件模型"""

    file: Annotated[bytes, Field(description="二进制文件内容")]

    class Config:
        json_schema_extra = {"type": "string", "format": "binary", "description": "二进制文件内容"}
