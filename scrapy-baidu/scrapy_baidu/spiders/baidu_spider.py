import scrapy
from scrapy import Request
from typing import Generator, Dict, Any, Optional, List
from datetime import datetime
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin
import logging
import asyncio
import json

from ..items import HotSearchItem, HotSearchData

logger = logging.getLogger(__name__)

class BaiduSpider(scrapy.Spider):
    """百度热搜爬虫"""

    name = 'baidu'
    allowed_domains = ['baidu.com']
    start_urls = ['https://www.baidu.com/?tn=68018901_16_pg']

    custom_settings = {
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
            'timeout': 30000,
            'args': ['--no-sandbox', '--disable-dev-shm-usage']
        },
        'CONCURRENT_REQUESTS': 4,
        'DOWNLOAD_DELAY': 1,
        'PLAYWRIGHT_MAX_PAGES': 8
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.stats = {
            'items_scraped': 0,
            'details_scraped': 0,
            'validation_errors': 0,
            'parse_errors': 0,
            'request_errors': 0
        }
        logger.info("初始化百度热搜爬虫")

    def start_requests(self) -> Generator[Request, None, None]:
        """开始请求"""
        for url in self.start_urls:
            logger.info("开始抓取热搜列表: %s", url)
            yield Request(
                url=url,
                callback=self.parse_hot_search,
                errback=self.handle_error,
                meta={
                    'playwright': True,
                    'playwright_include_page': True,
                    'playwright_context_kwargs': {
                        'java_script_enabled': True,
                    },
                    'dont_retry': False,
                    'handle_httpstatus_list': [403, 404, 500],
                    'download_timeout': 30,
                },
                dont_filter=True,
                priority=100
            )

    def validate_item(self, data: Dict[str, Any]) -> Optional[HotSearchItem]:
        """验证并创建数据项"""
        try:
            # 使用 Pydantic 模型验证数据
            validated_data = HotSearchData(**data)
            return validated_data.to_item()
        except Exception as e:
            self.stats['validation_errors'] += 1
            logger.error(
                "数据验证失败: %s -> %s",
                data.get('title', '未知标题'),
                str(e),
                exc_info=True
            )
            return None

    async def _run_with_loop(self, coro):
        """在事件循环中执行协程"""
        try:
            loop = asyncio.get_event_loop()
            if not loop.is_running():
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)

            # 创建任务并等待完成
            task = loop.create_task(coro)
            return await task

        except Exception as e:
            logger.error(f"执行协程失败: {str(e)}")
            raise

    async def parse_hot_search(self, response):
        """解析热搜页面"""
        page = response.meta.get('playwright_page')
        if not page:
            logger.error("未获取到页面对象")
            return

        try:
            # 等待热搜内容加载，添加失败重试逻辑
            retry_count = 0
            max_retries = 3
            selector = '#hotsearch-content-wrapper'

            while retry_count < max_retries:
                try:
                    logger.debug(f"等待热搜内容加载... (尝试 {retry_count + 1}/{max_retries})")

                    # 等待选择器
                    await self._run_with_loop(
                        page.wait_for_selector(selector, timeout=10000)
                    )
                    break
                except Exception as e:
                    retry_count += 1
                    if retry_count < max_retries:
                        logger.warning(f"等待热搜加载失败，重试: {str(e)}")
                        # 重新加载页面
                        await self._run_with_loop(page.reload())
                    else:
                        raise Exception(f"热搜内容加载失败: {str(e)}")

            # 获取所有热搜项目
            hot_items = await self._run_with_loop(
                page.query_selector_all('.hotsearch-item'))
            total_items = len(hot_items)

            if not hot_items:
                raise Exception("未找到热搜项目")

            logger.info("找到 %d 个热搜项目", total_items)

            for rank, item in enumerate(hot_items, 1):
                try:
                    # 提取基本数据
                    title_elem = await item.query_selector('.title-content')
                    if not title_elem:
                        logger.warning("第 %d 项缺少标题元素，跳过", rank)
                        continue

                    # 确保元素可见
                    await self._run_with_loop(
                        title_elem.scroll_into_view_if_needed())

                    title = await self._run_with_loop(title_elem.text_content())
                    url = await self._run_with_loop(title_elem.get_attribute('href'))

                    if not url:
                        logger.warning("第 %d 项缺少URL，跳过: %s", rank, title)
                        continue

                    url = urljoin(response.url, url)
                    # 提取热度
                    heat_elem = await item.query_selector('.heat-score')
                    heat_score = await heat_elem.text_content() if heat_elem else '0'
                    heat_score = int(''.join(filter(str.isdigit, heat_score)))

                    # 提取标签（可选）
                    tag_elems = await item.query_selector_all('.tag')
                    tags = []
                    for tag_elem in tag_elems:
                        tag_text = await tag_elem.text_content()
                        if tag_text:
                            tags.append(tag_text.strip())

                    # 创建数据项
                    hot_search_data = {
                        'title': title.strip(),
                        'rank': rank,
                        'heat_score': heat_score,
                        'url': url,
                        'crawl_time': datetime.now(),
                        'source': 'baidu',
                        'tags': tags,
                        'state': 'pending'
                    }

                    # 验证数据
                    item = self.validate_item(hot_search_data)
                    if not item:
                        continue

                    self.stats['items_scraped'] += 1
                    logger.debug(
                        "提取热搜项 #%d: %s (热度: %d)",
                        rank, title, heat_score
                    )

                    # 请求详情页
                    yield Request(
                        url=url,
                        callback=self.parse_detail,
                        errback=self.handle_error,
                        meta={
                            'playwright': True,
                            'playwright_include_page': True,
                            'playwright_context_kwargs': {
                                'java_script_enabled': True,
                            },
                            'item': item,
                            'dont_retry': False,
                            'handle_httpstatus_list': [403, 404, 500],
                            'download_timeout': 30,
                            'priority': rank
                        }
                    )

                except Exception as e:
                    self.stats['parse_errors'] += 1
                    logger.error(
                        "处理热搜项 #%d 失败: %s",
                        rank, str(e),
                        exc_info=True
                    )
                    continue

        except Exception as e:
            self.stats['parse_errors'] += 1
            logger.error(
                "解析热搜页面失败: %s",
                str(e),
                exc_info=True
            )

        finally:
            if page:
                try:
                    future = asyncio.get_event_loop().create_task(page.close())
                    await future
                except Exception as e:
                    logger.error(f"关闭页面失败: {str(e)}")
                logger.debug("关闭热搜页面")

    async def parse_detail(self, response):
        """解析详情页面"""
        page = response.meta.get('playwright_page')
        item = response.meta.get('item')

        if not page or not item:
            logger.error("未获取到页面对象或数据项")
            yield item
            return

        try:
            # 等待页面加载
            logger.debug("等待详情页面加载: %s", response.url)
            await page.wait_for_load_state('networkidle', timeout=10000)

            # 等待主要内容加载
            content_selectors = [
                'article',
                '.content-wrapper',
                '.article-content',
                'main',
                '#content'
            ]

            main_content = None
            for selector in content_selectors:
                try:
                    element = await page.wait_for_selector(selector, timeout=5000)
                    if element:
                        main_content = element
                        break
                except:
                    continue

            if main_content:
                # 获取文本内容
                text_content = await main_content.text_content()
                text_content = text_content.strip()

                # 生成摘要
                summary = text_content[:200] + ('...' if len(text_content) > 200 else '')

                # 更新数据
                item['content'] = text_content
                item['summary'] = summary
                item['state'] = 'completed'

                self.stats['details_scraped'] += 1
                logger.debug(
                    "成功解析详情页面: %s (内容长度: %d)",
                    item['title'],
                    len(text_content)
                )

            else:
                item['state'] = 'no_content'
                item['error'] = '未找到主要内容'
                logger.warning("页面 %s 未找到主要内容", response.url)

        except Exception as e:
            self.stats['parse_errors'] += 1
            logger.error(
                "解析详情页面失败: %s -> %s",
                response.url,
                str(e),
                exc_info=True
            )
            item['state'] = 'failed'
            item['error'] = str(e)

        finally:
            if page:
                try:
                    future = asyncio.get_event_loop().create_task(page.close())
                    await future
                except Exception as e:
                    logger.error(f"关闭页面失败: {str(e)}")
                logger.debug("关闭详情页面: %s", response.url)
            yield item

    async def handle_error(self, failure):
        """处理错误"""
        self.stats['request_errors'] += 1

        if failure.request.meta.get('item'):
            item = failure.request.meta['item']
            item['state'] = 'failed'
            item['error'] = str(failure.value)
            logger.error(
                "请求失败: %s -> %s",
                item['url'],
                str(failure.value),
                exc_info=failure.value
            )
            yield item
        else:
            logger.error(
                "请求失败: %s -> %s",
                failure.request.url,
                str(failure.value),
                exc_info=failure.value
            )

    def closed(self, reason):
        """爬虫关闭时的处理"""
        # 保存统计信息到文件
        try:
            stats_path = Path(self.settings.get('OUTPUT_DIR')) / 'spider_stats.json'
            stats_data = {
                'finish_time': datetime.now().isoformat(),
                'finish_reason': reason,
                'stats': self.stats
            }
            with open(stats_path, 'w', encoding='utf-8') as f:
                json.dump(stats_data, f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.error("保存统计信息失败: %s", str(e))

        # 输出统计信息
        logger.info("爬虫统计:")
        logger.info("- 抓取热搜数: %d", self.stats['items_scraped'])
        logger.info("- 解析详情数: %d", self.stats['details_scraped'])
        logger.info("- 验证错误数: %d", self.stats['validation_errors'])
        logger.info("- 解析错误数: %d", self.stats['parse_errors'])
        logger.info("- 请求错误数: %d", self.stats['request_errors'])
        logger.info("爬虫结束，原因: %s", reason)
