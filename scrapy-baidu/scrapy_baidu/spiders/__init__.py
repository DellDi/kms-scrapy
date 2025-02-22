"""
Scrapy spiders package

This package contains spider implementations for the Scrapy-Baidu project:
- BaiduSpider: Main spider for crawling Baidu hot search content,
              using Playwright for dynamic content handling
"""

from .baidu_spider import BaiduSpider

__all__ = ['BaiduSpider']