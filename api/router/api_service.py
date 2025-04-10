"""爬虫API服务(Jira)主入口"""

import os
import shutil
import asyncio
import subprocess
from concurrent.futures import ThreadPoolExecutor
from contextlib import asynccontextmanager
import logging
from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4
from pathlib import Path

from fastapi import HTTPException, Depends, Query, Security, APIRouter
from fastapi.responses import FileResponse, StreamingResponse
from sqlmodel import Session, select
from fastapi.security import HTTPBearer

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

from api.utils import (
    create_streaming_zip_response,
    create_streaming_targz_response,
    validate_task_for_download,
)


# 配置日志
logger = logging.getLogger("uvicorn")

# 定义安全方案仅用于 API 文档生成
security_scheme = HTTPBearer(
    scheme_name="Bearer Token", description="请输入 API Token", auto_error=False
)

router = APIRouter(
    prefix="/api/jira",
    tags=["爬虫服务-Jira"],
    dependencies=[Security(security_scheme)],  # 为所有路由添加 Bearer Token 认证
)

# 临时爬虫到的文件目录
TEMP_DIR = os.path.join(os.path.dirname(__package__), "api/temp_scrapy")
os.makedirs(TEMP_DIR, exist_ok=True)


def get_task_by_id(task_id: UUID, db: Session) -> Optional[Task]:
    """根据ID获取任务."""
    task = db.get(Task, task_id)
    if task and task.task_mode == "jira":
        return task
    return None


def create_task(
    task_id: UUID, jql: str, output_dir: str, callback_url: Optional[str], db: Session, **kwargs
) -> Task:
    """创建新任务."""
    task = Task(
        id=task_id,
        status="pending",
        jql=jql,
        output_dir=output_dir,
        start_time=datetime.now().timestamp(),
        callback_url=callback_url,
        extra_data=kwargs,
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
    task_dir = str(Path(TEMP_DIR) / str(task_id))
    os.makedirs(task_dir, exist_ok=True)
    logger.info(f"Created task directory: {task_dir}")

    # 创建任务记录
    task = create_task(
        task_id=task_id,
        jql=request.jql,
        output_dir=task_dir,
        callback_url=None,
        db=db,
        **request.model_dump(exclude={"jql"}),
    )

    # 异步启动爬虫任务
    asyncio.create_task(run_crawler(task_id, **request.model_dump(exclude={"jql"})))

    return TaskResponse(
        task_id=task.id,
        message="爬虫任务建立成功",
    )


async def run_crawler(task_id: UUID, **kwargs):
    """异步运行爬虫任务."""
    try:
        # 使用同步会话，因为在线程池中执行
        db = Session(engine)
        try:
            # 获取任务信息
            task = get_task_by_id(task_id, db)
            if not task:
                logger.error(f"Task {task_id} not found")
                return

            # 更新任务状态为运行中
            update_task_status(task, "running", db=db)

            # 构建命令参数列表
            cmd_parts = [
                "uv", "run", "-m", "jira.main",
                "--jql", task.jql,
                "--output_dir", task.output_dir,
            ]

            # 从kwargs中获取可选参数
            optional_params = {
                "description_limit": kwargs.get("description_limit"),
                "comments_limit": kwargs.get("comments_limit"),
                "page_size": kwargs.get("page_size"),
                "start_at": kwargs.get("start_at")
            }

            # 添加可选参数
            for param_name, param_value in optional_params.items():
                if param_value is not None:
                    cmd_parts.extend([f"--{param_name}", str(param_value)])

            # 获取API根路径
            API_ROOT_PORT = os.getenv("API_ROOT_PORT", "8000")
            API_ROOT_PATH = os.getenv("API_ROOT_PATH", "")

            # 添加回调URL
            callback_url = f"http://localhost:{API_ROOT_PORT}{API_ROOT_PATH}/api/jira/callback/{task_id}"
            cmd_parts.extend(["--callback_url", callback_url])

            # 记录完整命令
            cmd_str = " ".join(cmd_parts)
            logger.info(f"Running command: {cmd_str}")

            # 使用线程池执行子进程
            loop = asyncio.get_event_loop()
            with ThreadPoolExecutor() as pool:
                process = await loop.run_in_executor(
                    pool,
                    lambda: subprocess.Popen(
                        cmd_parts,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        text=True,
                        encoding='utf-8',
                        errors='replace'  # 处理无法解码的字符
                    )
                )

                # 异步读取输出
                stdout, stderr = await loop.run_in_executor(pool, process.communicate)
                return_code = process.returncode

                if return_code != 0:
                    error_msg = f"爬虫进程异常退出，返回码：{return_code}"
                    if stderr:
                        error_msg += f"\n错误输出：{stderr}"
                    raise RuntimeError(error_msg)

        finally:
            db.close()

    except Exception as e:
        # 捕获其他异常
        error_msg = f"爬虫执行失败：{str(e)}"
        logger.error(error_msg)
        import traceback
        logger.error(f"异常详情：\n{traceback.format_exc()}")
        try:
            # 创建新的数据库会话来记录错误
            error_db = Session(engine)
            try:
                task = get_task_by_id(task_id, error_db)
                if task:
                    update_task_status(task, "error", error=error_msg, db=error_db)
            finally:
                error_db.close()
        except Exception as db_error:
            logger.error(f"更新任务状态失败：{str(db_error)}")


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
    "/tasks",
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
    total = len(tasks)

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


@router.post("/callback/{task_id}", include_in_schema=False)
async def task_callback(task_id: UUID, db: Session = Depends(get_db)) -> dict:
    """爬虫任务回调."""
    task = get_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在")

    update_task_status(task=task, status="completed", message="任务已完成", db=db)

    return {"status": "received"}


@router.get("/download/{task_id}", response_class=StreamingResponse)
async def download_result(
    task_id: UUID,
    format: str = Query("zip", description="下载格式，支持 zip 或 tar.gz"),
    db: Session = Depends(get_db),
) -> StreamingResponse:
    """
    下载爬虫任务结果（流式响应）

    Args:
        task_id: 任务ID
        format: 下载格式，支持 zip 或 tar.gz，默认为 zip
        db: 数据库会话

    Returns:
        StreamingResponse: 流式响应，包含压缩后的任务结果文件
    """
    try:
        # 验证任务是否可下载
        result = await validate_task_for_download(task_id, db, get_task_by_id, TEMP_DIR)
        task_dir = result["task_dir"]

        # 根据格式选择不同的下载方式
        if format.lower() == "tar.gz":
            # 创建TAR.GZ文件名
            file_name = f"scrap_result_{task_id}.tar.gz"
            # 返回流式TAR.GZ响应
            return await create_streaming_targz_response(task_dir, file_name, task_id)
        else:
            # 创建ZIP文件名
            file_name = f"scrap_result_{task_id}.zip"
            # 返回流式ZIP响应
            return await create_streaming_zip_response(task_dir, file_name, task_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载任务结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载任务结果失败: {str(e)}")


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
    task_dir = str(Path(TEMP_DIR) / str(task_id))
    if os.path.exists(task_dir):
        shutil.rmtree(task_dir)
    else:
        logger.warning(f"任务目录不存在：{task_dir}")

    # 删除数据库记录
    db.delete(task)
    db.commit()
    return {"status": "200", "message": "任务已删除"}
