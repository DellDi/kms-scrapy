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


class DifyTaskStatus(BaseModel):
    """Dify 任务状态响应."""

    task_id: UUID = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态(pending/running/completed/failed)")
    input_dir: str = Field(..., description="输入目录")
    dataset_prefix: str = Field(..., description="数据集名称前缀")
    max_docs: int = Field(..., description="每个数据集的最大文档数量")
    created_at: datetime = Field(..., description="创建时间")
    updated_at: datetime = Field(..., description="更新时间")
    message: Optional[str] = Field(None, description="状态消息")
    total_files: Optional[int] = Field(None, description="总文件数")
    successful_uploads: Optional[int] = Field(None, description="成功上传数")
    duration_seconds: Optional[float] = Field(None, description="执行时长(秒)")


class DifyTaskResponse(BaseModel):
    """Dify 任务创建响应."""

    task_id: UUID = Field(..., description="任务ID")
    message: str = Field(..., description="状态消息")


class DifyTaskList(BaseModel):
    """Dify 任务列表响应."""

    tasks: List[DifyTaskStatus] = Field(..., description="任务列表")
    total: int = Field(..., description="总数")
    skip: int = Field(..., description="跳过数")
    limit: int = Field(..., description="限制数")


class JiraITOPSResponse(BaseModel):
    """Jira ITOPS工单创建响应."""

    url: str = Field(..., description="工单URL")
    message: str = Field(..., description="状态消息")
    issue_key: Optional[str] = Field(None, description="工单编号")
