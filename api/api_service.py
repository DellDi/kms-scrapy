"""Jira爬虫API服务."""
import os
import shutil
import asyncio
import tempfile
import logging
from datetime import datetime
from typing import Optional, List, Dict
from uuid import UUID, uuid4

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session

from api.models.request import CrawlRequest
from api.models.response import TaskStatus, TaskResponse, CallbackResponse
from api.database.db import get_db, init_db, SessionLocal
from api.database.models import ApiLog, Task
from api.middleware import APILoggingMiddleware

# 配置日志
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
    """,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json"
)

# 添加中间件
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
app.add_middleware(APILoggingMiddleware)

# 临时文件目录
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

# 初始化数据库
init_db()

def get_task_by_id(task_id: UUID, db: Session) -> Optional[Task]:
    """根据ID获取任务."""
    return db.query(Task).filter(Task.id == task_id).first()

def create_task(
    task_id: UUID,
    jql: str,
    output_dir: str,
    callback_url: Optional[str],
    db: Session
) -> TaskStatus:
    """创建新任务."""
    task = Task(
        id=task_id,
        status="pending",
        jql=jql,
        output_dir=output_dir,
        start_time=datetime.now().timestamp(),
        callback_url=callback_url
    )
    db.add(task)
    db.commit()
    db.refresh(task)

    return TaskStatus(
        task_id=task.id,
        status=task.status,
        start_time=task.start_time,
        end_time=task.end_time,
        message=task.message or ""
    )

def update_task_status(
    task: Task,
    status: str,
    message: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = None,
    **kwargs
) -> TaskStatus:
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

    return TaskStatus(
        task_id=task.id,
        status=task.status,
        start_time=task.start_time,
        end_time=task.end_time,
        message=task.message or ""
    )

async def run_crawler(task_id: UUID, _: Session) -> None:
    """异步运行爬虫任务."""
    try:
        # 创建新的数据库会话
        db = SessionLocal()
        try:
            # 重新获取任务对象
            task = get_task_by_id(task_id, db)
            if not task:
                logger.error(f"Task not found: {task_id}")
                return

            # 更新任务状态为运行中
            update_task_status(
                task=task,
                status="running",
                message="Crawler is running",
                db=db
            )

            # 构建命令
            cmd = [
                "uv", "run", "jira/main.py",
                "--jql", task.jql,
                "--output_dir", task.output_dir,
                "--callback_url", f"http://localhost:8000/api/jira/callback/{task_id}"
            ]

            # 异步执行爬虫命令
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )

            # 等待进程完成
            stdout, stderr = await process.communicate()

            # 重新获取任务对象（避免会话过期）
            task = get_task_by_id(task_id, db)
            if not task:
                logger.error(f"Task not found after execution: {task_id}")
                return

            if process.returncode != 0:
                # 爬虫执行失败
                update_task_status(
                    task=task,
                    status="failed",
                    message=f"Crawler failed: {stderr.decode()}",
                    error=stderr.decode(),
                    db=db
                )
            else:
                # 爬虫执行成功
                update_task_status(
                    task=task,
                    status="completed",
                    message="Crawler completed successfully",
                    db=db
                )

        finally:
            db.close()

    except Exception as e:
        # 捕获其他异常
        error_msg = str(e)
        logger.error(f"Crawler execution failed: {error_msg}")
        try:
            # 创建新的数据库会话来记录错误
            error_db = SessionLocal()
            try:
                task = get_task_by_id(task_id, error_db)
                if task:
                    update_task_status(
                        task=task,
                        status="failed",
                        message=f"Error: {error_msg}",
                        error=error_msg,
                        db=error_db
                    )
            finally:
                error_db.close()
        except Exception as e2:
            logger.error(f"Failed to record error status: {e2}")

@app.post(
    "/api/jira/crawl",
    response_model=TaskResponse,
    tags=["爬虫任务"],
)
async def start_crawl(
    request: CrawlRequest,
    db: Session = Depends(get_db)
) -> TaskResponse:
    """启动爬虫任务."""
    task_id = uuid4()
    task_dir = os.path.join(TEMP_DIR, str(task_id))
    os.makedirs(task_dir, exist_ok=True)
    logger.info(f"Created task directory: {task_dir}")

    # 创建任务记录
    task_status = create_task(
        task_id=task_id,
        jql=request.jql,
        output_dir=task_dir,
        callback_url=None,
        db=db
    )

    # 异步启动爬虫任务
    asyncio.create_task(run_crawler(task_id, db))

    return TaskResponse(
        task_id=task_id,
        message="Task created successfully"
    )

@app.get(
    "/api/jira/task/{task_id}",
    response_model=TaskStatus,
    tags=["爬虫任务"],
)
async def get_task_status(
    task_id: UUID,
    db: Session = Depends(get_db)
) -> TaskStatus:
    """获取任务状态."""
    task = get_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    return TaskStatus(
        task_id=task.id,
        status=task.status,
        start_time=task.start_time,
        end_time=task.end_time,
        message=task.message or ""
    )

@app.get(
    "/api/jira/download/{task_id}",
    tags=["爬虫任务"],
)
async def download_result(
    task_id: UUID,
    db: Session = Depends(get_db)
) -> FileResponse:
    """下载任务结果."""
    try:
        task = get_task_by_id(task_id, db)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status != "completed":
            raise HTTPException(
                status_code=400,
                detail=f"Task is not completed (current status: {task.status})"
            )

        # 检查源目录
        task_dir = os.path.join(TEMP_DIR, str(task_id))
        logger.info(f"Checking task directory: {task_dir}")

        if not os.path.exists(task_dir):
            raise HTTPException(
                status_code=404,
                detail="Task result directory not found"
            )

        # 创建临时zip文件
        zip_name = f"jira_result_{task_id}.zip"
        fd, zip_path = tempfile.mkstemp(suffix='.zip')
        os.close(fd)

        try:
            # 创建ZIP文件
            logger.info(f"Creating ZIP archive from {task_dir} to {zip_path}")
            base_path = os.path.splitext(zip_path)[0]  # 移除.zip后缀
            shutil.make_archive(base_path, "zip", task_dir)

            return FileResponse(
                path=zip_path,
                filename=zip_name,
                media_type="application/zip",
                headers={
                    "Content-Disposition": f'attachment; filename="{zip_name}"'
                }
            )
        except Exception as e:
            # 清理临时文件
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            raise HTTPException(
                status_code=500,
                detail=f"Failed to create ZIP file: {str(e)}"
            )

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(
            status_code=500,
            detail=f"Download failed: {str(e)}"
        )

@app.post(
    "/api/jira/callback/{task_id}",
    response_model=CallbackResponse,
    tags=["爬虫任务"],
    include_in_schema=False
)
async def task_callback(
    task_id: UUID,
    db: Session = Depends(get_db)
) -> CallbackResponse:
    """爬虫任务回调."""
    task = get_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    task_status = update_task_status(
        task=task,
        status="completed",
        message="Task completed successfully",
        db=db
    )

    return CallbackResponse(status="received")

@app.get("/api/tasks", response_model=List[dict])
async def list_tasks(
    skip: int = Query(0, description="跳过记录数"),
    limit: int = Query(10, description="返回记录数"),
    status: str = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db)
) -> List[dict]:
    """获取任务列表."""
    query = db.query(Task)

    if status:
        query = query.filter(Task.status == status)

    tasks = query.order_by(Task.created_at.desc()).offset(skip).limit(limit).all()
    return [task.to_dict() for task in tasks]

async def cleanup_old_tasks(db: Session) -> None:
    """清理超过24小时的任务数据."""
    cutoff_time = datetime.now().timestamp() - 86400  # 24小时前
    old_tasks = db.query(Task).filter(Task.start_time < cutoff_time).all()

    for task in old_tasks:
        task_dir = os.path.join(TEMP_DIR, str(task.id))
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
        db.delete(task)

    db.commit()

if __name__ == "__main__":
    uvicorn.run(
        "api.api_service:app",
        host="0.0.0.0",
        port=8000,
        reload=True
    )
