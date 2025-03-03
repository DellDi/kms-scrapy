"""爬虫API服务-爬取confluence"""

import os
import shutil
import asyncio
import tempfile
import logging
import uvicorn
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from api.database.models import Task
from api.database.db import get_db, engine
from api.models.request import  CrawlKMSRequest
from api.models.response import TaskStatus, TaskResponse, TaskList, BinaryFileSchema
from api.api_service import app, TEMP_DIR

# 配置日志
logger = logging.getLogger(__name__)

# 根据ID获取任务
def get_kms_task_by_id(task_id: UUID, db: Session):
    """根据ID获取KMS任务."""
    task = db.get(Task, task_id)
    if task and task.task_mode == "kms":
        return task
    return None


# 创建新任务
def create_kms_task(
    task_id: UUID, start_url: str, output_dir: str, callback_url: Optional[str], db: Session
):
    """创建新的KMS爬虫任务."""
    task = Task(
        id=task_id,
        task_mode="kms",
        status="pending",
        jql=start_url,  # 使用jql字段存储起始URL
        output_dir=output_dir,
        start_time=datetime.now(),
        callback_url=callback_url,
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


# 更新任务状态
def update_kms_task_status(
    task: Task,
    status: str,
    message: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = None,
    **kwargs,
):
    """更新KMS任务状态."""
    task.status = status
    task.message = message

    if status in ["completed", "failed"]:
        task.end_time = datetime.now().timestamp()

    if error:
        task.error = error

    for key, value in kwargs.items():
        if hasattr(task, key):
            setattr(task, key, value)

    if db:
        db.add(task)
        db.commit()
        db.refresh(task)

    return task


@app.post(
    "/api/kms/crawl",
    response_model=TaskResponse,
    tags=["爬虫任务-kms"],
)
async def start_kms_crawl(request: CrawlKMSRequest, db: Session = Depends(get_db)) -> Task:
    """启动KMS爬虫任务."""
    # 生成任务ID
    task_id = uuid4()

    # 创建输出目录
    output_dir = os.path.join(TEMP_DIR, str(task_id))
    os.makedirs(output_dir, exist_ok=True)

    # 创建任务记录
    task = create_kms_task(
        task_id=task_id,
        start_url=request.jql,  # 使用jql字段存储起始URL
        output_dir=output_dir,
        callback_url=request.callback_url,
        db=db,
    )

    # 异步启动爬虫
    asyncio.create_task(run_kms_crawler(task_id=task_id, start_url=request.start_url))

    return TaskResponse(
        task_id=task_id,
        message="KMS爬虫任务建立成功",
    )


async def run_kms_crawler(task_id: UUID, start_url: str, **kwargs) -> None:
    """异步运行KMS爬虫任务."""
    try:
        # 创建新的数据库会话
        with Session(engine) as db:
            # 获取任务信息
            task = get_kms_task_by_id(task_id, db)
            if not task:
                logger.error(f"任务不存在: {task_id}")
                return

            # 更新任务状态为运行中
            update_kms_task_status(
                task=task, status="running", message="KMS爬虫任务启动中...", db=db
            )

            # 准备爬虫命令
            output_dir = task.output_dir

            # 构建爬虫命令
            crawler_cmd = [
                "uv",
                "run",
                "crawler/main.py",
                "--output_dir",
                output_dir,
                "--start_url",
                start_url,
                "--callback_url",
                f"http://localhost:8000/api/kms/callback/{task_id}",
            ]

            # 如果有回调URL，添加到命令中
            if kwargs.get("callback_url"):
                crawler_cmd.extend(["--callback_url", f"{kwargs.get('callback_url')}/{task_id}"])

            logger.info(f"执行爬虫命令: {' '.join(crawler_cmd)}")

            # 执行爬虫命令
            process = await asyncio.create_subprocess_exec(
                *crawler_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                text=True,
            )

            # 等待爬虫完成
            stdout, stderr = process.communicate()

            # 检查爬虫执行结果
            if process.returncode != 0:
                # 爬虫执行失败
                error_msg = stderr or "爬虫执行失败，未知错误"
                logger.error(f"爬虫执行失败: {error_msg}")
                update_kms_task_status(
                    task=task,
                    status="failed",
                    message="爬虫执行失败",
                    error=error_msg,
                    db=db,
                )
            else:
                # 爬虫执行成功
                update_kms_task_status(task=task, status="completed", message="KMS爬虫任务已完成", db=db)

    except Exception as e:
        # 捕获其他异常
        error_msg = str(e)
        logger.error(f"KMS爬虫执行失败：{error_msg}")
        try:
            # 创建新的数据库会话来记录错误
            with Session(engine) as error_db:
                task = get_kms_task_by_id(task_id, error_db)
                if task:
                    update_kms_task_status(
                        task=task, status="failed", message="爬虫执行失败", error=error_msg, db=error_db
                    )
        except Exception as e2:
            logger.error(f"更新任务状态失败：{e2}")


@app.get(
    "/api/kms/task/{task_id}",
    response_model=TaskStatus,
    tags=["爬虫任务-kms"],
)
async def get_kms_task_status(task_id: UUID, db: Session = Depends(get_db)) -> TaskStatus:
    """获取KMS任务状态."""
    task = get_kms_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")
    return TaskStatus(
        task_id=task.id,
        task_mode=task.task_mode,
        status=task.status,
        created_at=task.created_at,
        updated_at=task.updated_at,
        message=task.message,
    )


@app.get(
    "/api/kms/tasks",
    response_model=TaskList,
    tags=["爬虫任务-kms"],
)
async def list_kms_tasks(
    skip: int = Query(0, description="跳过记录数"),
    limit: int = Query(10, description="返回记录数"),
    status: str = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
) -> TaskList:
    """获取KMS任务列表."""
    query = select(Task).where(Task.task_mode == "kms")
    if status:
        query = query.where(Task.status == status)
    query = query.offset(skip).limit(limit).order_by(Task.created_at.desc())

    tasks = db.exec(query).all()
    total = db.exec(select(Task).where(Task.task_mode == "kms")).count()

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


@app.post("/api/kms/callback/{task_id}", tags=["爬虫任务-kms"], include_in_schema=False)
async def kms_task_callback(task_id: UUID, db: Session = Depends(get_db)) -> dict:
    """KMS爬虫任务回调."""
    task = get_kms_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在，请重新建立")

    update_kms_task_status(task=task, status="completed", message="任务已完成", db=db)

    return {"status": "received"}


@app.get(
    "/api/kms/download/{task_id}",
    tags=["爬虫任务-kms"],
    response_class=FileResponse,
    responses={200: {"model": BinaryFileSchema, "description": "返回ZIP格式的爬虫结果文件"}},
)
async def download_kms_result(task_id: UUID, db: Session = Depends(get_db)) -> FileResponse:
    """下载KMS任务结果."""
    try:
        task = get_kms_task_by_id(task_id, db)
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
        zip_name = f"kms_result_{task_id}.zip"
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


@app.delete(
    "/api/kms/task/{task_id}",
    tags=["爬虫任务-kms"],
    responses={
        200: {"description": "任务已删除"},
        400: {"description": "任务尚未完成，请等待任务完成后再删除}"},
    },
)
async def delete_kms_task(task_id: UUID, db: Session = Depends(get_db)) -> dict:
    """删除KMS任务."""
    task = get_kms_task_by_id(task_id, db)
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
    db.delete(task)
    db.commit()
    return {"status": "200", "message": "任务已删除"}

if __name__ == "__main__":
    uvicorn.run("api.api_kms_service:app", host="0.0.0.0", port=8000, reload=True)