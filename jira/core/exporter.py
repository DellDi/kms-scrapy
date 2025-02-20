import os
import logging
import textwrap
from concurrent import futures
from typing import Tuple, List, Optional
from datetime import datetime

from .config import config
from .spider import JiraIssue

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)


class ExportError(Exception):
    """导出相关异常"""

    pass


class DocumentExporter:
    """文档导出处理类"""

    def __init__(self):
        """初始化导出器"""
        self.base_dir = config.exporter.output_dir
        self.encoding = config.exporter.encoding

    def _ensure_directory(self, directory: str):
        """
        确保目录存在

        Args:
            directory: 目录路径
        """
        try:
            os.makedirs(directory, exist_ok=True)
        except Exception as e:
            raise ExportError(f"创建目录失败: {str(e)}")

    def generate_paths(self, issue: JiraIssue, page_num: int) -> Tuple[str, str]:
        """
        生成文件和目录路径

        Args:
            issue: JiraIssue对象
            page_num: 页码

        Returns:
            Tuple[str, str]: (文件路径, 目录路径)
        """
        # 生成分页目录
        page_dir = os.path.join(self.base_dir, f"{config.exporter.page_dir_prefix}{page_num}")

        # 生成文件路径 (使用问题Key作为文件名)
        file_path = os.path.join(page_dir, f"{issue.key}.md")

        return file_path, page_dir

    def format_content(self, issue: JiraIssue) -> str:
        """
        格式化问题内容为Markdown格式

        Args:
            issue: JiraIssue对象

        Returns:
            str: 格式化后的Markdown内容
        """
        # 使用textwrap.dedent保持正确的缩进
        template = textwrap.dedent(
            f"""
# {issue.summary}

## 问题链接: [{issue.key}]({issue.link})

## 基本信息

- **客户名称**: {issue.customer_name}
- **创建时间**: {issue.created_date}
- **解决时间**: {issue.resolved_date}
- **报告人**: {issue.reporter}
- **经办人**: {issue.assignee}
- **状态**: {issue.status}
- **优先级**: {issue.priority}
- **标签**: {", ".join(issue.labels)}

## 问题描述

{issue.description}

## 优化后的内容

{issue.optimized_content or "（无优化内容）"}

## 附件内容
{issue.annex_str or "（无附件内容）"}

---
*本文档由爬虫自动生成于 {datetime.now().strftime("%Y-%m-%d %H:%M:%S")}*
        """
        ).strip()

        return template

    def write_file(self, content: str, file_path: str):
        """
        写入文件内容

        Args:
            content: 文件内容
            file_path: 文件路径
        """
        try:
            # 确保目录存在
            self._ensure_directory(os.path.dirname(file_path))

            # 写入文件
            with open(file_path, "w", encoding=self.encoding) as f:
                f.write(content)

        except Exception as e:
            raise ExportError(f"写入文件失败: {str(e)}")

    def export_issue(
            self, issue: JiraIssue, page_num: int, overwrite: bool = True
    ) -> Optional[Tuple[str, str]]:
        """
        导出单个问题到Markdown文件

        Args:
            issue: JiraIssue对象
            page_num: 页码
            overwrite: 是否覆盖已存在的文件

        Returns:
            Optional[Tuple[str, str]]: (markdown文件路径, 目录路径)，失败则返回None
        """
        try:
            # 生成路径
            file_path, dir_path = self.generate_paths(issue, page_num)

            # 检查文件是否存在
            if not overwrite and os.path.exists(file_path):
                logger.warning(f"文件已存在且不覆盖: {file_path}")
                return None

            # 格式化内容
            content = self.format_content(issue)

            # 写入文件
            self.write_file(content, file_path)

            logger.info(f"成功导出问题 {issue.key} 到 {file_path}")
            return file_path, dir_path

        except Exception as e:
            logger.error(f"导出问题 {issue.key} 失败: {str(e)}")
            return None

    def batch_export(
            self, issues: List[JiraIssue], page_num: int, max_workers: int = 4
    ) -> List[Tuple[str, str]]:
        """
        批量导出问题

        Args:
            issues: JiraIssue对象列表
            page_num: 页码
            max_workers: 最大工作线程数

        Returns:
            List[Tuple[str, str]]: 导出成功的文件路径列表
        """
        successful_exports = []

        # 确保分页目录存在
        page_dir = os.path.join(self.base_dir, f"{config.exporter.page_dir_prefix}{page_num}")
        self._ensure_directory(page_dir)

        # 使用线程池并行处理
        with futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            # 提交所有导出任务
            future_to_issue = {
                executor.submit(self.export_issue, issue, page_num): issue for issue in issues
            }

            # 收集结果
            for future in futures.as_completed(future_to_issue):
                issue = future_to_issue[future]
                try:
                    result = future.result()
                    if result:
                        successful_exports.append(result)
                except Exception as e:
                    logger.error(f"批量导出中处理 {issue.key} 失败: {str(e)}")

        return successful_exports

    def clear_output_directory(self):
        """清空输出目录"""
        try:
            if os.path.exists(self.base_dir):
                for root, dirs, files in os.walk(self.base_dir, topdown=False):
                    for name in files:
                        os.remove(os.path.join(root, name))
                    for name in dirs:
                        os.rmdir(os.path.join(root, name))
                os.rmdir(self.base_dir)
            logger.info(f"成功清空输出目录: {self.base_dir}")
        except Exception as e:
            raise ExportError(f"清空输出目录失败: {str(e)}")
