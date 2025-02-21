"""
Dify API 集成模块
用于管理文档到 Dify 平台的自动化上传和知识库管理
"""

from .api.client import DifyClient, DifyAPIError
from .core.knowledge_base import DatasetManager

__version__ = "0.1.0"

__all__ = [
    # API 客户端
    "DifyClient",
    "DifyAPIError",
    # 数据集管理
    "DatasetManager",
]
