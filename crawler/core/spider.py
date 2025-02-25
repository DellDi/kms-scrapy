import scrapy
from scrapy.http import Request, FormRequest
from bs4 import BeautifulSoup
from datetime import datetime

from .auth import AuthManager
from .config import config
from .content import ContentParser, KMSItem
from .exporter import DocumentExporter
from .optimizer import OptimizerFactory
from .tree_extractor import TreeExtractor


class ConfluenceSpider(scrapy.Spider):
    name = "confluence"
    custom_settings = {
        "DOWNLOAD_DELAY": config.spider.download_delay,
        "COOKIES_ENABLED": True,
        "CONCURRENT_REQUESTS": config.spider.concurrent_requests,
        "RETRY_TIMES": config.spider.retry_times,
        "RETRY_HTTP_CODES": config.spider.retry_http_codes,
        "DEFAULT_REQUEST_HEADERS": config.spider.default_headers,
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [kwargs.get("start_url", "http://kms.new-see.com:8090")]
        self.auth_manager = AuthManager({"meta": {"original_url": self.start_urls[0]}})
        self.content_parser = ContentParser(
            enable_text_extraction=False, content_optimizer=OptimizerFactory.create_optimizer()
        )
        self.baichuan_config = {
            "api_key": config.baichuan.api_key,
            "api_url": config.baichuan.api_url,
        }
        self.tree_extractor = TreeExtractor(self.auth_manager)  # 初始化树结构提取器

    def start_requests(self):
        for url in self.start_urls:
            yield self.auth_manager.create_authenticated_request(
                url,
                callback=self.parse,
                meta={"handle_httpstatus_list": [302, 200]},
            )

    def parse(self, response):
        # 处理内容页面
        self.logger.info(f"开始处理页面: {response}")

        # 解析页面内容
        soup = BeautifulSoup(response.text, "html.parser")
        title_element = soup.select_one("#title-text")
        main_content = soup.select_one("#main-content")

        # 检查页面是否已完全加载
        if not title_element or not main_content:
            retry_count = response.meta.get("retry_count", 0)
            max_retries = 3

            if retry_count < max_retries:
                self.logger.info(f"页面未完全加载，第{retry_count + 1}次重试")
                meta = response.meta.copy()
                meta["retry_count"] = retry_count + 1
                meta["download_delay"] = (retry_count + 1) * 2
                yield self.auth_manager.create_authenticated_request(
                    response.url, callback=self.parse, meta=meta
                )
            else:
                self.logger.warning(
                    f"页面 {response.url} 在{max_retries}次重试后仍未完全加载，跳过处理"
                )
            return

        # 尝试处理导航树
        tree_request = self.tree_extractor.process_tree_container(response, soup)
        if tree_request:
            # 设置回调以处理树结构内容
            tree_request.callback = self.tree_extractor.parse_tree_ajax
            # 设置内容解析回调
            self.tree_extractor.parse_content_callback = self.parse_content
            yield tree_request
            return

        # 如果没有导航树或无法处理，继续处理当前页面内容
        self.logger.info("继续处理页面内容")
        yield self.auth_manager.create_authenticated_request(
            url=response.url,
            callback=self.parse_content,
            meta={
                "handle_httpstatus_list": [302, 200],
            },
        )

    def optimize_content(self, content: str) -> str:
        optimizer = OptimizerFactory.create_optimizer()
        return optimizer.optimize(content)

    def parse_content(self, response):
        # 解析页面内容
        soup = BeautifulSoup(response.text, "html.parser")
        title_element = soup.select_one("#title-text")
        main_content = soup.select_one("#main-content")

        # 检查页面是否已完全加载
        retry_count = response.meta.get("retry_count", 0)
        max_retries = 3  # 最大重试次数
        # or not main_content.find_all()
        if not title_element or not main_content:
            if retry_count < max_retries:
                self.logger.info(f"页面内容未完全加载，第{retry_count + 1}次重试")
                meta = response.meta.copy()
                meta["retry_count"] = retry_count + 1
                delay = (retry_count + 1) * 3  # 每次重试增加3秒延迟
                meta["download_delay"] = delay
                yield self.auth_manager.create_authenticated_request(
                    response.url, callback=self.parse_content, meta=meta
                )
            else:
                self.logger.warning(
                    f"页面 {response.url} 在{max_retries}次重试后仍未完全加载，跳过处理"
                )
            return

        # 处理页面内容
        title = title_element.get_text(strip=True)
        content = soup.select_one("#main-content")

        # 处理附件
        attachments = []
        # 选择具有data-linked-resource-type='attachment'属性的元素
        for attachment in soup.select('#main-content [data-linked-resource-type="attachment"]'):
            # 根据元素类型获取附件链接
            if attachment.name == "img":
                file_url = response.urljoin(attachment.get("src", ""))
            else:  # a标签
                file_url = response.urljoin(attachment.get("href", ""))

            if file_url:  # 只处理有效的URL
                attachment_info = self.content_parser.process_attachment(
                    file_url, self._get_common_headers()
                )
                if attachment_info:
                    attachments.append(attachment_info)

        # 使用百川API优化内容
        optimized_content = self.optimize_content(content.get_text())

        # 创建KMSItem对象，包含深度信息
        depth_info = response.meta.get("depth_info", {})

        kms_item = KMSItem(
            title=title,
            content=optimized_content,
            attachments=attachments,
            depth_info=depth_info,  # 传递深度信息
        )

        # 使用DocumentExporter导出文档
        exporter = DocumentExporter()
        markdown_path, attachments_dir = exporter.export(kms_item)

        self.logger.info(f"已保存文档：{markdown_path}")
        self.logger.info(f"附件保存在：{attachments_dir}" if attachments else "无附件")
        # 先删除已经存在的confluence.json

        # 将关键信息yield给Scrapy数据管道
        yield {
            "title": title,
            "url": response.url,
            "markdown_path": markdown_path,
            "attachments_dir": attachments_dir if attachments else None,
            "attachments_count": len(attachments),
            "timestamp": datetime.now().isoformat(),
            "status": "success",
        }
