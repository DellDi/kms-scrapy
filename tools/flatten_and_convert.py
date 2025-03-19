#!/usr/bin/env python
# -*- coding: utf-8 -*-

"""
集成工具：扁平化目录并转换 Markdown 为 Word

这个工具结合了 flatten_directory.py 和 md_to_word.py 的功能，
可以一步完成目录扁平化和 Markdown 转 Word 的过程。
"""

import os
import sys
import argparse
import logging
import tempfile
import shutil
from pathlib import Path
from typing import Optional

# 导入其他工具模块
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from tools.flatten_directory import DirectoryFlattener
from tools.md_to_word import MarkdownToWordConverter

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.StreamHandler()],
)
logger = logging.getLogger("flatten_and_convert")


class FlattenAndConvert:
    """扁平化目录并转换 Markdown 文件为 Word 文档"""

    def __init__(
        self,
        input_dir: str,
        output_dir: str = "./word_output",
        temp_dir: Optional[str] = None,
        keep_temp: bool = False,
        no_convert: bool = False,
        template: Optional[str] = None,
        md_only: bool = True,
        flat_output: bool = True,
        recursive: bool = True,
        page_size: Optional[int] = None,
        overwrite: bool = False,
        copy_non_md: bool = False,
    ):
        """初始化集成工具

        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径
            temp_dir: 临时目录路径 (如果不指定，则自动创建)
            keep_temp: 是否保留临时目录
            no_convert: 是否跳过转换，只执行扁平化
            template: Word 模板文件路径
            md_only: 是否只处理 Markdown 文件
            flat_output: 是否扁平化输出
            recursive: 是否递归处理子目录
            page_size: 每页文件数量
            overwrite: 是否覆盖已存在的文件
            copy_non_md: 是否复制非 Markdown 文件到目标目录
        """
        self.input_dir = os.path.abspath(input_dir)
        self.output_dir = os.path.abspath(output_dir)
        self.keep_temp = keep_temp
        self.no_convert = no_convert
        self.template = template
        self.md_only = md_only
        self.flat_output = flat_output
        self.recursive = recursive
        self.page_size = page_size
        self.overwrite = overwrite
        self.copy_non_md = copy_non_md

        # 设置临时目录
        if temp_dir:
            self.temp_dir = os.path.abspath(temp_dir)
            os.makedirs(self.temp_dir, exist_ok=True)
            self.auto_temp = False
        else:
            self.temp_dir = tempfile.mkdtemp(prefix="flatten_md_")
            self.auto_temp = True

        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

    def __del__(self):
        """析构函数，清理临时目录"""
        if hasattr(self, "auto_temp") and self.auto_temp and not self.keep_temp:
            try:
                if os.path.exists(self.temp_dir):
                    shutil.rmtree(self.temp_dir)
                    logger.info(f"已删除临时目录: {self.temp_dir}")
            except Exception as e:
                logger.warning(f"清理临时目录时出错: {str(e)}")

    def process(self) -> bool:
        """执行扁平化和转换过程

        Returns:
            处理是否成功
        """
        try:
            # 步骤 1: 扁平化目录
            logger.info(f"步骤 1: 扁平化目录 {self.input_dir} -> {self.temp_dir}")
            flattener = DirectoryFlattener(
                input_dir=self.input_dir,
                output_dir=self.temp_dir,
                page_size=self.page_size,
            )
            flattener.flatten()

            # 步骤 2: 转换 Markdown 为 Word
            logger.info(f"步骤 2: 处理 {self.temp_dir} -> {self.output_dir}")
            if self.no_convert:
                logger.info("跳过转换，直接复制文件")
                # 如果输出目录已存在，先删除
                if os.path.exists(self.output_dir):
                    if self.overwrite:
                        logger.info(f"输出目录已存在，正在删除: {self.output_dir}")
                        shutil.rmtree(self.output_dir)
                    else:
                        logger.error(f"输出目录已存在，且未指定覆盖: {self.output_dir}")
                        return False

                # 复制目录
                for root, dirs, files in os.walk(self.temp_dir):
                    for file in files:
                        file_path = os.path.join(root, file)
                        rel_path = os.path.relpath(file_path, self.temp_dir)
                        output_file_path = os.path.join(self.output_dir, rel_path)
                        output_dir = os.path.dirname(output_file_path)
                        os.makedirs(output_dir, exist_ok=True)
                        shutil.copy2(file_path, output_file_path)
                logger.info(f"已复制所有文件到: {self.output_dir}")
                return True
            else:
                converter = MarkdownToWordConverter(
                    input_dir=self.temp_dir,
                    output_dir=self.output_dir,
                    flat=self.flat_output,
                    recursive=self.recursive,
                    overwrite=self.overwrite,
                    template=self.template,
                    md_only=self.md_only,
                    copy_non_md=self.copy_non_md
                )
                converter.convert_directory()

            logger.info(f"处理完成! Word 文档已保存到: {self.output_dir}")
            return True

        except Exception as e:
            logger.error(f"处理过程中出错: {str(e)}")
            return False


def main():
    """主函数，处理命令行参数并执行集成工具"""
    parser = argparse.ArgumentParser(description="扁平化目录并转换 Markdown 为 Word")
    parser.add_argument("input_dir", help="输入目录路径")
    parser.add_argument(
        "-o",
        "--output-dir",
        dest="output_dir",
        default="./word_output",
        help="输出目录路径 (默认: ./word_output)",
    )
    parser.add_argument("--page-size", type=int, default=None, help="每页文件数量")
    parser.add_argument("--temp-dir", dest="temp_dir", help="临时目录路径 (默认: 自动创建)")
    parser.add_argument("--keep-temp", default=False, action="store_true", help="保留临时目录")
    parser.add_argument(
        "--no-convert", default=False, action="store_true", help="不处理原始文件，跳过转换"
    )
    parser.add_argument("--template", help="Word 模板文件路径")
    parser.add_argument(
        "--all-files",
        dest="md_only",
        default=True,
        action="store_false",
        help="处理所有文件，不仅仅是 .md 文件",
    )
    parser.add_argument(
        "--preserve-structure",
        dest="flat_output",
        action="store_false",
        help="保留目录结构，不扁平化输出",
    )
    parser.add_argument(
        "--no-recursive", dest="recursive", action="store_false", help="不递归处理子目录"
    )
    parser.add_argument(
        "--overwrite", default=False, action="store_true", help="覆盖输出目录"
    )
    parser.add_argument(
        "--copy-non-md", default=False, action="store_true", help="复制非 Markdown 文件到目标目录"
    )

    args = parser.parse_args()

    # 检查 pandoc 是否已安装
    try:
        import pypandoc

        pypandoc.get_pandoc_version()
    except ImportError:
        logger.error("未找到 pypandoc 库。请安装: pip install pypandoc")
        return 1
    except OSError:
        logger.error("未找到 pandoc。请先安装 pandoc: https://pandoc.org/installing.html")
        return 1

    # 创建并执行集成工具
    processor = FlattenAndConvert(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        temp_dir=args.temp_dir,
        keep_temp=args.keep_temp,
        template=args.template,
        md_only=args.md_only,
        no_convert=args.no_convert,
        flat_output=args.flat_output,
        recursive=args.recursive,
        page_size=args.page_size,
        overwrite=args.overwrite,
        copy_non_md=args.copy_non_md
    )

    success = processor.process()
    return 0 if success else 1


if __name__ == "__main__":
    exit(main())
