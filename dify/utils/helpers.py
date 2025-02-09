"""
辅助工具函数
提供配置加载、文件处理和错误处理等通用功能
"""
import os
from typing import Dict, Optional
from pathlib import Path
import json
import yaml

def load_config(config_path: str) -> Dict:
    """
    加载配置文件
    支持 JSON 和 YAML 格式

    Args:
        config_path: 配置文件路径

    Returns:
        Dict: 配置数据
    """
    config_file = Path(config_path)

    if not config_file.exists():
        raise FileNotFoundError(f"配置文件不存在: {config_path}")

    try:
        if config_file.suffix in ['.json']:
            with open(config_path, 'r', encoding='utf-8') as f:
                return json.load(f)
        elif config_file.suffix in ['.yml', '.yaml']:
            with open(config_path, 'r', encoding='utf-8') as f:
                return yaml.safe_load(f)
        else:
            raise ValueError(f"不支持的配置文件格式: {config_file.suffix}")
    except Exception as e:
        raise RuntimeError(f"加载配置文件失败: {str(e)}")

def validate_config(config: Dict) -> bool:
    """
    验证配置是否有效

    Args:
        config: 配置数据

    Returns:
        bool: 是否有效
    """
    required_fields = ['api_key', 'api_base_url']

    for field in required_fields:
        if field not in config:
            raise ValueError(f"缺少必需的配置项: {field}")

    return True

def get_env_config() -> Dict:
    """
    从环境变量获取配置

    Returns:
        Dict: 配置数据
    """
    config = {
        'api_key': os.getenv('DIFY_API_KEY'),
        'api_base_url': os.getenv('DIFY_BASE_URL', 'https://api.dify.ai/v1'),
        'max_docs_per_kb': int(os.getenv('DIFY_MAX_DOCS_PER_KB', '100')),
        'retry_attempts': int(os.getenv('DIFY_RETRY_ATTEMPTS', '3')),
        'retry_delay': int(os.getenv('DIFY_RETRY_DELAY', '1'))
    }

    if not config['api_key']:
        raise ValueError("未设置必需的环境变量: DIFY_API_KEY")

    return config

def format_file_size(size_in_bytes: int) -> str:
    """
    格式化文件大小

    Args:
        size_in_bytes: 文件大小(字节)

    Returns:
        str: 格式化后的大小
    """
    for unit in ['B', 'KB', 'MB', 'GB']:
        if size_in_bytes < 1024:
            return f"{size_in_bytes:.2f} {unit}"
        size_in_bytes /= 1024
    return f"{size_in_bytes:.2f} TB"

def get_relative_path(base_path: str, full_path: str) -> str:
    """
    获取相对路径

    Args:
        base_path: 基础路径
        full_path: 完整路径

    Returns:
        str: 相对路径
    """
    try:
        return str(Path(full_path).relative_to(base_path))
    except ValueError:
        return full_path

def ensure_directory(directory: str) -> None:
    """
    确保目录存在，不存在则创建

    Args:
        directory: 目录路径
    """
    Path(directory).mkdir(parents=True, exist_ok=True)

def safe_filename(filename: str) -> str:
    """
    生成安全的文件名
    移除或替换不安全的字符

    Args:
        filename: 原始文件名

    Returns:
        str: 安全的文件名
    """
    # 替换不安全的字符
    unsafe_chars = '<>:"/\\|?*'
    filename = ''.join(c if c not in unsafe_chars else '_' for c in filename)

    # 确保文件名不以点或空格开始或结束
    filename = filename.strip('. ')

    # 如果文件名为空，使用默认名称
    if not filename:
        filename = 'unnamed_file'

    return filename

def get_mime_type(file_path: str) -> Optional[str]:
    """
    获取文件的 MIME 类型

    Args:
        file_path: 文件路径

    Returns:
        Optional[str]: MIME 类型
    """
    import mimetypes

    mime_type, _ = mimetypes.guess_type(file_path)
    return mime_type

def create_error_message(error: Exception, context: Optional[str] = None) -> str:
    """
    创建格式化的错误消息

    Args:
        error: 异常对象
        context: 错误上下文

    Returns:
        str: 格式化的错误消息
    """
    message = f"错误: {str(error)}"
    if context:
        message = f"{context}: {message}"

    if hasattr(error, '__cause__') and error.__cause__:
        message += f"\n原因: {str(error.__cause__)}"

    return message