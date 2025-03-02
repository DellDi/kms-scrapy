"""API请求日志记录中间件."""

import json
import time
from typing import Callable

from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from sqlalchemy.orm import Session

from api.database.db import get_db
from api.database.models import ApiLog


class APILoggingMiddleware(BaseHTTPMiddleware):
    """API请求日志记录中间件."""

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并记录日志."""
        # 记录开始时间
        start_time = time.time()

        # 准备记录请求信息
        path = request.url.path
        method = request.method
        client_ip = request.client.host
        user_agent = request.headers.get("user-agent")

        # 获取请求参数
        params = dict(request.query_params)

        # 获取请求体
        try:
            body = await request.body()
            body_str = body.decode() if body else None
        except Exception:
            body_str = None

        response = None
        error_message = None

        try:
            # 处理请求
            response = await call_next(request)

            # 获取响应内容
            response_body = b""
            async for chunk in response.body_iterator:
                response_body += chunk

            # 重新构建响应
            return Response(
                content=response_body,
                status_code=response.status_code,
                headers=dict(response.headers),
                media_type=response.media_type,
            )

        except Exception as e:
            error_message = str(e)
            raise

        finally:
            # 计算处理时长
            duration = int((time.time() - start_time) * 1000)

            try:
                log_message = response_body.decode("utf-8", errors="replace")
            except:
                log_message = "【附件下载】"
            # 保存日志
            log_entry = ApiLog(
                client_ip=client_ip,
                request_path=path,
                request_method=method,
                request_params=json.dumps(params) if params else None,
                request_body=body_str,
                response_status=response.status_code if response else 500,
                response_body=log_message if response else None,
                user_agent=user_agent,
                duration_ms=duration,
                error_message=error_message,
            )

            # 使用数据库会话保存日志
            try:
                with get_db() as db:
                    db.add(log_entry)
                    db.commit()
            except Exception as e:
                print(f"Error saving API log: {e}")
