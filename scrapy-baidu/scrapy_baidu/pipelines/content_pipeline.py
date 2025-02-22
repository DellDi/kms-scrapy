import re
import html
import logging
from bs4 import BeautifulSoup
from typing import Dict, Any, Optional
from datetime import datetime
from scrapy import Spider
from pydantic import ValidationError

from ..items import HotSearchItem, HotSearchData

# 配置模块日志记录器
logger = logging.getLogger(__name__)

class ContentCleaningPipeline:
    """内容清洗管道"""

    def __init__(self):
        """初始化清洗管道"""
        # 清洗配置
        self.strip_html = True
        self.normalize_whitespace = True
        self.max_content_length = 10000
        self.max_title_length = 100

        # 统计信息
        self.items_processed = 0
        self.items_dropped = 0
        self.validation_errors = 0

        # HTML标签白名单
        self.allowed_tags = {
            'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'a', 'strong', 'em', 'blockquote'
        }

        logger.info("内容清洗管道初始化完成")
        logger.debug("允许的HTML标签: %s", self.allowed_tags)

    def process_item(self, item: Dict[str, Any], spider: Spider) -> HotSearchItem:
        """处理数据项"""
        try:
            # 清理和规范化数据
            logger.debug("开始处理数据项: %s", item.get('title', '未知标题'))
            cleaned_data = self._clean_item(item)

            # 验证数据
            logger.debug("验证数据...")
            validated_data = HotSearchData(**cleaned_data)

            # 转换回 Scrapy Item
            result_item = HotSearchItem(**validated_data.dict())

            # 更新统计
            self.items_processed += 1
            logger.debug("数据项处理完成")

            return result_item

        except ValidationError as e:
            self.validation_errors += 1
            logger.error("数据验证失败: %s", str(e))
            raise

        except Exception as e:
            self.items_dropped += 1
            logger.error("内容清洗失败: %s", str(e))
            raise

    def _clean_item(self, item: Dict[str, Any]) -> Dict[str, Any]:
        """清理数据项"""
        cleaned = item.copy()

        # 清理标题
        if 'title' in cleaned:
            cleaned['title'] = self._clean_text(
                cleaned['title'],
                max_length=self.max_title_length
            )
            logger.debug("清理标题: %s", cleaned['title'])

        # 清理内容
        if 'content' in cleaned:
            cleaned['content'] = self._clean_html(
                cleaned['content'],
                max_length=self.max_content_length
            )
            logger.debug("清理内容长度: %d", len(cleaned['content']))

        # 清理摘要
        if 'summary' in cleaned:
            cleaned['summary'] = self._clean_text(
                cleaned['summary'],
                max_length=200
            )

        # 规范化标签列表
        if 'tags' in cleaned:
            cleaned['tags'] = self._clean_tags(cleaned['tags'])
            logger.debug("处理标签: %s", cleaned['tags'])

        # 确保必要的时间字段
        if 'crawl_time' not in cleaned:
            cleaned['crawl_time'] = datetime.now()

        # 处理热度值
        if 'heat_score' in cleaned:
            cleaned['heat_score'] = self._normalize_heat_score(cleaned['heat_score'])

        # 处理URL
        if 'url' in cleaned:
            cleaned['url'] = self._normalize_url(cleaned['url'])

        # 设置默认状态
        if 'state' not in cleaned:
            cleaned['state'] = 'processed'

        return cleaned

    def _clean_text(self, text: Optional[str], max_length: int = None) -> str:
        """清理文本内容"""
        if not text:
            return ""

        # 解码HTML实体
        text = html.unescape(text)

        # 规范化空白字符
        if self.normalize_whitespace:
            text = re.sub(r'\s+', ' ', text)

        # 去除首尾空白
        text = text.strip()

        # 截断过长的文本
        if max_length and len(text) > max_length:
            text = text[:max_length] + '...'

        return text

    def _clean_html(self, content: Optional[str], max_length: int = None) -> str:
        """清理HTML内容"""
        if not content:
            return ""

        # 使用BeautifulSoup清理HTML
        soup = BeautifulSoup(content, 'html.parser')

        # 只保留允许的标签
        if self.strip_html:
            for tag in soup.find_all():
                if tag.name not in self.allowed_tags:
                    tag.unwrap()

        # 获取文本内容
        text = soup.get_text(separator='\n', strip=True)

        # 规范化空白字符
        if self.normalize_whitespace:
            text = re.sub(r'\n\s*\n', '\n\n', text)
            text = re.sub(r' +', ' ', text)

        # 截断过长的内容
        if max_length and len(text) > max_length:
            text = text[:max_length] + '...'

        return text.strip()

    def _clean_tags(self, tags: Any) -> list:
        """清理标签列表"""
        if not tags:
            return []

        if isinstance(tags, str):
            tags = [tags]

        # 确保是列表类型
        tags = list(tags)

        # 清理每个标签
        cleaned_tags = []
        for tag in tags:
            if tag:
                cleaned_tag = self._clean_text(str(tag))
                if cleaned_tag:
                    cleaned_tags.append(cleaned_tag)

        # 去重
        cleaned_tags = list(dict.fromkeys(cleaned_tags))

        return cleaned_tags

    def _normalize_heat_score(self, score: Any) -> int:
        """规范化热度值"""
        try:
            if isinstance(score, str):
                # 提取数字
                score = re.sub(r'[^\d]', '', score)
            return int(score)
        except (ValueError, TypeError):
            return 0

    def _normalize_url(self, url: Optional[str]) -> str:
        """规范化URL"""
        if not url:
            return ""

        # 去除空白字符
        url = url.strip()

        # 确保有协议前缀
        if not url.startswith(('http://', 'https://')):
            url = 'https://' + url

        return url

    def close_spider(self, spider: Spider):
        """爬虫关闭时的处理"""
        logger.info("内容清洗管道统计:")
        logger.info("- 处理项目数: %d", self.items_processed)
        logger.info("- 丢弃项目数: %d", self.items_dropped)
        logger.info("- 验证错误数: %d", self.validation_errors)