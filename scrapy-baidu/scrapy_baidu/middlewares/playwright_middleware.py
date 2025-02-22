import asyncio
from typing import Optional, Type, Dict, Any
from playwright.async_api import async_playwright, Browser, Page
from scrapy import Spider, signals
from scrapy.http import Request, Response, HtmlResponse
from scrapy.exceptions import NotConfigured
import logging
import nest_asyncio
from datetime import datetime
import sys
import os

# 允许在已有事件循环中嵌套新的事件循环
nest_asyncio.apply()

logger = logging.getLogger(__name__)

class PlaywrightMiddleware:
    """Playwright 中间件，处理动态页面渲染"""

    def __init__(self, settings):
        if not settings.getbool('PLAYWRIGHT_ENABLED', True):
            raise NotConfigured('Playwright is disabled')

        self.browser: Optional[Browser] = None
        self.playwright = None
        self.launch_options = settings.get('PLAYWRIGHT_LAUNCH_OPTIONS', {})
        self.context_args = settings.get('PLAYWRIGHT_CONTEXT_ARGS', {})
        self.max_pages = settings.getint('PLAYWRIGHT_MAX_PAGES', 8)
        self.install_if_missing = settings.getbool('PLAYWRIGHT_INSTALL_IF_MISSING', True)

        # 页面管理
        self._pages = set()
        self._page_semaphore = asyncio.Semaphore(self.max_pages)

        # 初始化事件循环
        try:
            self._loop = asyncio.get_event_loop()
        except RuntimeError:
            self._loop = asyncio.new_event_loop()
            asyncio.set_event_loop(self._loop)

        # 性能监控
        self._start_time = datetime.now()
        self._request_count = 0
        self._error_count = 0

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建中间件实例"""
        middleware = cls(crawler.settings)
        crawler.signals.connect(middleware.spider_opened, signal=signals.spider_opened)
        crawler.signals.connect(middleware.spider_closed, signal=signals.spider_closed)
        return middleware

    def spider_opened(self, spider: Spider):
        """爬虫启动时初始化浏览器"""
        logger.info("初始化 Playwright 浏览器")
        retry_count = 0
        max_retries = 3

        while retry_count < max_retries:
            try:
                # 确保在事件循环中运行
                if self._loop.is_running():
                    future = asyncio.run_coroutine_threadsafe(
                        self._init_browser(),
                        self._loop
                    )
                    future.result(timeout=30)  # 30秒超时
                else:
                    self._loop.run_until_complete(self._init_browser())

                logger.info("Playwright 浏览器初始化成功")
                return

            except Exception as e:
                retry_count += 1
                error_msg = str(e)

                # 检查是否是浏览器未安装错误
                if "Executable doesn't exist" in error_msg and self.install_if_missing:
                    logger.warning("Playwright 浏览器未安装，尝试安装...")
                    try:
                        result = os.system("playwright install chromium")
                        if result == 0:
                            logger.info("Playwright 浏览器安装成功")
                            continue
                        else:
                            logger.error("Playwright 浏览器安装失败")
                    except Exception as install_error:
                        logger.error(f"安装过程出错: {str(install_error)}")

                if retry_count < max_retries:
                    logger.warning(f"初始化失败 ({retry_count}/{max_retries}): {error_msg}")
                else:
                    logger.error(f"Playwright 浏览器初始化失败: {error_msg}", exc_info=True)
                    raise

    async def _init_browser(self):
        """初始化浏览器"""
        self.playwright = await async_playwright().start()
        self.browser = await self.playwright.chromium.launch(**self.launch_options)

    def spider_closed(self, spider: Spider):
        """爬虫关闭时清理资源"""
        logger.info("关闭 Playwright 浏览器")

        try:
            # 确保在事件循环中运行清理
            if self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._cleanup(),
                    self._loop
                )
                future.result(timeout=10)  # 10秒超时
            else:
                self._loop.run_until_complete(self._cleanup())
        except Exception as e:
            logger.error(f"关闭浏览器失败: {str(e)}", exc_info=True)
        finally:
            # 记录性能统计
            duration = (datetime.now() - self._start_time).total_seconds()
            logger.info(
                "Playwright 统计 - 请求数: %d, 错误数: %d, 运行时间: %.2f秒",
                self._request_count,
                self._error_count,
                duration
            )

    async def _cleanup(self):
        """清理资源"""
        # 关闭所有页面
        for page in self._pages.copy():
            try:
                await page.close()
            except Exception as e:
                logger.error(f"关闭页面失败: {str(e)}")

        # 关闭浏览器
        if self.browser:
            try:
                await self.browser.close()
            except Exception as e:
                logger.error(f"关闭浏览器失败: %s", str(e))

        # 停止 Playwright
        if self.playwright:
            try:
                await self.playwright.stop()
            except Exception as e:
                logger.error(f"停止 Playwright 失败: %s", str(e))

    async def _get_page(self) -> Page:
        """获取新的页面实例"""
        if not self.browser:
            raise RuntimeError("浏览器未初始化")

        async with self._page_semaphore:
            context = await self.browser.new_context(**self.context_args)
            page = await context.new_page()
            self._pages.add(page)
            return page

    def process_request(self, request: Request, spider: Spider) -> Optional[HtmlResponse]:
        """处理请求"""
        # 如果不需要 Playwright 处理，跳过
        if not request.meta.get('playwright', False):
            return None

        if not self.browser:
            logger.error("浏览器未初始化，跳过请求")
            return None

        self._request_count += 1

        try:
            # 确保在事件循环中运行
            if self._loop.is_running():
                future = asyncio.run_coroutine_threadsafe(
                    self._process_request_async(request),
                    self._loop
                )
                return future.result(timeout=30)  # 30秒超时
            else:
                return self._loop.run_until_complete(
                    self._process_request_async(request)
                )
        except Exception as e:
            self._error_count += 1
            logger.error(f"处理请求失败: {str(e)}", exc_info=True)
            return None

    async def _process_request_async(self, request: Request) -> Optional[HtmlResponse]:
        """异步处理请求"""
        page = await self._get_page()

        try:
            # 设置超时
            timeout = request.meta.get('playwright_timeout', 30000)

            # 导航到页面
            response = await page.goto(
                request.url,
                wait_until='networkidle',
                timeout=timeout
            )

            if not response:
                raise Exception("页面导航失败")

            # 处理特定页面的交互逻辑
            if request.meta.get('click_selector'):
                try:
                    await page.click(request.meta['click_selector'])
                    await page.wait_for_load_state('networkidle')
                except Exception as e:
                    logger.warning(f"点击交互失败: {str(e)}")

            # 获取页面内容
            content = await page.content()

            # 创建响应对象
            html_response = HtmlResponse(
                url=request.url,
                body=content.encode('utf-8'),
                encoding='utf-8',
                request=request
            )

            # 如果需要保留页面对象
            if request.meta.get('playwright_include_page', False):
                html_response.meta['playwright_page'] = page
            else:
                await self._release_page(page)

            return html_response

        except Exception as e:
            await self._release_page(page)
            raise

    async def _release_page(self, page: Page):
        """释放页面实例"""
        if page in self._pages:
            try:
                await page.close()
                self._pages.remove(page)
            except Exception as e:
                logger.error(f"释放页面失败: {str(e)}")

    def process_response(self, request: Request, response: Response, spider: Spider) -> Response:
        """处理响应"""
        try:
            if hasattr(response, 'meta') and 'playwright_page' in response.meta:
                self._loop.run_until_complete(
                    self._release_page(response.meta['playwright_page'])
                )
        except Exception as e:
            logger.error(f"处理响应失败: {str(e)}", exc_info=True)

        return response

    def process_exception(self, request: Request, exception: Exception, spider: Spider):
        """处理异常"""
        self._error_count += 1
        logger.error(f"请求异常: {str(exception)}", exc_info=True)

        try:
            if 'playwright_page' in request.meta:
                self._loop.run_until_complete(
                    self._release_page(request.meta['playwright_page'])
                )
        except Exception as e:
            logger.error(f"处理异常时清理资源失败: {str(e)}", exc_info=True)

        return None