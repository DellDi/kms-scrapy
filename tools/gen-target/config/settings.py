#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
配置设置模块

加载和管理配置信息
"""

import os
import logging
from typing import Dict, Any, Optional
from pathlib import Path
import argparse

from dotenv import load_dotenv

logger = logging.getLogger("gen-target.config")

# 加载环境变量
load_dotenv()


class Settings:
    """配置设置类"""

    def __init__(self):
        """初始化配置设置"""
        # 数据库配置
        self.db_config = {
            "host": os.getenv("MYSQL_HOST", "localhost"),
            "port": int(os.getenv("MYSQL_PORT", "3306")),
            "user": os.getenv("MYSQL_USER", "root"),
            "password": os.getenv("MYSQL_PASSWORD", ""),
            "db": os.getenv("MYSQL_DATABASE", "newsee-view"),
            "charset": "utf8mb4"
        }

        # OpenAI配置
        self.openai_api_key = os.getenv("OPENAI_API_KEY", "")
        self.openai_model = os.getenv("OPENAI_API_MODEL", "gpt-3.5-turbo")
        self.openai_base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1")

        # 输出配置
        self.output_dir = "./output/docs"

        # 运行配置
        self.generator_type = "target"  # 默认生成器类型
        self.category_id = None  # 指定要处理的类别ID
        self.limit = 0  # 限制每种类别处理的项目数量
        self.use_llm = True  # 是否使用LLM增强
        self.concurrency = 1  # LLM请求并发数
        self.delay = 0.5  # LLM请求间隔延迟

    def update_from_args(self, args: argparse.Namespace) -> None:
        """
        从命令行参数更新配置
        
        Args:
            args: 命令行参数
        """
        # 更新输出目录
        if hasattr(args, 'output') and args.output:
            self.output_dir = args.output

        # 更新生成器类型
        if hasattr(args, 'generator') and args.generator:
            self.generator_type = args.generator

        # 更新类别ID
        if hasattr(args, 'category') and args.category is not None:
            self.category_id = args.category

        # 更新限制数量
        if hasattr(args, 'limit') and args.limit > 0:
            self.limit = args.limit

        # 更新是否使用LLM
        if hasattr(args, 'no_llm') and args.no_llm:
            self.use_llm = False

        # 更新LLM并发数
        if hasattr(args, 'concurrency') and args.concurrency > 0:
            self.concurrency = args.concurrency

        # 更新LLM请求延迟
        if hasattr(args, 'delay') and args.delay >= 0:
            self.delay = args.delay

        # 检查OpenAI API密钥
        if self.use_llm and not self.openai_api_key:
            logger.warning("未设置OPENAI_API_KEY环境变量，将不使用LLM增强内容")
            self.use_llm = False

    def get_db_config(self) -> Dict[str, Any]:
        """
        获取数据库配置
        
        Returns:
            Dict[str, Any]: 数据库配置
        """
        return self.db_config.copy()

    def update_db_config(self, **kwargs) -> None:
        """
        更新数据库配置
        
        Args:
            **kwargs: 数据库配置参数
        """
        self.db_config.update(kwargs)


# 全局设置实例
settings = Settings()
