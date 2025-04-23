#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库生成器工厂

根据类型创建不同的知识库生成器
"""

import logging
import importlib
from typing import Dict, Type, Optional, Any

from .base_generator import BaseGenerator
from .db import MySQLConnector
from .llm import LLMEnricher
from .doc_generator import DocGenerator

logger = logging.getLogger("gen-target.factory")


class GeneratorFactory:
    """知识库生成器工厂"""
    
    def __init__(self):
        """初始化工厂"""
        self.generators: Dict[str, Type[BaseGenerator]] = {}
    
    def register(self, name: str, generator_class: Type[BaseGenerator]) -> None:
        """
        注册生成器类
        
        Args:
            name: 生成器名称
            generator_class: 生成器类
        """
        self.generators[name] = generator_class
        logger.debug(f"已注册生成器: {name}")
    
    def create(self, 
              name: str, 
              db_connector: MySQLConnector, 
              doc_generator: DocGenerator,
              llm_enricher: Optional[LLMEnricher] = None,
              limit: int = 0) -> Optional[BaseGenerator]:
        """
        创建生成器实例
        
        Args:
            name: 生成器名称
            db_connector: 数据库连接器
            doc_generator: 文档生成器
            llm_enricher: LLM增强器，可选
            limit: 每个类别处理的项目数量限制，0表示不限制
            
        Returns:
            Optional[BaseGenerator]: 生成器实例，如果不存在则返回None
        """
        if name not in self.generators:
            # 尝试动态导入
            try:
                module = importlib.import_module(f"generators.{name}_generator")
                # 约定生成器类名为 XxxGenerator，其中Xxx是首字母大写的name
                class_name = f"{name.capitalize()}Generator"
                generator_class = getattr(module, class_name)
                self.register(name, generator_class)
            except (ImportError, AttributeError) as e:
                logger.error(f"找不到生成器: {name}, 错误: {e}")
                return None
        
        generator_class = self.generators[name]
        return generator_class(db_connector, doc_generator, llm_enricher, limit)


# 全局工厂实例
factory = GeneratorFactory()
