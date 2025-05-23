"""爬虫API服务-爬取confluence"""

import os
import shutil
import asyncio
import logging

from datetime import datetime
from typing import Optional, List
from uuid import UUID, uuid4

from fastapi import Depends, HTTPException, Query, APIRouter, Security
from fastapi.security import HTTPBearer
from fastapi.responses import FileResponse, StreamingResponse, JSONResponse
from sqlmodel import Session, select

from api.database.models import Task
from api.database.db import get_db, engine
from api.models.request import CrawlKMSRequest
from api.models.response import TaskStatus, TaskResponse, TaskList, BinaryFileSchema
from api.router.api_service import TEMP_DIR
from api.utils import create_streaming_zip_response, create_streaming_targz_response, validate_task_for_download

# 配置日志
logger = logging.getLogger("uvicorn")

# 定义安全方案仅用于 API 文档生成
security_scheme = HTTPBearer(
    scheme_name="Bearer Token", description="请输入 API Token", auto_error=False
)

router = APIRouter(
    prefix="/api/kms",
    tags=["爬虫任务-kms"],
    dependencies=[Security(security_scheme)],  # 为所有路由添加 Bearer Token 认证
)


# 根据ID获取任务
def get_kms_task_by_id(task_id: UUID, db: Session):
    """根据ID获取KMS任务."""
    task = db.get(Task, task_id)
    if task and task.task_mode == "kms":
        return task
    return None


# 创建新任务
def create_kms_task(
    task_id: UUID,
    start_url: str,
    output_dir: str,
    callback_url: Optional[str],
    db: Session,
    **kwargs,
):
    """创建新的KMS爬虫任务."""
    task = Task(
        id=task_id,
        task_mode="kms",
        status="pending",
        jql=start_url,  # 使用jql字段存储起始URL
        output_dir=output_dir,
        start_time=datetime.now().timestamp(),  # 转换为时间戳
        callback_url=callback_url,
        extra_data=kwargs,
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


@router.post(
    "/crawl",
    response_model=TaskResponse,
)
async def start_kms_crawl(request: CrawlKMSRequest, db: Session = Depends(get_db)) -> Task:
    """启动KMS爬虫任务."""
    # 校验api_key参数
    if request.api_key:
        if not request.api_url or not request.model:
            raise HTTPException(
                status_code=400, detail="当提供api_key时，api_url和model参数必须提供"
            )

    # 生成任务ID
    task_id = uuid4()

    # 创建输出目录
    output_dir = os.path.join(TEMP_DIR, str(task_id))
    os.makedirs(output_dir, exist_ok=True)

    # 创建任务记录
    task = create_kms_task(
        task_id=task_id,
        start_url=request.start_url,
        output_dir=output_dir,
        db=db,
        callback_url=f"http://localhost:8000/api/kms/callback/{task_id}",
        **request.model_dump(exclude={"start_url"}),
    )

    # 异步启动爬虫
    asyncio.create_task(
        run_confluence_crawler(
            task_id=task_id,
            start_url=request.start_url,
            **request.model_dump(exclude={"start_url"}),
        )
    )

    return TaskResponse(
        task_id=task_id,
        message="Confluence爬虫任务建立成功",
    )


async def run_confluence_crawler(task_id: UUID, start_url: str, **kwargs) -> None:
    """异步运行Confluence爬虫任务."""
    try:
        # 使用同步会话，因为在线程池中执行
        db = Session(engine)
        try:
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

            API_ROOT_PORT = os.getenv("API_ROOT_PORT", "8000")
            API_ROOT_PATH = os.getenv("API_ROOT_PATH", "")
            # 构建爬虫命令
            crawler_cmd = [
                "uv",
                "run",
                "-m",
                "crawler.main",
                "--start_url",
                start_url,
                "--output_dir",
                output_dir,
                "--callback_url",
                f"http://localhost:{API_ROOT_PORT}{API_ROOT_PATH}/api/kms/callback/{task_id}",
            ]

            # 添加可选参数
            for key, value in kwargs.items():
                if value is not None:  # 只添加非None的参数
                    crawler_cmd.append(f"--{key}")
                    crawler_cmd.append(str(value))  # 确保值是字符串

            # 记录完整命令
            cmd_str = " ".join(crawler_cmd)
            logger.info(f"执行爬虫命令: {cmd_str}")

            # 使用线程池执行子进程
            loop = asyncio.get_event_loop()
            from concurrent.futures import ThreadPoolExecutor
            import subprocess
            
            with ThreadPoolExecutor() as pool:
                process = await loop.run_in_executor(
                    pool,
                    lambda: subprocess.Popen(
                        crawler_cmd,
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

                # 检查爬虫执行结果
                if return_code != 0:
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
                    update_kms_task_status(
                        task=task, status="completed", message="KMS爬虫任务已完成", db=db
                    )
        finally:
            db.close()

    except Exception as e:
        # 捕获其他异常
        error_msg = str(e)
        logger.error(f"Confluence爬虫执行失败：{error_msg}")
        import traceback
        logger.error(f"异常详情：\n{traceback.format_exc()}")
        try:
            # 创建新的数据库会话来记录错误
            error_db = Session(engine)
            try:
                task = get_kms_task_by_id(task_id, error_db)
                if task:
                    update_kms_task_status(
                        task=task,
                        status="failed",
                        message="爬虫执行失败",
                        error=error_msg,
                        db=error_db,
                    )
            finally:
                error_db.close()
        except Exception as e2:
            logger.error(f"更新任务状态失败：{e2}")


@router.get(
    "/task/{task_id}",
    response_model=TaskStatus,
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


@router.get(
    "/tasks",
    response_model=TaskList,
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
async def kms_task_callback(task_id: UUID, db: Session = Depends(get_db)) -> dict:
    """KMS爬虫任务回调."""
    task = get_kms_task_by_id(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="任务不存在，请重新建立")

    update_kms_task_status(task=task, status="completed", message="任务已完成", db=db)

    return {"status": "received"}


@router.get("/download/{task_id}", response_class=StreamingResponse)
async def download_kms_result(
    task_id: UUID,
    format: str = Query("zip", description="下载格式，支持 zip 或 tar.gz"),
    db: Session = Depends(get_db)
) -> StreamingResponse:
    """
    下载 KMS 任务结果（流式响应）

    Args:
        task_id: 任务ID
        format: 下载格式，支持 zip 或 tar.gz，默认为 zip
        db: 数据库会话

    Returns:
        StreamingResponse: 流式响应，包含压缩后的任务结果文件
    """
    try:
        # 验证任务是否可下载
        result = await validate_task_for_download(task_id, db, get_kms_task_by_id, TEMP_DIR)
        task_dir = result["task_dir"]

        # 根据格式选择不同的下载方式
        if format.lower() == "tar.gz":
            # 创建TAR.GZ文件名
            file_name = f"kms_result_{task_id}.tar.gz"
            # 返回流式TAR.GZ响应
            return await create_streaming_targz_response(task_dir, file_name, task_id)
        else:
            # 创建ZIP文件名
            file_name = f"kms_result_{task_id}.zip"
            # 返回流式ZIP响应
            return await create_streaming_zip_response(task_dir, file_name, task_id)

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"下载 KMS 任务结果失败: {str(e)}")
        raise HTTPException(status_code=500, detail=f"下载 KMS 任务结果失败: {str(e)}")


@router.delete(
    "/task/{task_id}",
    responses={
        200: {"description": "任务已删除"},
        400: {"description": "任务尚未完成，请等待任务完成后再删除"},
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
