"""响应模型定义."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field

class TaskStatus(BaseModel):
    """任务状态响应模型."""

    task_id: UUID = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态")
    start_time: float = Field(..., description="开始时间")
    end_time: Optional[float] = Field(None, description="结束时间")
    message: str = Field("", description="状态消息")

class TaskResponse(BaseModel):
    """任务创建响应."""

    task_id: UUID
    message: str

class CallbackResponse(BaseModel):
    """回调响应."""

    status: str