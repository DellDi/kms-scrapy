"""
Dify 知识库导入工具配置
"""

import os

# API 配置
API_KEY = os.getenv("DIFY_API_KEY", "your-api-key")
BASE_URL = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")

# 数据集配置
DATASET_NAME_PREFIX = "大品控父子检索知识库"  # 数据集名称前缀
DATASET_NAME_PATTERN = rf"{DATASET_NAME_PREFIX}-(\d+)"  # 数据集名称匹配模式
MAX_DOCS_PER_DATASET = 12000  # 每个数据集的最大文档数量

# 文件和目录配置
DEFAULT_INPUT_DIR = "output-jira"  # 默认从output目录读取文件

# 嵌入模型提供商字典 - 高质量 - 嵌入模型和重排序模型
EMBEDDING_PROVIDER_DICT = {
    "reranking_model": {
        "reranking_provider_name": "siliconflow",  # siliconflow tongyi
        "reranking_model_name": "BAAI/bge-reranker-v2-m3",  # BAAI/bge-reranker-v2-m3 gte-rerank
    },
    "embedding_model_provider": "siliconflow",  # siliconflow tongyi
    "embedding_model": "BAAI/bge-large-zh-v1.5",  # BAAI/bge-large-zh-v1.5 text-embedding-v3
}

# 嵌入规则-高质量默认
EMBEDDING_DEFAULT_PROCESS_RULE = {
    "rules": {
        "pre_processing_rules": [
            {"id": "remove_extra_spaces", "enabled": True},
            {"id": "remove_urls_emails", "enabled": False},
        ],
        "segmentation": {"separator": "\n\n", "max_tokens": 500, "chunk_overlap": 50},
    },
    "mode": "custom",
}

# 嵌入规则父子检索 - 高质量（模型全文档）
EMBEDDING_PROCESS_PARENT_RULE = {
    "mode": "hierarchical",
    "rules": {
        "pre_processing_rules": [
            {"id": "remove_extra_spaces", "enabled": True},
            {"id": "remove_urls_emails", "enabled": False},
        ],
        "segmentation": {"separator": "\n\n", "max_tokens": 500},
        "parent_mode": "full-doc",  # full-doc, paragraph
        "subchunk_segmentation": {"separator": "\n", "max_tokens": 200},
    },
}


# 支持的文件类型  TXT、 MARKDOWN、 MDX、 PDF、 HTML、 XLSX、 XLS、 DOCX、 CSV、 MD、 HTM，每个文件不超过 15MB
SUPPORTED_FILE_EXTENSIONS = [
    ".txt",
    ".md",
    ".markdown",
    ".mdx",
    ".pdf",
    ".html",
    ".xlsx",
    ".docx",
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
