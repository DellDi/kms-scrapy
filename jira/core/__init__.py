"""
Jira爬虫核心模块

提供Jira系统数据爬取、处理和导出功能。
"""

from .auth import AuthManager, AuthError
from .config import config
from .spider import JiraSpider, JiraIssue
from .exporter import DocumentExporter, ExportError

__all__ = [
    'AuthManager',
    'AuthError',
    'config',
    'JiraSpider',
    'JiraIssue',
    'DocumentExporter',
    'ExportError',
]