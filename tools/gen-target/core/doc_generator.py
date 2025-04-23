#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
文档生成器模块

提供通用的知识库文档生成功能
"""

import logging
from typing import Dict, List, Any, Protocol, TypeVar, Generic
from pathlib import Path
from datetime import datetime

logger = logging.getLogger("gen-target.doc")

T = TypeVar('T')


class MarkdownSerializable(Protocol):
    """可序列化为Markdown的对象协议"""
    
    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        ...


class DocGenerator(Generic[T]):
    """通用文档生成器"""
    
    def __init__(self, output_dir: str):
        """
        初始化文档生成器
        
        Args:
            output_dir: 输出目录路径
        """
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_doc(self, 
                    filename: str, 
                    title: str, 
                    items: List[T],
                    item_to_markdown: callable = None) -> None:
        """
        生成文档
        
        Args:
            filename: 文件名（不含路径）
            title: 文档标题
            items: 文档项目列表
            item_to_markdown: 项目转Markdown函数，如果为None则使用项目的to_markdown方法
        """
        if not items:
            logger.warning(f"文档 {filename} 没有项目，跳过文档生成")
            return
        
        file_path = self.output_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"本文档包含 {len(items)} 个项目\n\n")
            
            for item in items:
                if item_to_markdown:
                    f.write(item_to_markdown(item))
                elif hasattr(item, 'to_markdown'):
                    f.write(item.to_markdown())
                else:
                    f.write(f"- {str(item)}\n")
                f.write("\n---\n\n")
        
        logger.info(f"已生成文档: {file_path}")
    
    def generate_index(self, 
                      title: str, 
                      categories: Dict[Any, str], 
                      category_counts: Dict[Any, int],
                      filename: str = "index.md") -> None:
        """
        生成索引文档
        
        Args:
            title: 索引标题
            categories: 类别映射 {类别ID: 类别名称}
            category_counts: 类别计数 {类别ID: 项目数量}
            filename: 索引文件名
        """
        file_path = self.output_dir / filename
        
        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {title}\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            
            f.write("## 目录\n\n")
            for cat_id, cat_name in categories.items():
                count = category_counts.get(cat_id, 0)
                doc_filename = f"{cat_name}.md"
                f.write(f"- [{cat_name}](./{doc_filename}) ({count} 个项目)\n")
        
        logger.info(f"已生成索引文档: {file_path}")
