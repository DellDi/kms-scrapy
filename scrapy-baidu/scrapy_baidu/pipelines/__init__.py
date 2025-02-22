"""
Scrapy pipelines package

This package contains data processing pipelines for the Scrapy-Baidu project:
- ContentCleaningPipeline: Handles content cleaning and normalization
- MarkdownPipeline: Converts and saves data in Markdown format
"""

from .content_pipeline import ContentCleaningPipeline
from .markdown_pipeline import MarkdownPipeline

__all__ = ['ContentCleaningPipeline', 'MarkdownPipeline']