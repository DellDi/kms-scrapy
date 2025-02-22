"""
百度热搜爬虫
~~~~~~~~~~~~

一个基于 Scrapy 和 Playwright 的现代爬虫，用于抓取百度热搜内容。

:copyright: (c) 2025 zengdi
:license: MIT
"""

__version__ = '0.1.0'
__author__ = 'zengdi'

from .spiders.baidu_spider import BaiduSpider
from .items import HotSearchItem, HotSearchData

__all__ = ['BaiduSpider', 'HotSearchItem', 'HotSearchData']