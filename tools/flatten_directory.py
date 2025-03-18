#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文件扁平化工具

将一个文件夹内的所有深度的文件复制提取出来，到一个一维的扁平化的输出路径的文件夹内
支持过滤系统文件和隐藏文件，以及自定义忽略模式
支持按照分页参数将文件分组到子文件夹中
"""

import os
import re
import shutil
import argparse
import hashlib
import math
from pathlib import Path
from typing import Optional, Dict, Set, Tuple, List
from datetime import datetime


class DirectoryFlattener:
    """目录扁平化处理类"""

    # 默认忽略的文件模式
    DEFAULT_IGNORE_PATTERNS = [
        r'\.DS_Store$',  # macOS系统文件
        r'^\._.*',      # macOS元数据文件
        r'Thumbs\.db$', # Windows缩略图文件
        r'desktop\.ini$', # Windows桌面配置文件
        r'\.$',         # 当前目录
        r'\.\.$'        # 上级目录
    ]

    def __init__(self, input_dir: str, output_dir: Optional[str] = None,
                 ignore_patterns: Optional[List[str]] = None,
                 ignore_hidden: bool = True,
                 ignore_system_files: bool = True,
                 page_size: Optional[int] = None):
        """
        初始化目录扁平化处理器

        Args:
            input_dir: 输入目录路径
            output_dir: 输出目录路径，如果为None则使用默认值
        """
        self.input_dir = os.path.abspath(input_dir)

        # 如果输出目录为None，则使用默认值：input_dir_flattened
        if output_dir is None:
            parent_dir = os.path.dirname(self.input_dir)
            dir_name = os.path.basename(self.input_dir)
            self.output_dir = os.path.join(parent_dir, f"{dir_name}_flattened")
        else:
            self.output_dir = os.path.abspath(output_dir)

        # 设置忽略模式
        self.ignore_patterns = list(self.DEFAULT_IGNORE_PATTERNS)
        if ignore_patterns:
            self.ignore_patterns.extend(ignore_patterns)

        self.ignore_hidden = ignore_hidden
        self.ignore_system_files = ignore_system_files
        self.page_size = page_size  # 每页文件数量

        self.file_map: Dict[str, str] = {}  # 原始文件路径 -> 目标文件路径
        self.duplicates: Set[Tuple[str, str]] = set()  # 记录重复文件
        self.skipped_files: int = 0  # 被忽略的文件数量
        self.page_count: int = 0  # 总页数

    def should_ignore_file(self, file_path: str) -> bool:
        """判断文件是否应该被忽略

        Args:
            file_path: 文件路径

        Returns:
            bool: 如果应该忽略则返回True，否则返回False
        """
        file_name = os.path.basename(file_path)

        # 检查是否为隐藏文件
        if self.ignore_hidden and file_name.startswith('.'):
            return True

        # 检查是否匹配忽略模式
        for pattern in self.ignore_patterns:
            if re.search(pattern, file_name):
                return True

        return False

    def scan_directory(self) -> None:
        """扫描目录并构建文件映射"""
        print(f"正在扫描目录: {self.input_dir}")

        # 用于检测文件名冲突
        filename_map: Dict[str, str] = {}

        for root, _, files in os.walk(self.input_dir):
            for file in files:
                # 原始文件的完整路径
                original_path = os.path.join(root, file)

                # 检查是否应该忽略该文件
                if self.should_ignore_file(original_path):
                    self.skipped_files += 1
                    continue

                # 如果文件名已存在，则添加哈希值以避免冲突
                if file in filename_map:
                    # 计算文件内容的哈希值前8位
                    file_hash = self._calculate_file_hash(original_path)[:8]
                    base_name, ext = os.path.splitext(file)
                    new_filename = f"{base_name}_{file_hash}{ext}"

                    # 记录重复文件
                    self.duplicates.add((original_path, filename_map[file]))

                    # 更新文件映射
                    if self.page_size is None:
                        self.file_map[original_path] = os.path.join(self.output_dir, new_filename)
                    else:
                        # 暂时存储文件名，稍后再分配到页面
                        self.file_map[original_path] = new_filename
                else:
                    # 文件名不存在冲突，直接使用原始文件名
                    filename_map[file] = original_path
                    if self.page_size is None:
                        self.file_map[original_path] = os.path.join(self.output_dir, file)
                    else:
                        # 暂时存储文件名，稍后再分配到页面
                        self.file_map[original_path] = file

    def flatten(self) -> None:
        """执行扁平化操作"""
        # 确保输出目录存在
        os.makedirs(self.output_dir, exist_ok=True)

        # 扫描目录
        self.scan_directory()

        # 复制文件
        total_files = len(self.file_map)
        print(f"共发现 {total_files} 个文件，开始复制...")

        # 如果设置了分页大小，则按页组织文件
        if self.page_size is not None and self.page_size > 0:
            self._organize_files_by_pages(total_files)
        else:
            # 不分页，直接复制到输出目录
            for i, (src, dst) in enumerate(self.file_map.items(), 1):
                try:
                    shutil.copy2(src, dst)
                    print(f"进度: [{i}/{total_files}] 复制: {os.path.basename(src)}")
                except Exception as e:
                    print(f"错误: 复制文件 {src} 失败: {str(e)}")

        # 输出重复文件信息
        if self.duplicates:
            print(f"\n发现 {len(self.duplicates)} 个文件名冲突，已通过添加哈希值解决:")
            for original, duplicate in self.duplicates:
                print(f"  - {os.path.basename(original)} 与 {os.path.basename(duplicate)} 冲突")

        # 输出忽略文件信息
        if self.skipped_files > 0:
            print(f"\n已忽略 {self.skipped_files} 个系统文件或隐藏文件")

        if self.page_size is not None and self.page_size > 0:
            print(f"\n扁平化完成! 所有文件已按每页 {self.page_size} 个文件分组，共 {self.page_count} 页")
            print(f"输出目录: {self.output_dir}")
        else:
            print(f"\n扁平化完成! 所有文件已复制到: {self.output_dir}")

    def _organize_files_by_pages(self, total_files: int) -> None:
        """按页组织文件

        Args:
            total_files: 总文件数
        """
        # 计算总页数
        self.page_count = math.ceil(total_files / self.page_size)
        print(f"按每页 {self.page_size} 个文件进行分组，共 {self.page_count} 页")

        # 创建临时映射，用于按页组织文件
        temp_map = {}
        file_list = list(self.file_map.items())

        for i, (src, filename) in enumerate(file_list):
            # 计算当前文件应该在哪一页
            page_num = i // self.page_size + 1
            page_dir = os.path.join(self.output_dir, f"page_{page_num}")

            # 确保页目录存在
            os.makedirs(page_dir, exist_ok=True)

            # 更新文件映射
            dst = os.path.join(page_dir, filename)
            temp_map[src] = dst

            # 复制文件
            try:
                shutil.copy2(src, dst)
                print(f"进度: [{i+1}/{total_files}] 复制: {filename} 到 page_{page_num}")
            except Exception as e:
                print(f"错误: 复制文件 {src} 失败: {str(e)}")

        # 更新文件映射
        self.file_map = temp_map

    @staticmethod
    def _calculate_file_hash(file_path: str) -> str:
        """计算文件的MD5哈希值"""
        hash_md5 = hashlib.md5()
        with open(file_path, "rb") as f:
            for chunk in iter(lambda: f.read(4096), b""):
                hash_md5.update(chunk)
        return hash_md5.hexdigest()


def main():
    """主函数"""
    # 解析命令行参数
    parser = argparse.ArgumentParser(
        description="将一个文件夹内的所有深度的文件复制提取出来，到一个一维的扁平化的输出路径的文件夹内"
    )
    parser.add_argument(
        "input_dir",
        type=str,
        help="输入目录路径"
    )
    parser.add_argument(
        "-o", "--output-dir",
        type=str,
        default=None,
        help="输出目录路径 (默认为: input_dir_flattened)"
    )
    parser.add_argument(
        "--include-hidden",
        action="store_true",
        help="包含隐藏文件 (默认忽略)"
    )
    parser.add_argument(
        "--include-system-files",
        action="store_true",
        help="包含系统文件如.DS_Store (默认忽略)"
    )
    parser.add_argument(
        "--ignore",
        type=str,
        nargs="+",
        help="额外的忽略文件模式，支持正则表达式"
    )
    parser.add_argument(
        "--page-size",
        type=int,
        default=None,
        help="分页大小，指定每个子文件夹中包含的文件数量 (默认不分页)"
    )

    args = parser.parse_args()

    # 检查输入目录是否存在
    if not os.path.isdir(args.input_dir):
        print(f"错误: 输入目录 '{args.input_dir}' 不存在或不是一个目录")
        return 1

    # 创建扁平化处理器并执行
    flattener = DirectoryFlattener(
        input_dir=args.input_dir,
        output_dir=args.output_dir,
        ignore_patterns=args.ignore,
        ignore_hidden=not args.include_hidden,
        ignore_system_files=not args.include_system_files,
        page_size=args.page_size
    )
    flattener.flatten()

    return 0


if __name__ == "__main__":
    exit(main())
