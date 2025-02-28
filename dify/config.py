"""
Dify 知识库导入工具配置
"""

import os

# API 配置
API_KEY = os.getenv("DIFY_API_KEY", "your-api-key")
BASE_URL = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")

# 文件和目录配置
DEFAULT_INPUT_DIR = "output-jira"  # 默认从output目录读取文件

# 嵌入模型提供商字典
EMBEDDING_PROVIDER_DICT = {
    "reranking_model": {
        "reranking_provider_name": "siliconflow",  # siliconflow tongyi
        "reranking_model_name": "BAAI/bge-reranker-v2-m3",  # BAAI/bge-reranker-v2-m3 gte-rerank
    },
    "embedding_model_provider": "siliconflow",  # siliconflow tongyi
    "embedding_model": "BAAI/bge-large-zh-v1.5",  # BAAI/bge-large-zh-v1.5 text-embedding-v3
}

# 数据集配置
DATASET_NAME_PREFIX = "大品控标准知识库"  # 数据集名称前缀
DATASET_NAME_PATTERN = rf"{DATASET_NAME_PREFIX}-(\d+)"  # 数据集名称匹配模式
MAX_DOCS_PER_DATASET = 2500  # 每个数据集的最大文档数量

# 支持的文件类型  TXT、 MARKDOWN、 MDX、 PDF、 HTML、 XLSX、 XLS、 DOCX、 CSV、 MD、 HTM，每个文件不超过 15MB
SUPPORTED_FILE_EXTENSIONS = [
    ".txt",
    ".md",
    ".markdown",
    ".mdx",
    ".pdf",
    ".html",
    ".xlsx",
    ".xls",
    ".docx",
    ".csv",
    ".md",
    ".htm",
]

# 特殊类型的附件大小进行限制,枚举
AttachmentSizeLimit = {
    "pdf": 5 * 1024 * 1024,
    "docx": 5 * 1024 * 1024,
    "xlsx": 20 * 1024,
    "csv": 15 * 1024,
    "txt": 15 * 1024,
}
