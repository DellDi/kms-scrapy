#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库生成工具主程序

连接数据库，生成结构化的知识库文档
"""

import os
import argparse
import logging
import asyncio
from pathlib import Path

import sys
from pathlib import Path

# 添加当前目录到系统路径，以便能够正确导入模块
current_dir = str(Path(__file__).parent.absolute())
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# 使用绝对导入
from config.settings import settings
from core.db import MySQLConnector
from core.llm import LLMEnricher
from core.doc_generator import DocGenerator
from core.generator_factory import factory

# 导入所有生成器
from generators.target_generator import TargetGenerator

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gen-target")


def register_generators():
    """注册所有知识库生成器"""
    factory.register("target", TargetGenerator)
    # 在这里注册更多生成器
    # factory.register("project", ProjectGenerator)


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="知识库生成工具")
    parser.add_argument("--output", "-o", default="./output/docs", help="输出目录")
    parser.add_argument("--generator", "-g", default="target", help="生成器类型，如target, project等")
    parser.add_argument("--category", "-c", type=int, help="指定要处理的类别ID")
    parser.add_argument("--limit", "-l", type=int, default=0, help="限制每种类别处理的项目数量，0表示不限制")
    parser.add_argument("--no-llm", action="store_true", help="不使用LLM增强内容")
    parser.add_argument("--concurrency", type=int, default=1, help="LLM请求并发数")
    parser.add_argument("--delay", type=float, default=0.5, help="LLM请求间隔延迟(秒)")
    args = parser.parse_args()
    
    # 更新配置
    settings.update_from_args(args)
    
    # 注册生成器
    register_generators()
    
    # 创建数据库连接器
    db_connector = MySQLConnector(settings.get_db_config())
    
    # 创建文档生成器
    doc_generator = DocGenerator(settings.output_dir)
    
    # 创建LLM增强器
    llm_enricher = None
    if settings.use_llm:
        llm_enricher = LLMEnricher(
            settings.openai_api_key,
            settings.openai_model,
            settings.openai_base_url
        )
    
    # 创建知识库生成器
    generator = factory.create(
        settings.generator_type,
        db_connector,
        doc_generator,
        llm_enricher,
        settings.limit
    )
    
    if not generator:
        logger.error(f"无法创建生成器: {settings.generator_type}")
        return
    
    try:
        # 生成知识库
        if settings.category_id is not None:
            await generator.generate_for_specific_category(settings.category_id)
        else:
            await generator.generate_all()
        
        logger.info("知识库生成完成")
        
    finally:
        # 断开数据库连接
        db_connector.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
