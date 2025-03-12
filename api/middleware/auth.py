"""Bearer Token 认证中间件.

该中间件用于验证请求头中的 Bearer Token，并在需要时拒绝未授权的请求。
支持配置白名单路径，这些路径不需要进行 Token 验证。
"""

import os
from typing import Callable, List, Optional

from fastapi import Request, Response
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.status import HTTP_401_UNAUTHORIZED


class BearerTokenMiddleware(BaseHTTPMiddleware):
    """Bearer Token 认证中间件."""

    def __init__(
        self,
        app,
        token: Optional[str] = None,
        whitelist_paths: Optional[List[str]] = None,
        token_env_var: str = "API_TOKEN",
    ):
        """初始化 Bearer Token 中间件.

        Args:
            app: FastAPI 应用实例
            token: 可选的静态 token 值，如果不提供则从环境变量获取
            whitelist_paths: 不需要验证 token 的路径列表
            token_env_var: 存储 token 的环境变量名称
        """
        super().__init__(app)
        self.token = token or os.getenv(token_env_var, "")
        # 默认白名单路径，只包含必要的根路径和API文档路径
        self.whitelist_paths = whitelist_paths or [
            "/api/docs",  # Swagger UI
            "/api/redoc",  # ReDoc UI
            "/api/openapi.json",  # OpenAPI 规范
            "/api/common",
            "/api/jira/callback",
            "/api/kms/callback",
        ]

    async def dispatch(self, request: Request, call_next: Callable) -> Response:
        """处理请求并验证 Bearer Token.

        如果请求路径在白名单中，或者请求头中包含有效的 Bearer Token，
        则允许请求继续处理；否则返回 401 未授权错误。
        """
        # 检查路径是否在白名单中
        path = request.url.path

        # 精确匹配根路径
        if path == "/":
            return await call_next(request)

        # 对于其他路径，使用更精确的匹配规则
        for wp in self.whitelist_paths:
            # 精确匹配完整路径
            if path == wp:
                return await call_next(request)

            # 对于 API 文档路径，允许子路径访问
            if path.startswith(wp):
                return await call_next(request)

        # 获取并验证 Authorization 头
        auth_header = request.headers.get("Authorization")
        if not auth_header:
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"detail": "缺少认证令牌"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # 验证 token 格式和值
        parts = auth_header.split()
        if len(parts) != 2 or parts[0].lower() != "bearer":
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"detail": "认证令牌格式无效"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        if parts[1] != self.token:
            return JSONResponse(
                status_code=HTTP_401_UNAUTHORIZED,
                content={"detail": "认证令牌无效"},
                headers={"WWW-Authenticate": "Bearer"},
            )

        # Token 验证通过，继续处理请求
        return await call_next(request)
