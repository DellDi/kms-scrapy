"""爬虫API服务(Jira)主入口"""

import os
import shutil
import asyncio
import tempfile
import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import  HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select

# 新的示例和router模式
from fastapi import APIRouter

from api.models.request import CrawlRequest
from api.database.models import Task, ApiLog
from api.database.db import get_db, engine
from api.models.response import (
    BinaryFileSchema,
    TaskList,
    TaskResponse,
    TaskStatus,
)

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/jira", tags=["爬虫服务-Jira"])

# 临时文件目录
TEMP_DIR = os.path.join(os.path.dirname(__file__), "temp")
os.makedirs(TEMP_DIR, exist_ok=True)

def get_task_by_id(task_id: UUID, db: Session) -> Optional[Task]:
    """根据ID获取任务."""
    task = db.get(Task, task_id)
    if task and task.task_mode == "jira":
        return task
    return None

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


def update_task_status(
    task: Task,
    status: str,
    message: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = None,
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

    if db:
        db.commit()
        db.refresh(task)
    return task


@router.post(
    "/crawl",
    response_model=TaskResponse,
)
async def start_crawl(request: CrawlRequest, db: Session = Depends(get_db)) -> Task:
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
    asyncio.create_task(run_crawler(task_id, **request.model_dump()))

    return TaskResponse(
        task_id=task.id,
        message="爬虫任务建立成功",
    )


async def run_crawler(task_id: UUID, **kwargs) -> None:
    """异步运行爬虫任务."""
    try:
        # 创建新的数据库会话
        with Session(engine) as db:
            # 重新获取任务对象
            task = get_task_by_id(task_id, db)
            if not task:
                logger.error(f"Task not found: {task_id}")
                return
            start_at = kwargs.get("start_at")
            page_size = kwargs.get("page_size")
            # 更新任务状态为运行中
            update_task_status(task=task, status="running", message="Crawler is running", db=db)

            # 构建命令
            cmd = [
                "uv",
                "run",
                "jira/main.py",
                "--jql",
                task.jql,
                "--start_at",
                str(start_at),
                "--page_size",
                str(page_size),
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

            # 在同一个会话中更新状态
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
                update_task_status(task=task, status="completed", message="爬虫任务已完成", db=db)

    except Exception as e:
        # 捕获其他异常
        error_msg = str(e)
        logger.error(f"爬虫执行失败：{error_msg}")
        try:
            # 创建新的数据库会话来记录错误
            with Session(engine) as error_db:
                task = get_task_by_id(task_id, error_db)
                if task:
                    update_task_status(
                        task=task,
                        status="failed",
                        message=f"Error: {error_msg}",
                        error=error_msg,
                        db=error_db,
                    )
        except Exception as e2:
            logger.error(f"更新任务状态失败：{e2}")


@router.get(
    "/task/{task_id}",
    response_model=TaskStatus,
)
async def get_task_status(task_id: UUID, db: Session = Depends(get_db)) -> TaskStatus:
    """获取任务状态."""
    task = get_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务无法找到，请重新建立")
    return TaskStatus(
        task_id=task.id,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        message=task.message,
    )


@router.get(
    "/api/tasks",
    response_model=TaskList,
)
async def list_tasks(
    skip: int = Query(0, description="跳过记录数"),
    limit: int = Query(10, description="返回记录数"),
    status: str = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
) -> TaskList:
    """获取jira任务列表."""
    query = select(Task).where(Task.task_mode == "jira")
    if status:
        query = query.where(Task.status == status)
    query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())

    tasks = db.exec(query).all()
    total = tasks.count(0)

    return TaskList(
        tasks=[
            TaskStatus(
                task_id=t.id,
                task_mode=t.task_mode,
                status=t.status,
                created_at=t.created_at,
                updated_at=t.updated_at,
                message=t.message,
            )
            for t in tasks
        ],
        total=total,
        skip=skip,
        limit=limit,
    )


@router.post("/callback/{task_id}",  include_in_schema=False)
async def task_callback(task_id: UUID, db: Session = Depends(get_db)) -> dict:
    """爬虫任务回调."""
    task = get_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_task_status(task=task, status="completed", message="任务已完成", db=db)

    return {"status": "received"}


@router.get(
    "/download/{task_id}",
    response_class=FileResponse,
    responses={200: {"model": BinaryFileSchema, "description": "返回ZIP格式的爬虫结果文件"}},
)
async def download_result(task_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    """下载任务结果."""
    try:
        task = get_task_by_id(task_id, db)
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")

        if task.status != "completed":
            raise HTTPException(
                status_code=400, detail=f"Task is not completed (current status: {task.status})"
            )

        # 检查源目录
        task_dir = os.path.join(TEMP_DIR, str(task_id))
        logger.info(f"Checking task directory: {task_dir}")

        if not os.path.exists(task_dir):
            raise HTTPException(status_code=404, detail="任务目录不存在，请重新建立任务")

        # 创建临时zip文件
        zip_name = f"scrap_result_{task_id}.zip"
        fd, zip_path = tempfile.mkstemp(suffix=".zip")
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
                headers={"Content-Disposition": f'attachment; filename="{zip_name}"'},
            )
        except Exception as e:
            # 清理临时文件
            if os.path.exists(zip_path):
                os.unlink(zip_path)
            raise HTTPException(status_code=500, detail=f"Failed to create ZIP file: {str(e)}")

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Download failed: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Download failed: {str(e)}")


@router.delete(
    "/task/{task_id}",
    responses={
        200: {"description": "任务已删除"},
        400: {"description": "任务尚未完成，请等待任务完成后再删除}"},
    },
)
async def delete_task(task_id: UUID, db: Session = Depends(get_db)) -> dict:
    """删除任务."""
    task = get_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    # 检查任务状态
    if task.status == "pending":
        raise HTTPException(
            status_code=400, detail=f"任务尚未完成，请等待任务完成后再删除。当前状态：{task.status}"
        )

    # 删除任务目录
    task_dir = os.path.join(TEMP_DIR, str(task_id))
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)
    else:
        logger.warning(f"任务目录不存在：{task_dir}")

    # 删除数据库记录
    db.exec(Task).filter(Task.id == task_id).delete()
    db.commit()
    return {"status": "200", "message": "任务已删除"}


