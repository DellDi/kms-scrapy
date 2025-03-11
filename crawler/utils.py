"""
通用工具函数模块，提供跨平台兼容性支持
"""

import os
import sys
import platform
import ctypes
import logging
from typing import Optional, Any, Callable

# 设置日志记录器
logger = logging.getLogger(__name__)

# ===== 文件类型检测相关函数 =====

def setup_magic_module():
    """
    智能设置和加载magic模块，处理跨平台兼容性
    
    Returns:
        导入的magic模块或模拟的magic对象
    """
    # 根据操作系统优化magic导入
    is_windows = platform.system() == 'Windows'
    
    # 在Windows下尝试特殊处理，其他系统直接导入
    if is_windows:
        try:
            import magic
            return magic
        except ImportError:
            # 如果导入失败，尝试使用替代方案
            try:
                # 尝试查找python-magic-bin安装的DLL位置
                venv_path = os.path.dirname(sys.executable)
                dll_paths = [
                    os.path.join(venv_path, 'Lib', 'site-packages', 'magic'),
                    os.path.join(venv_path, 'Lib', 'site-packages', 'magic', 'libmagic'),
                    os.path.join(venv_path, 'Lib', 'site-packages', 'magic', 'magic1.dll'),
                ]
                
                # 尝试加载DLL
                for path in dll_paths:
                    if os.path.isdir(path):
                        os.environ['PATH'] = path + os.pathsep + os.environ['PATH']
                    elif os.path.isfile(path) and path.endswith('.dll'):
                        try:
                            ctypes.cdll.LoadLibrary(path)
                            break
                        except Exception as e:
                            logger.debug(f"加载DLL失败: {path}, 错误: {str(e)}")
                
                # 重新尝试导入magic
                import magic
                return magic
            except ImportError:
                # 如果仍然失败，创建一个模拟的magic对象
                logger.warning("无法导入magic库，将使用模拟的magic对象")
                
                class MockMagic:
                    @staticmethod
                    def from_buffer(buffer, mime=False):
                        # 使用mimetypes模块作为备选方案
                        return "application/octet-stream"
                
                return MockMagic()
    else:
        # 非Windows系统（Mac/Linux）直接导入
        try:
            import magic
            return magic
        except ImportError:
            logger.error("在非Windows系统上无法导入magic库，请安装libmagic")
            raise

def detect_file_type(file_content: bytes, file_name: str = "", headers: dict = None) -> str:
    """
    智能检测文件类型，跨平台兼容
    
    Args:
        file_content: 文件内容（字节）
        file_name: 文件名（可选）
        headers: HTTP头信息（可选，用于获取Content-Type）
        
    Returns:
        文件MIME类型
    """
    import mimetypes
    
    # 尝试使用magic库
    try:
        magic_module = setup_magic_module()
        if hasattr(magic_module, 'from_buffer') and callable(magic_module.from_buffer):
            return magic_module.from_buffer(file_content, mime=True)
    except Exception as e:
        logger.warning(f"使用magic检测文件类型失败: {str(e)}")
    
    # 备选方案：使用HTTP头信息
    if headers:
        content_type = headers.get("Content-Type", "")
        if content_type and content_type != "application/octet-stream":
            return content_type
    
    # 备选方案：使用文件扩展名
    if file_name:
        file_type, _ = mimetypes.guess_type(file_name)
        if file_type:
            return file_type
    
    # 默认返回
    return "application/octet-stream"

# ===== 路径处理相关函数 =====

def ensure_long_path_support(path: str) -> str:
    """
    确保路径支持长路径（超过260个字符）
    在Windows系统中，通过添加\\?\前缀支持长路径
    在Mac/Linux系统中，不需要特殊处理
    
    Args:
        path: 原始路径
        
    Returns:
        处理后的路径
    """
    # 只在Windows系统下添加前缀
    if platform.system() == 'Windows' and not path.startswith('\\\\?\\'):
        # 转换为绝对路径并添加前缀
        abs_path = os.path.abspath(path)
        return f'\\\\?\\{abs_path}'
    return path

def safe_makedirs(path: str, exist_ok: bool = False) -> None:
    """
    安全地创建目录，处理长路径问题
    
    Args:
        path: 目录路径
        exist_ok: 如果为True，则目录已存在不会报错
    """
    # 在Windows系统下使用长路径支持
    if platform.system() == 'Windows':
        long_path = ensure_long_path_support(path)
        os.makedirs(long_path, exist_ok=exist_ok)
    else:
        # 在Mac/Linux系统下直接使用原始路径
        os.makedirs(path, exist_ok=exist_ok)
    
def safe_open(path: str, mode: str = 'r', *args, **kwargs):
    """
    安全地打开文件，处理长路径问题
    
    Args:
        path: 文件路径
        mode: 打开模式
        args, kwargs: 传递给open()的其他参数
    
    Returns:
        文件对象
    """
    # 在Windows系统下使用长路径支持
    if platform.system() == 'Windows':
        long_path = ensure_long_path_support(path)
        return open(long_path, mode, *args, **kwargs)
    else:
        # 在Mac/Linux系统下直接使用原始路径
        return open(path, mode, *args, **kwargs)
