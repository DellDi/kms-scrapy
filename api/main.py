import asyncio
import uvicorn
import logging
from logging.handlers import RotatingFileHandler
import os
import sys
import shutil
from datetime import datetime
from dotenv import load_dotenv

from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware

from contextlib import asynccontextmanager

from api.router.api_service import router as jira_router, TEMP_DIR
from api.router.api_kms_service import router as kms_router
from api.router.common import router as common_router
from api.router.dify_service import router as dify_router
from sqlmodel import Session, select

from api.database.models import Task, DifyTask
from api.middleware import APILoggingMiddleware, BearerTokenMiddleware
from api.database.db import get_db, init_db, engine

# 载入环境变量
load_dotenv()

# 从环境变量获取API根路径，默认为空字符串
API_ROOT_PATH = os.getenv("API_ROOT_PATH", "")
API_ROOT_PORT = os.getenv("API_ROOT_PORT", "8000")
API_ROOT_PORT = int(API_ROOT_PORT)

# 配置日志
log_dir = "logs-api"
if not os.path.exists(log_dir):
    os.makedirs(log_dir)

# 创建轮换文件处理器
file_handler = RotatingFileHandler(
    os.path.join(log_dir, "api.log"),
    maxBytes=10 * 1024 * 1024,  # 10MB
    backupCount=5,
    encoding="utf-8",
)
file_handler.setFormatter(
    logging.Formatter(
        "%(asctime)s - %(levelname)s - %(name)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
)

# 配置根日志记录器
logging.basicConfig(
    level=logging.DEBUG,
    handlers=[
        file_handler,  # 输出到轮换文件
    ],
)

# 使用uvicorn的日志记录器
logger = logging.getLogger("uvicorn")

# 自定义 uvicorn 日志格式
log_config = {
    "version": 1,
    "disable_existing_loggers": False,
    "formatters": {
        "default": {
            "()": "uvicorn.logging.DefaultFormatter",
            "fmt": "%(asctime)s - %(levelprefix)s %(message)s",
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "use_colors": True,
        },
        "access": {
            "()": "uvicorn.logging.AccessFormatter",
            "fmt": '%(asctime)s - %(levelprefix)s %(client_addr)s - "%(request_line)s" %(status_code)s',
            "datefmt": "%Y-%m-%d %H:%M:%S",
            "use_colors": True,
        },
    },
    "handlers": {
        "default": {
            "formatter": "default",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stderr",
        },
        "access": {
            "formatter": "access",
            "class": "logging.StreamHandler",
            "stream": "ext://sys.stdout",
        },
    },
    "loggers": {
        "uvicorn": {"handlers": ["default"], "level": "INFO", "propagate": False},
        "uvicorn.error": {"level": "INFO"},
        "uvicorn.access": {"handlers": ["access"], "level": "INFO", "propagate": False},
    },
}


async def periodic_cleanup():
    while True:
        try:
            # 创建新的数据库会话
            with Session(engine) as db:
                await cleanup_old_tasks(db=db)
                await cleanup_old_dify_tasks(db=db)
                logger.info("已完成定期清理任务")
        except Exception as e:
            logger.error(f"定期清理任务失败: {str(e)}")

        # 每7天执行一次
        await asyncio.sleep(86400 * 7)


async def cleanup_old_tasks(db: Session = Depends(get_db)) -> None:
    """清理超过24小时的任务数据."""
    cutoff_time = datetime.now().timestamp() - 86400 * 7  # 7天
    query = select(Task).where(Task.start_time < cutoff_time)
    old_tasks = db.exec(query).all()

    for task in old_tasks:
        task_dir = os.path.join(TEMP_DIR, str(task.id))
        if os.path.exists(task_dir):
            shutil.rmtree(task_dir)
        db.delete(task)

    db.commit()


async def cleanup_old_dify_tasks(db: Session = Depends(get_db)) -> None:
    """清理超过7天的Dify任务上传数据记录."""
    cutoff_time = datetime.now().timestamp() - 86400 * 7  # 7天
    query = select(DifyTask).where(DifyTask.start_time < cutoff_time)
    old_tasks = db.exec(query).all()

    for task in old_tasks:
        task_dir = task.input_dir
        if os.path.exists(task_dir) and os.path.isdir(task_dir):
            try:
                shutil.rmtree(task_dir)
                logger.info(f"Deleted old Dify task directory: {task_dir}")
            except Exception as e:
                logger.error(f"Failed to delete Dify task directory: {e}")
        db.delete(task)

    db.commit()


@asynccontextmanager
async def lifespan(app: FastAPI):
    # 启动时执行
    cleanup_task = asyncio.create_task(periodic_cleanup())
    logger.info("启动定期清理任务")

    yield

    # 关闭时执行
    cleanup_task.cancel()
    logger.info("应用关闭，清理资源")


# 初始化数据库
init_db()

# 定义全局安全方案
security_schemes = {
    "BearerAuth": {
        "type": "http",
        "scheme": "bearer",
        "bearerFormat": "JWT",
        "description": "请输入 API Token",
    }
}

app = FastAPI(
    title="爬虫API服务",
    description="""
    # 爬虫API服务文档

    该服务提供了一组API接口，用于管理和控制爬虫任务。

    ## 认证说明

    接口需要使用 Bearer Token 认证。请在请求头中添加：

    ```
    Authorization: Bearer YOUR_API_TOKEN
    ```

    ## 主要功能

    1. **爬虫任务管理**
       - 启动新的爬虫任务
       - 查询任务执行状态
       - 下载爬虫结果

    2. **知识库管理**
       - Dify知识库导入
       - 任务状态追踪
       - 文档处理

    3. **系统监控**
       - API请求日志查询
       - 任务执行状态跟踪
    """,
    lifespan=lifespan,
    version="1.0.0",
    docs_url="/api/docs",
    redoc_url="/api/redoc",
    openapi_url="/api/openapi.json",
    root_path=API_ROOT_PATH,  # 使用环境变量设置根路径
    openapi_tags=[
        {"name": "爬虫服务-Jira", "description": "Jira 爬虫相关接口"},
        {"name": "爬虫任务-kms", "description": "KMS 爬虫相关接口"},
        {"name": "知识库服务-Dify", "description": "Dify 知识库相关接口"},
        {"name": "系统监控", "description": "系统监控相关接口"},
    ],
    swagger_ui_parameters={"defaultModelsExpandDepth": -1},
    openapi_extra={"components": {"securitySchemes": security_schemes}},
    security=[{"BearerAuth": []}],
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
# 使用环境变量中的 API_TOKEN 值来初始化 Bearer Token 中间件
app.add_middleware(BearerTokenMiddleware, token_env_var="API_TOKEN")


@app.get("/", tags=["根路径"], include_in_schema=False)
def get_root():
    return {"message": "Welcome to the API"}


app.include_router(common_router)
app.include_router(jira_router)
app.include_router(kms_router)
app.include_router(dify_router)


# 链接加粗
base_url = f"http://localhost:{API_ROOT_PORT}{API_ROOT_PATH}"
link_doc = f"\033[1m{base_url}/api/docs\033[0m"
link_redoc = f"\033[1m{base_url}/api/redoc\033[0m"
logger.info(f"访问API文档: {link_doc}")
logger.info(f"访问API文档: {link_redoc}")

# 默认8000端口，支持外部端口号定义
if __name__ == "__main__":
    # 启动 uvicorn 服务器，使用自定义日志配置
    uvicorn.run(
        "api.main:app", host="0.0.0.0", port=API_ROOT_PORT, reload=True, log_config=log_config
    )
