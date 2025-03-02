"""Jira爬虫API服务."""
import os
import shutil
import asyncio
import tempfile
from datetime import datetime
from typing import Dict, List, Optional
from uuid import UUID, uuid4

import logging

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from api.models.request import CrawlRequest
from api.models.response import TaskStatus, TaskResponse, CallbackResponse

from api.database.db import get_db, init_db, get_db_context
from api.database.models import ApiLog, Task
from api.middleware import APILoggingMiddleware

logger = logging.getLogger(__name__)

# 创建FastAPI实例
app = FastAPI(
    title="Jira爬虫API服务",
    description="""
    # Jira爬虫API服务文档

    该服务提供了一组API接口，用于管理和控制Jira爬虫任务。

    ## 主要功能

    1. **爬虫任务管理**
       - 启动新的爬虫任务
       - 查询任务执行状态
       - 下载爬虫结果

    2. **系统监控**
       - API请求日志查询
       - 任务执行状态跟踪

    ## 使用流程

    1. 调用 `/api/jira/crawl` 接口启动爬虫任务
    2. 使用返回的task_id通过 `/api/jira/task/{task_id}` 查询任务状态
    3. 当任务完成后，使用 `/api/jira/download/{task_id}` 下载结果

    ## 日志系统

    系统使用SQLite数据库记录所有API请求的详细信息，包括：
    - 客户端IP
    - 请求路径和方法
    - 响应状态码
    - 处理时长等
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    openapi_tags=[
        {"name": "爬虫任务", "description": "爬虫任务的启动、状态查询和结果下载"},
        {"name": "系统监控", "description": "系统日志查询和状态监控"},
    ],
)

# 添加CORS中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 添加日志中间件
app.add_middleware(APILoggingMiddleware)

# 临时文件目录
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# 初始化数据库
init_db()

def update_task_status(
    task: Task,
    status: str,
    message: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = Depends(get_db),
    **kwargs,
) -> Task:
    """更新任务状态."""
    task.status = status
    task.message = message
    task.error = error

    if status in ["completed", "failed"]:
        task.end_time = datetime.now().timestamp()
        if task.start_time:
            task.duration_seconds = task.end_time - task.start_time

    # 更新其他属性
    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)

    db.commit()
    db.refresh(task)
    return task


def get_task_by_id(task_id: UUID, db: Session) -> Optional[Task]:
    """根据ID获取任务."""
    return db.query(Task).filter(Task.id == task_id).first()


def create_task(
    task_id: UUID, jql: str, output_dir: str, callback_url: Optional[str], db: Session
) -> Task:
    """创建新任务."""
    task = Task(
        id=task_id,
        status="pending",
        jql=jql,
        output_dir=output_dir,
        start_time=datetime.now().timestamp(),
        callback_url=callback_url,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


@app.post(
    "/api/jira/crawl",
    response_model=TaskResponse,
    tags=["爬虫任务"],
)
async def start_crawl(request: CrawlRequest, db: Session = Depends(get_db)) -> TaskResponse:
    """启动爬虫任务."""
    task_id = uuid4()
    task_dir = os.path.join(TEMP_DIR, str(task_id))
    os.makedirs(task_dir, exist_ok=True)
    logger.info(f"Created task directory: {task_dir}")

    # 创建任务记录
    task = create_task(
        task_id=task_id, jql=request.jql, output_dir=task_dir, callback_url=None, db=db
    )

    # 异步启动爬虫任务
    asyncio.create_task(run_crawler(task_id, db))

    return TaskResponse(task_id=task_id, message="Task created successfully")


async def run_crawler(task_id: UUID, db: Session) -> None:
    """异步运行爬虫任务."""
    task = get_task_by_id(task_id, db)
    if not task:
        logger.error(f"Task not found: {task_id}")
        return

    try:
        # 更新任务状态为运行中
        update_task_status(task=task, status="running", message="Crawler is running", db=db)

        # 构建命令
        cmd = [
            "uv",
            "run",
            "jira/main.py",
            "--jql",
            task.jql,
            "--output_dir",
            task.output_dir,
            "--callback_url",
            f"http://localhost:8000/api/jira/callback/{task_id}",
        ]

        # 异步执行爬虫命令
        process = await asyncio.create_subprocess_exec(
            *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
        )

        # 等待进程完成
        stdout, stderr = await process.communicate()

        if process.returncode != 0:
            # 爬虫执行失败
            update_task_status(
                task=task,
                status="failed",
                message=f"Crawler failed: {stderr.decode()}",
                error=stderr.decode(),
                db=db,
            )
        else:
            # 爬虫执行成功
            update_task_status(
                task=task, status="completed", message="Crawler completed successfully", db=db
            )

    except Exception as e:
        # 捕获其他异常
        error_msg = str(e)
        logger.error(f"Crawler execution failed: {error_msg}")
        update_task_status(
            task=task, status="failed", message=f"Error: {error_msg}", error=error_msg, db=db
        )


@app.get(
    "/api/jira/task/{task_id}",
    response_model=TaskStatus,
    tags=["爬虫任务"],
    summary="查询任务状态",
    description="""
    根据任务ID查询爬虫任务的执行状态。

    - **task_id**: 任务ID（UUID格式）

    返回任务的详细状态信息，包括：
    - 任务状态（pending/running/completed/failed）
    - 开始时间
    - 结束时间（如果已完成）
    - 状态消息
    """,
)
async def get_task_status(task_id: UUID, db: Session = Depends(get_db)) -> TaskStatus:
    task = get_task_by_id(task_id, db)

    """获取任务状态."""
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")
    return task.status


@app.get(
    "/api/jira/download/{task_id}",
    tags=["爬虫任务"],
    summary="下载任务结果",
    description="""
    下载已完成的爬虫任务结果（ZIP格式）。

    - **task_id**: 任务ID（UUID格式）

    注意：
    - 只有在任务状态为 completed 时才能下载
    - 下载的文件为ZIP格式，包含所有爬取的数据
    """,
)
async def download_result(task_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    task = get_task_by_id(task_id, db)

    logger.debug(f"Downloading result for task {task}")

    """下载任务结果."""
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    if task.status != "completed":
        raise HTTPException(status_code=400, detail=f"Task is not completed{task}")

    task_dir = os.path.join(TEMP_DIR, str(task_id))
    if not os.path.exists(task_dir):
        raise HTTPException(status_code=404, detail="Task result not found")

    # 创建临时zip文件
    zip_path = os.path.join(tempfile.gettempdir(), f"{task_id}.zip")
    shutil.make_archive(zip_path[:-4], "zip", task_dir)  # 移除.zip后缀

    return FileResponse(
        zip_path, media_type="application/zip", filename=f"jira_result_{task_id}.zip"
    )


@app.post(
    "/api/jira/callback/{task_id}",
    response_model=CallbackResponse,
    tags=["爬虫任务"],
    summary="爬虫任务回调",
    description="供爬虫程序调用的回调接口，用于更新任务执行状态。",
    include_in_schema=False,  # 在文档中隐藏此接口
)
async def task_callback(task_id: UUID) -> CallbackResponse:
    task = get_task_by_id(task_id)

    """爬虫任务回调."""
    if task is None:
        raise HTTPException(status_code=404, detail="Task not found")

    update_task_status(task_id, "completed")

    return CallbackResponse(status="received")


@app.get(
    "/api/logs",
    response_model=List[dict],
    tags=["系统监控"],
    summary="查询API日志",
    description="""
    查询系统API请求日志。支持分页和过滤功能。

    参数：
    - **skip**: 跳过记录数（默认0）
    - **limit**: 返回记录数（默认10）
    - **path**: 按请求路径筛选
    - **status**: 按HTTP状态码筛选

    返回日志记录列表，每条记录包含：
    - 请求路径和方法
    - 客户端IP
    - 响应状态码
    - 处理时长等
    """,
)
async def get_logs(
    skip: int = Query(0, description="跳过记录数"),
    limit: int = Query(10, description="返回记录数"),
    path: str = Query(None, description="按路径筛选"),
    status: int = Query(None, description="按状态码筛选"),
    db: Session = Depends(get_db),
) -> List[dict]:
    """获取API请求日志."""
    query = db.query(ApiLog)

    # 应用过滤条件
    if path:
        query = query.filter(ApiLog.request_path.contains(path))
    if status:
        query = query.filter(ApiLog.response_status == status)

    # 排序、分页
    logs = query.order_by(ApiLog.created_at.desc()).offset(skip).limit(limit).all()

    # 转换为字典列表
    return [
        {
            "id": log.id,
            "client_ip": log.client_ip,
            "request_path": log.request_path,
            "request_method": log.request_method,
            "request_params": log.request_params,
            "response_status": log.response_status,
            "created_at": log.created_at.isoformat(),
            "duration_ms": log.duration_ms,
            "error_message": log.error_message,
        }
        for log in logs
    ]


def cleanup_old_tasks() -> None:
    """清理超过24小时的任务数据."""
    now = datetime.now().timestamp()
    for task_id, task in list(tasks.items()):
        if now - task.start_time > 86400:  # 24小时
            task_dir = os.path.join(TEMP_DIR, str(task_id))
            if os.path.exists(task_dir):
                shutil.rmtree(task_dir)
            del tasks[task_id]


if __name__ == "__main__":
    uvicorn.run("api.api_service:app", host="0.0.0.0", port=8000, reload=True)
