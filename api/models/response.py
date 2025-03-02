"""响应模型定义."""
from datetime import datetime
from typing import Optional
from uuid import UUID

from pydantic import BaseModel, Field


class TaskStatus(BaseModel):
    """任务状态模型."""

    task_id: UUID = Field(..., description="任务ID")
    status: str = Field(..., description="任务状态: pending, running, completed, failed")
    start_time: float = Field(..., description="任务开始时间(Unix时间戳)")
    end_time: Optional[float] = Field(None, description="任务结束时间(Unix时间戳)")
    message: Optional[str] = Field(None, description="任务状态描述")

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "status": "running",
                "start_time": 1614402123.45,
                "end_time": None,
                "message": "Crawler is running"
            }
        }


class TaskResponse(BaseModel):
    """任务创建响应."""

    task_id: UUID = Field(..., description="任务ID")
    message: str = Field(..., description="响应消息")

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {
                "task_id": "550e8400-e29b-41d4-a716-446655440000",
                "message": "Task created successfully"
            }
        }


class CallbackResponse(BaseModel):
    """回调响应."""

    status: str = Field(..., description="回调状态")

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {
                "status": "received"
            }
        }