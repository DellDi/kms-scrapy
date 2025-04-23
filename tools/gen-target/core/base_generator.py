#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
知识库生成器基类

定义知识库生成器的通用接口和基础功能
"""

import logging
import asyncio
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional, TypeVar, Generic

from .db import MySQLConnector
from .llm import LLMEnricher
from .doc_generator import DocGenerator

logger = logging.getLogger("gen-target.generator")

T = TypeVar('T')  # 数据项类型
C = TypeVar('C')  # 类别ID类型


class BaseGenerator(Generic[T, C], ABC):
    """知识库生成器基类"""
    
    def __init__(self, 
                db_connector: MySQLConnector, 
                doc_generator: DocGenerator,
                llm_enricher: Optional[LLMEnricher] = None,
                limit: int = 0):
        """
        初始化知识库生成器
        
        Args:
            db_connector: 数据库连接器
            doc_generator: 文档生成器
            llm_enricher: LLM增强器，可选
            limit: 每个类别处理的项目数量限制，0表示不限制
        """
        self.db = db_connector
        self.doc_generator = doc_generator
        self.llm_enricher = llm_enricher
        self.limit = limit
        self.categories: Dict[C, str] = {}  # 类别映射 {类别ID: 类别名称}
        self.category_counts: Dict[C, int] = {}  # 类别计数 {类别ID: 项目数量}
    
    @abstractmethod
    async def initialize(self) -> bool:
        """
        初始化生成器，加载必要的数据
        
        Returns:
            bool: 初始化是否成功
        """
        pass
    
    @abstractmethod
    async def get_categories(self) -> Dict[C, str]:
        """
        获取所有类别
        
        Returns:
            Dict[C, str]: 类别映射 {类别ID: 类别名称}
        """
        pass
    
    @abstractmethod
    async def get_items(self, category_id: Optional[C] = None) -> List[Dict[str, Any]]:
        """
        获取指定类别或所有类别的项目数据
        
        Args:
            category_id: 类别ID，None表示获取所有类别
            
        Returns:
            List[Dict[str, Any]]: 项目数据列表
        """
        pass
    
    @abstractmethod
    def create_item(self, data: Dict[str, Any]) -> T:
        """
        从原始数据创建项目对象
        
        Args:
            data: 原始数据
            
        Returns:
            T: 项目对象
        """
        pass
    
    @abstractmethod
    def get_prompt_generator(self) -> callable:
        """
        获取提示词生成函数
        
        Returns:
            callable: 接收项目对象返回提示词的函数
        """
        pass
    
    @abstractmethod
    def get_result_processor(self) -> callable:
        """
        获取结果处理函数
        
        Returns:
            callable: 接收项目对象和LLM结果，返回增强后项目对象的函数
        """
        pass
    
    async def process_items(self, items_data: List[Dict[str, Any]]) -> List[T]:
        """
        处理项目数据
        
        Args:
            items_data: 原始项目数据列表
            
        Returns:
            List[T]: 处理后的项目对象列表
        """
        # 创建项目对象
        items = [self.create_item(data) for data in items_data]
        
        # 使用LLM增强项目内容
        if self.llm_enricher:
            prompt_generator = self.get_prompt_generator()
            result_processor = self.get_result_processor()
            
            items = await self.llm_enricher.batch_enrich(
                items, 
                prompt_generator, 
                result_processor
            )
        
        return items
    
    async def generate_for_category(self, category_id: C) -> bool:
        """
        为指定类别生成知识库文档
        
        Args:
            category_id: 类别ID
            
        Returns:
            bool: 是否成功
        """
        if category_id not in self.categories:
            logger.error(f"类别 {category_id} 不存在")
            return False
        
        # 获取类别项目数据
        items_data = await self.get_items(category_id)
        if self.limit > 0:
            items_data = items_data[:self.limit]
        
        logger.info(f"获取到类别 {category_id} 的 {len(items_data)} 个项目")
        self.category_counts[category_id] = len(items_data)
        
        # 处理项目数据
        items = await self.process_items(items_data)
        
        # 生成文档
        category_name = self.categories[category_id]
        self.doc_generator.generate_doc(
            f"{category_name}.md",
            f"{category_name} 知识库",
            items
        )
        
        return True
    
    async def generate_all(self) -> bool:
        """
        生成所有类别的知识库文档
        
        Returns:
            bool: 是否成功
        """
        # 初始化生成器
        if not await self.initialize():
            return False
        
        # 获取所有类别
        self.categories = await self.get_categories()
        logger.info(f"获取到 {len(self.categories)} 个类别")
        
        # 为每个类别生成文档
        for category_id in self.categories:
            await self.generate_for_category(category_id)
        
        # 生成索引文档
        self.doc_generator.generate_index(
            "知识库索引",
            self.categories,
            self.category_counts
        )
        
        return True
    
    async def generate_for_specific_category(self, category_id: C) -> bool:
        """
        为特定类别生成知识库文档
        
        Args:
            category_id: 类别ID
            
        Returns:
            bool: 是否成功
        """
        # 初始化生成器
        if not await self.initialize():
            return False
        
        # 获取所有类别
        self.categories = await self.get_categories()
        
        # 检查类别是否存在
        if category_id not in self.categories:
            logger.error(f"指定的类别 {category_id} 不存在")
            return False
        
        # 为指定类别生成文档
        success = await self.generate_for_category(category_id)
        
        # 生成索引文档
        if success:
            filtered_categories = {category_id: self.categories[category_id]}
            self.doc_generator.generate_index(
                "知识库索引",
                filtered_categories,
                self.category_counts
            )
        
        return success
