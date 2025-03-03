"""响应模型定义."""

import imp
from typing import Optional, Dict, Any, List, Annotated
from uuid import UUID

from datetime import datetime
from typing import List, Type
from pydantic import BaseModel, Field, create_model


class TaskStatus(BaseModel):
    """任务状态响应."""

    task_id: UUID = Field(..., description="任务ID")
    task_mode: str = Field(description="任务模式", default="jira")
    status: str = Field(..., description="任务状态(pending/running/completed/failed)")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
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


class BinaryFileSchema(BaseModel):
    """仅用于API文档展示的二进制文件模型"""

    file: Annotated[bytes, Field(description="二进制文件内容")]

    class Config:
        json_schema_extra = {"type": "string", "format": "binary", "description": "二进制文件内容"}
