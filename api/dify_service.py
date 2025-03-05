"""Dify 知识库导入 API 服务"""

import os
import shutil
import asyncio
import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID

from fastapi import HTTPException, Depends, Query
from fastapi.responses import FileResponse
from sqlmodel import Session, select

from fastapi import APIRouter

from api.models.request import DifyUploadRequest
from api.database.models import DifyTask, Task
from api.database.db import get_db, engine
from api.models.response import (
    DifyTaskStatus,
    DifyTaskResponse,
    DifyTaskList,
)
from api.api_service import TEMP_DIR

# 配置日志
logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/dify", tags=["知识库服务-Dify"])


def get_dify_task_by_id(task_id: UUID, db: Session) -> Optional[DifyTask]:
    """根据ID获取Dify任务."""
    return db.get(DifyTask, task_id)


def get_task_by_id(task_id: UUID, db: Session) -> Optional[Task]:
    """根据ID获取爬虫任务."""
    return db.get(Task, task_id)


def create_dify_task(
    task_id: UUID,
    crawler_task_id: UUID,
    dataset_prefix: str,
    max_docs: int,
    db: Session
) -> DifyTask:
    """创建新的Dify任务."""
    # 获取爬虫任务的输出目录路径
    crawler_task = get_task_by_id(crawler_task_id, db)
    if not crawler_task:
        raise HTTPException(status_code=404, detail=f"爬虫任务 {crawler_task_id} 不存在")

    # 检查爬虫任务的输出目录是否存在
    task_dir = os.path.join(TEMP_DIR, str(crawler_task_id))
    if not os.path.exists(task_dir) or not os.path.isdir(task_dir):
        raise HTTPException(status_code=404, detail=f"爬虫任务目录 {task_dir} 不存在")

    task = DifyTask(
        id=task_id,
        status="pending",
        input_dir=task_dir,  # 使用爬虫任务的输出目录
        dataset_prefix=dataset_prefix,
        max_docs=max_docs,
        start_time=datetime.now().timestamp(),
        extra_data={"crawler_task_id": str(crawler_task_id)}  # 记录关联的爬虫任务ID
    )
    db.add(task)
    db.commit()
    db.refresh(task)
    return task


def update_dify_task_status(
    task: DifyTask,
    status: str,
    message: Optional[str] = None,
    error: Optional[str] = None,
    db: Session = None,
    **kwargs,
) -> DifyTask:
    """更新Dify任务状态."""
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
    "/upload/{crawler_task_id}",
    response_model=DifyTaskResponse,
)
async def start_dify_upload(
    crawler_task_id: UUID,
    request: DifyUploadRequest,
    db: Session = Depends(get_db)
) -> DifyTaskResponse:
    """启动Dify知识库导入任务.

    需要指定已存在的爬虫任务ID，将使用该爬虫任务的输出作为Dify导入的输入。
    """
    # 检查爬虫任务是否存在
    crawler_task = get_task_by_id(crawler_task_id, db)
    if not crawler_task:
        raise HTTPException(status_code=404, detail=f"爬虫任务 {crawler_task_id} 不存在")

    # 检查爬虫任务目录是否存在
    task_dir = os.path.join(TEMP_DIR, str(crawler_task_id))
    if not os.path.exists(task_dir) or not os.path.isdir(task_dir):
        raise HTTPException(status_code=404, detail=f"爬虫任务目录 {task_dir} 不存在")

    # 生成新的Dify任务ID
    from uuid import uuid4
    dify_task_id = uuid4()

    # 创建任务记录
    task = create_dify_task(
        task_id=dify_task_id,
        crawler_task_id=crawler_task_id,
        dataset_prefix=request.dataset_prefix,
        max_docs=request.max_docs,
        db=db
    )

    # 异步启动Dify导入任务
    asyncio.create_task(run_dify_uploader(dify_task_id, **request.model_dump()))

    return DifyTaskResponse(
        task_id=task.id,
        message=f"Dify知识库导入任务已建立，将处理爬虫任务 {crawler_task_id} 的输出",
    )


async def run_dify_uploader(task_id: UUID, **kwargs) -> None:
    """异步运行Dify知识库导入任务."""
    try:
        # 创建新的数据库会话
        with Session(engine) as db:
            # 重新获取任务对象
            task = get_dify_task_by_id(task_id, db)
            if not task:
                logger.error(f"Task not found: {task_id}")
                return

            # 更新任务状态为运行中
            update_dify_task_status(task=task, status="running", message="Dify uploader is running", db=db)

            # 构建命令
            cmd = [
                "python",
                "dify/main.py",
                "--dataset-prefix",
                task.dataset_prefix,
                "--max-docs",
                str(task.max_docs),
                "--input-dir",
                task.input_dir,
            ]

            # 异步执行命令
            process = await asyncio.create_subprocess_exec(
                *cmd, stdout=asyncio.subprocess.PIPE, stderr=asyncio.subprocess.PIPE
            )

            # 等待进程完成
            stdout, stderr = await process.communicate()

            # 在同一个会话中更新状态
            if process.returncode != 0:
                # 执行失败
                update_dify_task_status(
                    task=task,
                    status="failed",
                    message=f"Dify uploader failed: {stderr.decode()}",
                    error=stderr.decode(),
                    db=db,
                )
            else:
                # 执行成功
                # 解析输出以获取上传统计信息
                stdout_text = stdout.decode()
                total_files = 0
                successful_uploads = 0

                for line in stdout_text.splitlines():
                    if "总文件数:" in line:
                        try:
                            total_files = int(line.split(":")[-1].strip())
                        except ValueError:
                            pass
                    elif "成功上传:" in line:
                        try:
                            successful_uploads = int(line.split(":")[-1].strip())
                        except ValueError:
                            pass

                update_dify_task_status(
                    task=task,
                    status="completed",
                    message="Dify知识库导入任务已完成",
                    total_files=total_files,
                    successful_uploads=successful_uploads,
                    db=db
                )

    except Exception as e:
        # 捕获其他异常
        error_msg = str(e)
        logger.error(f"Dify知识库导入执行失败：{error_msg}")
        try:
            # 创建新的数据库会话来记录错误
            with Session(engine) as error_db:
                task = get_dify_task_by_id(task_id, error_db)
                if task:
                    update_dify_task_status(
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
    response_model=DifyTaskStatus,
)
async def get_dify_task_status(task_id: UUID, db: Session = Depends(get_db)) -> DifyTaskStatus:
    """获取Dify任务状态."""
    task = get_dify_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务无法找到，请重新建立")

    return DifyTaskStatus(
        task_id=task.id,
        status=task.status,
        input_dir=task.input_dir,
        dataset_prefix=task.dataset_prefix,
        max_docs=task.max_docs,
        created_at=task.created_at,
        updated_at=task.updated_at,
        message=task.message,
        total_files=task.total_files,
        successful_uploads=task.successful_uploads,
        duration_seconds=task.duration_seconds,
    )


@router.get(
    "/tasks",
    response_model=DifyTaskList,
)
async def list_dify_tasks(
    skip: int = Query(0, description="跳过记录数"),
    limit: int = Query(10, description="返回记录数"),
    status: str = Query(None, description="按状态筛选"),
    db: Session = Depends(get_db),
) -> DifyTaskList:
    """获取Dify任务列表."""
    query = select(DifyTask)

    if status:
        query = query.where(DifyTask.status == status)

    # 获取总数
    total_query = query
    total = len(db.exec(total_query).all())

    # 分页查询
    query = query.offset(skip).limit(limit).order_by(DifyTask.created_at.desc())
    tasks = db.exec(query).all()

    # 转换为响应模型
    task_statuses = [
        DifyTaskStatus(
            task_id=task.id,
            status=task.status,
            input_dir=task.input_dir,
            dataset_prefix=task.dataset_prefix,
            max_docs=task.max_docs,
            created_at=task.created_at,
            updated_at=task.updated_at,
            message=task.message,
            total_files=task.total_files,
            successful_uploads=task.successful_uploads,
            duration_seconds=task.duration_seconds,
        )
        for task in tasks
    ]

    return DifyTaskList(
        tasks=task_statuses,
        total=total,
        skip=skip,
        limit=limit,
    )


@router.delete(
    "/task/{task_id}",
    response_model=DifyTaskResponse,
)
async def delete_dify_task(task_id: UUID, db: Session = Depends(get_db)) -> DifyTaskResponse:
    """删除Dify任务."""
    task = get_dify_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务无法找到")

    # 只删除任务记录
    db.delete(task)
    db.commit()

    return DifyTaskResponse(
        task_id=task_id,
        message="任务已成功删除",
    )
