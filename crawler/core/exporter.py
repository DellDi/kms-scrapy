import os
import re
import logging
from typing import Optional, List, Dict, Any
from .content import KMSItem
from crawler.core.config import config
from crawler.utils import safe_makedirs, safe_open


class DocumentExporter:
    """文档导出器，负责将KMSItem对象导出为Markdown文件"""

    def __init__(self, base_dir: str = None):
        self.output_dir = config.spider.output_dir
        self.base_dir = base_dir or os.getcwd()
        self.markdown_dir = os.path.join(self.base_dir, self.output_dir, "markdown")
        self.attachments_dir = os.path.join(self.base_dir, self.output_dir, "attachments")
        self.logger = logging.getLogger(__name__)

    def _create_dirs(
        self, safe_title: str, attachments: Optional[List[dict]] = [], depth_info: dict = None
    ) -> tuple[str, str]:
        """创建必要的目录结构"""
        if depth_info:
            # 直接使用传入的输出路径
            output_path = depth_info.get("output_path")
            parent_path = depth_info.get("_parent_path", "")
            current_depth = depth_info.get("current_depth", 0)

            self.logger.info(f"创建目录 - 深度: {current_depth}")
            self.logger.info(f"父路径: {parent_path}")
            self.logger.info(f"当前输出路径: {output_path}")
            self.logger.info(f"完整深度信息: {depth_info}")

            if output_path:
                doc_markdown_dir = os.path.join(self.markdown_dir, output_path)
                self.logger.info(f"使用输出路径创建目录: {doc_markdown_dir}")
            else:
                # 如果没有提供输出路径，使用安全的标题
                doc_markdown_dir = os.path.join(self.markdown_dir, safe_title)
                self.logger.info(f"使用安全标题创建目录: {doc_markdown_dir}")
            safe_makedirs(doc_markdown_dir, exist_ok=True)
        else:
            doc_markdown_dir = os.path.join(self.markdown_dir, safe_title)
            safe_makedirs(doc_markdown_dir, exist_ok=True)

        # 只在有附件时创建附件目录
        doc_attachments_dir = os.path.join(doc_markdown_dir, "attachments")
        if attachments:
            safe_makedirs(doc_attachments_dir, exist_ok=True)

        return doc_markdown_dir, doc_attachments_dir

    def _sanitize_title(self, title: str) -> str:
        """将标题中的非法字符替换为下划线"""
        return re.sub(r'[\\/:*?"<>|]', "_", title)

    def _save_attachments(
        self, attachments: List[Dict[str, Any]], attachments_dir: str
    ) -> List[Dict[str, str]]:
        """保存爬虫页面对应的附件文件并返回附件信息列表"""
        saved_attachments = []
        for attachment in attachments:
            # 保存原始附件
            attachment_path = os.path.join(attachments_dir, attachment["filename"])
            with safe_open(attachment_path, "wb") as f:
                f.write(attachment["content"])
            # 如果有提取的文本内容，保存为文本格式的文件
            if attachment.get("extracted_text"):
                base_name = os.path.splitext(attachment["filename"])[0]
                # 根据文件类型保存对应的文本文件
                if attachment["type"] == "text/plain":
                    base_name = f"{base_name}.txt"
                elif attachment["type"] == "text/html":
                    base_name = f"{base_name}.html"
                elif attachment["type"] == "text/markdown":
                    base_name = f"{base_name}.md"
                else:
                    base_name = f"{base_name}.txt"

                text_path = os.path.join(attachments_dir, base_name)
                with safe_open(text_path, "w", encoding="utf-8") as f:
                    f.write(attachment["extracted_text"])
                saved_attachments.append(
                    {
                        "filename": attachment["filename"],
                        "path": attachment_path,
                        "text_path": text_path,
                    }
                )
            else:
                saved_attachments.append(
                    {"filename": attachment["filename"], "path": attachment_path}
                )
        return saved_attachments

    def _build_markdown_content(
        self, item: KMSItem, attachments_info: List[Dict[str, str]], safe_title: str
    ) -> str:
        """构建Markdown文档内容"""
        markdown_content = f"# {item.title}\n\n{item.content}\n\n"

        if attachments_info:
            markdown_content += "\n## 附件\n\n"
            for attachment in attachments_info:
                relative_path = os.path.join("attachments", attachment["filename"])
                markdown_content += f'- [{attachment["filename"]}]({relative_path})\n'

        return markdown_content

    def export(self, item: KMSItem) -> tuple[str, str]:
        # 提取depth_info
        # depth_info = item.depth_info if item.depth_info else None
        """导出文档为Markdown格式

        Args:
            item: KMSItem对象，包含文档标题、内容和附件信息

        Returns:
            tuple: (markdown文件路径, 附件目录路径)
        """
        safe_title = self._sanitize_title(item.title)
        markdown_dir, attachments_dir = self._create_dirs(
            safe_title, item.attachments, item.depth_info
        )

        # 保存附件
        attachments_info = (
            self._save_attachments(item.attachments, attachments_dir) if item.attachments else []
        )

        # 构建并保存markdown内容
        markdown_content = self._build_markdown_content(item, attachments_info, safe_title)
        markdown_path = os.path.join(markdown_dir, f"{safe_title}.md")

        with safe_open(markdown_path, "w", encoding="utf-8") as f:
            f.write(markdown_content)

        return markdown_path, attachments_dir
