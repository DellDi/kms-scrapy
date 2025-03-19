#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
将一个目录中的所有 Markdown 文件转换为 Word 文档格式
支持处理 flatten_directory.py 工具处理后的目录结构
支持保留原始目录结构或扁平化输出
支持高级格式转换，包括标题、列表、表格、代码块等
"""

import os
import re
import argparse
import shutil
from pathlib import Path
from typing import Optional, List, Dict, Set, Tuple, Any
import logging
from datetime import datetime
import pypandoc

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)

logger = logging.getLogger('md_to_word')

class MarkdownToWordConverter:
    """Markdown 转 Word 转换器

    使用 pypandoc 将 Markdown 文件转换为 Word 文档
    支持保留目录结构或扁平化输出
    """

    def __init__(
        self,
        input_dir: str,
        output_dir: str = "./word_output",
        flat: bool = True,
        recursive: bool = True,
        overwrite: bool = False,
        template: Optional[str] = None,
        md_only: bool = True,
        copy_non_md: bool = False,
    ):
        """初始化转换器

        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
            flat: 是否扁平化输出 (True: 所有文件放在同一目录下, False: 保留目录结构)
            recursive: 是否递归处理子目录
            overwrite: 是否覆盖已存在的文件
            template: Word 模板文件路径
            md_only: 是否只处理 Markdown 文件
            copy_non_md: 是否复制非 Markdown 文件到目标目录 (只有当 md_only=True 时有效)
        """
        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.flat = flat
        self.recursive = recursive
        self.overwrite = overwrite
        self.template = template
        self.md_only = md_only
        self.copy_non_md = copy_non_md

        # 初始化统计信息
        self.stats = {
            "total": 0,
            "success": 0,
            "failed": 0,
            "skipped": 0,
            "copied": 0,
        }

        # 创建输出目录
        os.makedirs(self.output_dir, exist_ok=True)

    def convert_directory(self) -> None:
        """转换目录中的所有 Markdown 文件为 Word 文档"""
        if self.recursive:
            for root, _, files in os.walk(self.input_dir):
                self._process_files_in_directory(root, files)
        else:
            # 只处理顶层目录
            _, _, files = next(os.walk(self.input_dir))
            self._process_files_in_directory(self.input_dir, files)

        # 输出统计信息
        logger.info(f"转换完成! 共处理 {self.stats['total']} 个文件")
        logger.info(f"- 成功转换: {self.stats['success']} 个文件")
        logger.info(f"- 跳过文件: {self.stats['skipped']} 个文件")
        logger.info(f"- 转换失败: {self.stats['failed']} 个文件")
        logger.info(f"- 复制文件: {self.stats['copied']} 个文件")
        logger.info(f"所有 Word 文档已保存到: {self.output_dir}")

    def _process_files_in_directory(self, root: str, files: List[str]) -> None:
        """处理目录中的文件

        Args:
            root: 当前处理的目录路径
            files: 目录中的文件列表
        """
        for file in files:
            if self.md_only and not file.lower().endswith('.md'):
                if self.copy_non_md:
                    input_file = os.path.join(root, file)

                    # 确定输出文件路径
                    if self.flat:
                        # 扁平化输出，所有文件放在同一目录下
                        output_file = os.path.join(self.output_dir, os.path.basename(input_file))
                    else:
                        # 保留目录结构
                        rel_path = os.path.relpath(root, self.input_dir)
                        output_dir = os.path.join(self.output_dir, rel_path)
                        os.makedirs(output_dir, exist_ok=True)
                        output_file = os.path.join(output_dir, os.path.basename(input_file))

                    # 检查文件是否已存在
                    if os.path.exists(output_file) and not self.overwrite:
                        logger.info(f"跳过已存在的文件: {output_file}")
                        self.stats['skipped'] += 1
                        self.stats['total'] += 1
                        continue

                    # 复制文件
                    shutil.copy2(input_file, output_file)
                    logger.info(f"复制文件: {input_file} -> {output_file}")
                    self.stats['copied'] += 1
                    self.stats['total'] += 1
                else:
                    self.stats['skipped'] += 1
                    self.stats['total'] += 1
                continue

            input_file = os.path.join(root, file)

            # 确定输出文件路径
            if self.flat:
                # 扁平化输出，所有文件放在同一目录下
                output_file = os.path.join(self.output_dir, os.path.basename(input_file))
            else:
                # 保留目录结构
                rel_path = os.path.relpath(root, self.input_dir)
                # 检查是否是分页目录结构（如 page_1, page_2 等）
                output_dir = os.path.join(self.output_dir, rel_path)
                os.makedirs(output_dir, exist_ok=True)
                output_file = os.path.join(output_dir, os.path.basename(input_file))

            # 修改扩展名为 .docx
            output_file = os.path.splitext(output_file)[0] + '.docx'

            # 检查文件是否已存在
            if os.path.exists(output_file) and not self.overwrite:
                logger.info(f"跳过已存在的文件: {output_file}")
                self.stats['skipped'] += 1
                self.stats['total'] += 1
                continue

            # 转换文件
            self.convert_file(input_file, output_file)

    def convert_file(self, input_file: str, output_file: str) -> bool:
        """转换单个 Markdown 文件为 Word 文档

        Args:
            input_file: 输入 Markdown 文件路径
            output_file: 输出 Word 文档路径

        Returns:
            转换是否成功
        """
        self.stats['total'] += 1

        try:
            # 准备转换参数
            extra_args = []

            # 如果指定了模板，添加模板参数
            if self.template:
                extra_args.extend(['--reference-doc', self.template])

            # 使用 pypandoc 进行转换
            pypandoc.convert_file(
                input_file,
                'docx',
                outputfile=output_file,
                extra_args=extra_args
            )

            logger.info(f"成功转换: {input_file} -> {output_file}")
            self.stats['success'] += 1
            return True

        except Exception as e:
            logger.error(f"转换失败: {input_file} - {str(e)}")
            self.stats['failed'] += 1
            return False


def main():
    """主函数，处理命令行参数并执行转换"""
    parser = argparse.ArgumentParser(description='将 Markdown 文件转换为 Word 文档')
    parser.add_argument('input_dir', help='输入目录，包含 Markdown 文件')
    parser.add_argument('-o', '--output-dir', dest='output_dir', default='./word_output',
                        help='输出目录，用于保存 Word 文档')
    parser.add_argument('--flat', action='store_true', help='扁平化输出，不保留目录结构')
    parser.add_argument('--no-recursive', dest='recursive', action='store_false',
                        help='不递归处理子目录')
    parser.add_argument('--overwrite', action='store_true', help='覆盖已存在的文件')
    parser.add_argument('--template', help='Word 模板文件路径')
    parser.add_argument('--all-files', dest='md_only', action='store_false',
                        help='处理所有文件，不仅仅是 .md 文件')
    parser.add_argument('--copy-non-md', dest='copy_non_md', action='store_true',
                        help='复制非 Markdown 文件到目标目录')

    args = parser.parse_args()

    # 检查 pandoc 是否已安装
    try:
        pypandoc.get_pandoc_version()
    except OSError:
        logger.error("未找到 pandoc。请先安装 pandoc: https://pandoc.org/installing.html")
        return 1

    # 创建转换器并执行转换
    converter = MarkdownToWordConverter(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        flat=args.flat,
        recursive=args.recursive,
        overwrite=args.overwrite,
        template=args.template,
        md_only=args.md_only,
        copy_non_md=args.copy_non_md
    )

    converter.convert_directory()
    return 0


if __name__ == '__main__':
    exit(main())
