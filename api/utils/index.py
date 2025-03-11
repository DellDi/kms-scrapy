"""
API 工具函数
"""

import os
import io
import zipfile
import tarfile
import asyncio
import logging
from typing import Dict, Any, AsyncGenerator, Optional
from uuid import UUID
from fastapi import HTTPException
from fastapi.responses import StreamingResponse
from sqlmodel import Session

# 配置日志
logger = logging.getLogger("uvicorn")


async def create_streaming_zip_response(
    task_dir: str,
    zip_name: str,
    task_id: UUID,
    chunk_size: int = 1024 * 1024,  # 默认 1MB 块大小
) -> StreamingResponse:
    """
    创建流式 ZIP 响应，用于大文件下载

    Args:
        task_dir: 要压缩的目录路径
        zip_name: 下载文件名
        task_id: 任务 ID
        chunk_size: 分块大小，默认 1MB

    Returns:
        StreamingResponse: 流式响应对象
    """
    if not os.path.exists(task_dir):
        raise HTTPException(status_code=404, detail="任务目录不存在，请重新建立任务")

    logger.info(f"准备流式下载目录: {task_dir}, 任务ID: {task_id}")

    # 预计算 ZIP 文件大小
    async def calculate_zip_size():
        total_size = 0
        file_count = 0

        # 收集所有文件信息
        for root, _, files in os.walk(task_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                total_size += file_size
                file_count += 1

        # ZIP 压缩后的大小估算 (压缩比约为 0.6-0.7，保守估计用 0.8)
        estimated_zip_size = int(total_size * 0.8)
        logger.info(
            f"预计算完成: {file_count} 个文件, 原始大小: {total_size/1024/1024:.2f}MB, 估计ZIP大小: {estimated_zip_size/1024/1024:.2f}MB"
        )

        return estimated_zip_size, file_count

    # 计算估计大小
    estimated_size, file_count = await calculate_zip_size()

    # 创建流式响应生成器
    async def zip_directory_stream() -> AsyncGenerator[bytes, None]:
        """异步生成 ZIP 文件流"""
        # 创建内存中的 ZIP 文件
        zip_buffer = io.BytesIO()

        # 在线程池中执行 ZIP 压缩（避免阻塞事件循环）
        def create_zip() -> io.BytesIO:
            """在线程池中创建 ZIP 文件"""
            logger.info(f"开始压缩目录: {task_dir}")
            try:
                with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as zf:
                    total_size = 0

                    for root, _, files in os.walk(task_dir):
                        for file in files:
                            file_path = os.path.join(root, file)
                            arcname = os.path.relpath(file_path, task_dir)

                            # 添加文件到 ZIP
                            zf.write(file_path, arcname=arcname)

                            # 统计信息
                            total_size += os.path.getsize(file_path)

                    logger.info(
                        f"压缩完成: {file_count} 个文件, 总大小: {total_size/1024/1024:.2f}MB"
                    )

                # 重置缓冲区位置
                zip_buffer.seek(0)
                return zip_buffer
            except Exception as e:
                logger.error(f"创建 ZIP 文件失败: {str(e)}")
                raise HTTPException(status_code=500, detail=f"创建 ZIP 文件失败: {str(e)}")

        # 异步执行 ZIP 创建
        loop = asyncio.get_event_loop()
        buffer = await loop.run_in_executor(None, create_zip)
        
        # 获取实际大小
        actual_size = buffer.getbuffer().nbytes
        logger.info(f"ZIP 文件实际大小: {actual_size/1024/1024:.2f}MB")
        
        # 更新估计大小为实际大小
        nonlocal estimated_size
        estimated_size = actual_size

        # 分块读取并返回
        logger.info(f"开始流式传输 ZIP 文件, 块大小: {chunk_size/1024:.2f}KB")
        bytes_sent = 0
        start_time = asyncio.get_event_loop().time()

        while True:
            chunk = buffer.read(chunk_size)
            if not chunk:
                break

            bytes_sent += len(chunk)
            yield chunk

            # 每 10MB 记录一次日志
            if bytes_sent % (10 * 1024 * 1024) < chunk_size:
                elapsed = asyncio.get_event_loop().time() - start_time
                speed = bytes_sent / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                logger.info(f"已传输: {bytes_sent/1024/1024:.2f}MB, 速度: {speed:.2f}MB/s")

        # 记录总传输信息
        total_time = asyncio.get_event_loop().time() - start_time
        logger.info(
            f"传输完成: 总大小 {bytes_sent/1024/1024:.2f}MB, "
            f"耗时 {total_time:.2f}秒, "
            f"平均速度 {bytes_sent/(1024*1024*total_time) if total_time > 0 else 0:.2f}MB/s"
        )

    # 返回流式响应，不包含 Content-Length 头
    headers = {
        "Content-Disposition": f'attachment; filename="{zip_name}"',
    }
    
    # 创建生成器
    generator = zip_directory_stream()
    
    # 返回流式响应
    return StreamingResponse(generator, media_type="application/zip", headers=headers)


async def create_streaming_targz_response(
    task_dir: str,
    targz_name: str,
    task_id: UUID,
    chunk_size: int = 1024 * 1024,  # 默认 1MB 块大小
) -> StreamingResponse:
    """
    创建流式 TAR.GZ 响应，用于大文件下载

    TAR.GZ 格式相比 ZIP 有以下优势：
    1. 更高的压缩率，特别是对于文本文件
    2. 更好的流式处理支持，不需要在文件末尾写入中央目录
    3. 更低的内存占用
    4. 在 Linux/Mac 系统上有更好的兼容性

    Args:
        task_dir: 要压缩的目录路径
        targz_name: 下载文件名
        task_id: 任务 ID
        chunk_size: 分块大小，默认 1MB

    Returns:
        StreamingResponse: 流式响应对象
    """
    if not os.path.exists(task_dir):
        raise HTTPException(status_code=404, detail="任务目录不存在，请重新建立任务")

    logger.info(f"准备流式下载目录(tar.gz): {task_dir}, 任务ID: {task_id}")

    # 预计算 TAR.GZ 文件大小
    async def calculate_targz_size():
        total_size = 0
        file_count = 0
        file_list = []

        # 收集所有文件信息
        for root, _, files in os.walk(task_dir):
            for file in files:
                file_path = os.path.join(root, file)
                file_size = os.path.getsize(file_path)
                arcname = os.path.relpath(file_path, task_dir)
                file_list.append((file_path, arcname))
                total_size += file_size
                file_count += 1

        # TAR.GZ 压缩后的大小估算 (压缩比约为 0.3-0.5，保守估计用 0.6)
        estimated_targz_size = int(total_size * 0.6)
        logger.info(
            f"预计算完成: {file_count} 个文件, 原始大小: {total_size/1024/1024:.2f}MB, 估计TAR.GZ大小: {estimated_targz_size/1024/1024:.2f}MB"
        )

        return estimated_targz_size, file_count, file_list

    # 计算估计大小和获取文件列表
    estimated_size, file_count, file_list = await calculate_targz_size()

    # 创建真正的流式响应生成器
    async def real_streaming_targz() -> AsyncGenerator[bytes, None]:
        """真正的流式 TAR.GZ 生成器，边压缩边传输"""

        # 创建读写管道
        read_fd, write_fd = os.pipe()
        read_pipe = os.fdopen(read_fd, "rb")
        write_pipe = os.fdopen(write_fd, "wb")

        # 压缩任务
        async def compress_task():
            try:
                with tarfile.open(fileobj=write_pipe, mode="w|gz", compresslevel=6) as tf:
                    total_size = 0

                    for file_path, arcname in file_list:
                        # 添加文件到 TAR.GZ
                        tf.add(file_path, arcname=arcname)

                        # 统计信息
                        file_size = os.path.getsize(file_path)
                        total_size += file_size

                        # 定期记录日志
                        if total_size % (50 * 1024 * 1024) < file_size:  # 每 50MB 记录一次
                            logger.info(f"已压缩(tar.gz): {total_size/1024/1024:.2f}MB")

                logger.info(
                    f"压缩完成(tar.gz): {file_count} 个文件, 总大小: {total_size/1024/1024:.2f}MB"
                )
            except Exception as e:
                logger.error(f"创建 TAR.GZ 文件失败: {str(e)}")
            finally:
                # 关闭写入管道
                write_pipe.close()

        # 在后台启动压缩任务
        compress_task_obj = asyncio.create_task(compress_task())

        # 从读取管道中读取数据并返回
        bytes_sent = 0
        start_time = asyncio.get_event_loop().time()

        try:
            while True:
                # 从管道读取数据
                chunk = await asyncio.get_event_loop().run_in_executor(
                    None, read_pipe.read, chunk_size
                )
                if not chunk:
                    break

                bytes_sent += len(chunk)
                yield chunk

                # 每 10MB 记录一次日志
                if bytes_sent % (10 * 1024 * 1024) < chunk_size:
                    elapsed = asyncio.get_event_loop().time() - start_time
                    speed = bytes_sent / (1024 * 1024 * elapsed) if elapsed > 0 else 0
                    logger.info(
                        f"已传输(tar.gz): {bytes_sent/1024/1024:.2f}MB, 速度: {speed:.2f}MB/s"
                    )

            # 等待压缩任务完成
            await compress_task_obj

            # 记录总传输信息
            total_time = asyncio.get_event_loop().time() - start_time
            logger.info(
                f"传输完成(tar.gz): 总大小 {bytes_sent/1024/1024:.2f}MB, "
                f"耗时 {total_time:.2f}秒, "
                f"平均速度 {bytes_sent/(1024*1024*total_time) if total_time > 0 else 0:.2f}MB/s"
            )
        finally:
            # 关闭读取管道
            read_pipe.close()

            # 如果压缩任务还在运行，取消它
            if not compress_task_obj.done():
                compress_task_obj.cancel()
                try:
                    await compress_task_obj
                except asyncio.CancelledError:
                    pass

    # 返回流式响应，不包含 Content-Length 头
    headers = {
        "Content-Disposition": f'attachment; filename="{targz_name}"',
    }

    return StreamingResponse(real_streaming_targz(), media_type="application/gzip", headers=headers)


async def validate_task_for_download(
    task_id: UUID, db: Session, get_task_func: callable, temp_dir: str
) -> Dict[str, Any]:
    """
    验证任务是否可以下载

    Args:
        task_id: 任务 ID
        db: 数据库会话
        get_task_func: 获取任务的函数
        temp_dir: 临时目录路径

    Returns:
        Dict: 包含任务目录和任务对象的字典
    """
    # 获取任务
    task = get_task_func(task_id, db)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")

    # 检查任务状态
    if task.status != "completed":
        raise HTTPException(
            status_code=400, detail=f"Task is not completed (current status: {task.status})"
        )

    # 检查源目录
    task_dir = os.path.join(temp_dir, str(task_id))
    logger.info(f"检查任务目录: {task_dir}")

    if not os.path.exists(task_dir):
        raise HTTPException(status_code=404, detail="任务目录不存在，请重新建立任务")

    return {"task_dir": task_dir, "task": task}
