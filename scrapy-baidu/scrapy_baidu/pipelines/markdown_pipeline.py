import os
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, Union
import logging
import json
from ..items import HotSearchItem, HotSearchData

# 配置模块日志记录器
logger = logging.getLogger(__name__)

class MarkdownPipeline:
    """Markdown 转换和存储管道"""

    def __init__(self, output_dir: Optional[str] = None):
        """初始化转换管道"""
        self.output_dir = Path(output_dir or 'output').absolute()
        self.current_date = None
        self.current_timestamp = None

        # 统计信息
        self.files_created = 0
        self.bytes_written = 0
        self.errors = 0

        # 缓存当前批次的数据用于生成汇总
        self.current_batch = []
        self.batch_size = 50

        # 初始化时创建基本目录
        self._ensure_base_dirs()
        logger.info("Markdown 转换管道初始化完成，输出目录: %s", self.output_dir)

    def _ensure_base_dirs(self):
        """确保基本目录结构存在"""
        try:
            # 创建输出根目录
            self.output_dir.mkdir(parents=True, exist_ok=True)

            # 创建元数据目录
            metadata_dir = self.output_dir / 'metadata'
            metadata_dir.mkdir(exist_ok=True)

            logger.debug("创建目录结构: %s", self.output_dir)
        except Exception as e:
            logger.error("创建目录失败: %s", str(e), exc_info=True)
            raise

    def _ensure_date_dirs(self):
        """确保日期相关的目录结构存在"""
        if not self.current_date or not self.current_timestamp:
            return

        try:
            # 创建日期目录
            self.date_dir = self.output_dir / self.current_date
            self.date_dir.mkdir(exist_ok=True)

            # 创建时间戳目录
            self.timestamp_dir = self.date_dir / self.current_timestamp
            self.timestamp_dir.mkdir(exist_ok=True)

            # 创建附件目录
            self.attachments_dir = self.timestamp_dir / 'attachments'
            self.attachments_dir.mkdir(exist_ok=True)

            logger.debug("创建日期目录: %s", self.timestamp_dir)
        except Exception as e:
            logger.error("创建日期目录失败: %s", str(e), exc_info=True)
            raise

    @classmethod
    def from_crawler(cls, crawler):
        """从爬虫创建管道实例"""
        output_dir = crawler.settings.get('MARKDOWN_OUTPUT_DIR', 'output')
        return cls(output_dir=output_dir)

    def process_item(self, item: Union[Dict[str, Any], HotSearchItem], spider) -> HotSearchItem:
        """处理数据项"""
        try:
            # 更新当前时间戳
            current_time = item.get('crawl_time', datetime.now())
            date_str = current_time.strftime('%Y-%m-%d')
            timestamp_str = current_time.strftime('%H-%M-%S')

            # 如果日期或时间戳变化，更新目录结构
            if date_str != self.current_date or timestamp_str != self.current_timestamp:
                self.current_date = date_str
                self.current_timestamp = timestamp_str
                self._ensure_date_dirs()

            # 生成文件名
            filename = self._generate_filename(item)
            logger.debug("处理数据项: %s -> %s", item.get('title'), filename)

            # 转换为Markdown并保存
            self._save_markdown(item, filename)

            # 添加到当前批次
            self.current_batch.append(item)

            # 如果达到批次大小，生成汇总
            if len(self.current_batch) >= self.batch_size:
                self._generate_summary()
                self.current_batch = []

            return item

        except Exception as e:
            self.errors += 1
            logger.error("Markdown转换失败: %s", str(e), exc_info=True)
            raise

    def _generate_filename(self, item: Dict[str, Any]) -> str:
        """生成文件名"""
        rank = item.get('rank', 0)
        title = item.get('title', '未知标题')

        # 清理标题，移除不合法的文件名字符
        safe_title = "".join(c for c in title if c.isalnum() or c in (' ', '-', '_')).strip()
        safe_title = safe_title[:50]  # 限制长度

        return f"{rank:02d}_{safe_title}.md"

    def _save_markdown(self, item: Dict[str, Any], filename: str):
        """保存为Markdown文件"""
        try:
            file_path = self.timestamp_dir / filename

            # 生成Markdown内容
            content = self._generate_markdown(item)

            # 保存文件
            with open(file_path, 'w', encoding='utf-8') as f:
                f.write(content)
                self.bytes_written += len(content.encode('utf-8'))
                self.files_created += 1

            logger.debug("保存文件: %s (大小: %d bytes)", file_path, len(content.encode('utf-8')))

        except Exception as e:
            logger.error("保存文件失败: %s -> %s", filename, str(e), exc_info=True)
            raise

    def _generate_markdown(self, item: Dict[str, Any]) -> str:
        """生成Markdown内容"""
        timestamp = item.get('crawl_time', datetime.now()).strftime('%Y-%m-%d %H:%M:%S')

        # Markdown模板
        template = f"""# {item.get('title', '未知标题')}

## 基本信息
- 排名：{item.get('rank', 'N/A')}
- 热度：{item.get('heat_score', 'N/A')}
- 时间：{timestamp}
- 分类：{item.get('category', '未分类')}
- 来源：百度热搜

## 标签
{', '.join(item.get('tags', [])) or '暂无标签'}

## 内容摘要
{item.get('summary', '暂无摘要')}

## 详细内容
{item.get('content', '暂无详细内容')}

## 相关链接
[查看原文]({item.get('url', '#')})

---
*数据来源：百度热搜*
*爬取时间：{timestamp}*
"""
        return template

    def _generate_summary(self):
        """生成汇总文件"""
        if not self.current_batch:
            return

        try:
            summary_path = self.date_dir / 'summary.md'
            mode = 'a' if summary_path.exists() else 'w'

            with open(summary_path, mode, encoding='utf-8') as f:
                if mode == 'w':
                    f.write(f"# {self.current_date} 百度热搜汇总\n\n")

                f.write(f"\n## {self.current_timestamp} 更新\n")

                # 按排名排序
                sorted_items = sorted(
                    self.current_batch,
                    key=lambda x: x.get('rank', 999)
                )

                # 写入每个热搜项的概要
                for item in sorted_items:
                    f.write(f"\n### {item.get('rank', '?')}. {item.get('title', '未知标题')}\n")
                    f.write(f"- 热度：{item.get('heat_score', 'N/A')}\n")
                    f.write(f"- 时间：{item.get('crawl_time', datetime.now()).strftime('%H:%M:%S')}\n")
                    f.write(f"- [详情]({self.current_timestamp}/{self._generate_filename(item)})\n")

            logger.debug("更新汇总文件: %s", summary_path)

        except Exception as e:
            logger.error("生成汇总文件失败: %s", str(e), exc_info=True)
            raise

    def close_spider(self, spider):
        """爬虫关闭时的处理"""
        logger.info("关闭 Markdown 转换管道")

        # 生成最后一批数据的汇总
        if self.current_batch:
            self._generate_summary()

        try:
            # 生成元数据文件
            metadata = {
                'last_update': datetime.now().isoformat(),
                'statistics': {
                    'files_created': self.files_created,
                    'bytes_written': self.bytes_written,
                    'errors': self.errors
                }
            }

            metadata_path = self.output_dir / 'metadata' / 'stats.json'
            with open(metadata_path, 'w', encoding='utf-8') as f:
                json.dump(metadata, f, ensure_ascii=False, indent=2)

            # 输出统计信息
            logger.info("Markdown转换管道统计:")
            logger.info("- 创建文件数: %d", self.files_created)
            logger.info("- 写入字节数: %d", self.bytes_written)
            logger.info("- 错误数: %d", self.errors)
            logger.info("- 元数据文件: %s", metadata_path)

        except Exception as e:
            logger.error("保存元数据失败: %s", str(e), exc_info=True)