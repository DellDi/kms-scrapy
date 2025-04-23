#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
指标知识库生成器

实现指标知识库的生成逻辑
"""

import logging
import re
from typing import Dict, List, Any, Optional, Callable, TypeVar, cast

from core.base_generator import BaseGenerator
from core.db import MySQLConnector
from core.llm import LLMEnricher
from core.doc_generator import DocGenerator

logger = logging.getLogger("gen-target.target")


class TargetItem:
    """指标项数据模型"""
    
    def __init__(self, data: Dict[str, Any]):
        """
        初始化指标项
        
        Args:
            data: 原始数据
        """
        self.id = data.get("id")
        self.target_type = data.get("targetType")
        self.target_item_name = data.get("targetItemName", "")
        self.unit = data.get("unit", "")
        self.target_remark = data.get("targetRemark", "")
        self.is_good_target = data.get("isGoodTarget")
        self.target_icon = data.get("targetIcon")
        self.order_id = data.get("orderID")
        self.decimal_place = data.get("decimalPlace", 0)
        self.status = data.get("status", 1)
        
        # 生成的补充信息
        self.aliases: List[str] = []
        self.dimensions: List[str] = []
        self.related_terms: List[str] = []
        self.metric_id = self._generate_metric_id()
    
    def _generate_metric_id(self) -> str:
        """
        生成指标ID
        
        Returns:
            str: 指标ID
        """
        if not self.target_item_name:
            return f"metric_{self.id}"
        
        # 将中文名称转换为拼音或英文标识符
        name = self.target_item_name.lower()
        # 替换常见中文词汇为英文
        replacements = {
            "利润": "profit",
            "收入": "income",
            "成本": "cost",
            "费用": "expense",
            "率": "rate",
            "比例": "ratio",
            "增长": "growth",
            "销售": "sales",
            "资产": "assets",
            "负债": "liabilities",
            "现金": "cash",
            "流量": "flow",
            "回报": "return",
            "投资": "investment",
            "净": "net",
            "毛": "gross",
            "总": "total",
            "平均": "average",
            "月": "month",
            "年": "year",
            "季度": "quarter",
            "日": "day"
        }
        
        for cn, en in replacements.items():
            name = name.replace(cn, en)
        
        # 移除非字母数字字符，并用下划线替换空格
        name = re.sub(r'[^\w\s]', '', name)
        name = re.sub(r'\s+', '_', name)
        
        # 如果处理后仍有中文或为空，则使用ID
        if re.search(r'[\u4e00-\u9fff]', name) or not name:
            return f"metric_{self.id}"
        
        return f"metric_{name}"
    
    def to_markdown(self) -> str:
        """
        转换为Markdown格式
        
        Returns:
            str: Markdown格式的指标信息
        """
        aliases_str = ", ".join(self.aliases) if self.aliases else "无"
        dimensions_str = ", ".join(self.dimensions) if self.dimensions else "无"
        related_terms_str = ", ".join(self.related_terms) if self.related_terms else "无"
        
        md = f"""## 指标 ID: {self.metric_id}
标准名称: {self.target_item_name}
别名: {aliases_str}
定义: {self.target_remark or "无"}
单位: {self.unit or "无"}
常用维度: {dimensions_str}
相关术语: {related_terms_str}
"""
        return md


class TargetGenerator(BaseGenerator[TargetItem, int]):
    """指标知识库生成器"""
    
    def __init__(self, 
                db_connector: MySQLConnector, 
                doc_generator: DocGenerator,
                llm_enricher: Optional[LLMEnricher] = None,
                limit: int = 0):
        """
        初始化指标知识库生成器
        
        Args:
            db_connector: 数据库连接器
            doc_generator: 文档生成器
            llm_enricher: LLM增强器，可选
            limit: 每个类别处理的项目数量限制，0表示不限制
        """
        super().__init__(db_connector, doc_generator, llm_enricher, limit)
    
    async def initialize(self) -> bool:
        """
        初始化生成器
        
        Returns:
            bool: 初始化是否成功
        """
        # 连接数据库
        if not self.db.connect():
            return False
        
        return True
    
    async def get_categories(self) -> Dict[int, str]:
        """
        获取所有指标类型
        
        Returns:
            Dict[int, str]: 指标类型映射 {类型ID: 类型名称}
        """
        sql = """
        SELECT DISTINCT targetType, COUNT(*) as count 
        FROM target_targetitem 
        GROUP BY targetType
        """
        results = self.db.query(sql)
        return {row["targetType"]: f"Type_{row['targetType']}" for row in results}
    
    async def get_items(self, category_id: Optional[int] = None) -> List[Dict[str, Any]]:
        """
        获取指定类型或所有类型的指标项数据
        
        Args:
            category_id: 指标类型ID，None表示获取所有类型
            
        Returns:
            List[Dict[str, Any]]: 指标项数据列表
        """
        if category_id is not None:
            sql = """
            SELECT * FROM target_targetitem 
            WHERE targetType = %s AND status = 1
            ORDER BY orderID
            """
            return self.db.query(sql, (category_id,))
        else:
            sql = """
            SELECT * FROM target_targetitem 
            WHERE status = 1
            ORDER BY targetType, orderID
            """
            return self.db.query(sql)
    
    def create_item(self, data: Dict[str, Any]) -> TargetItem:
        """
        从原始数据创建指标项对象
        
        Args:
            data: 原始数据
            
        Returns:
            TargetItem: 指标项对象
        """
        return TargetItem(data)
    
    def get_prompt_generator(self) -> Callable[[TargetItem], str]:
        """
        获取提示词生成函数
        
        Returns:
            Callable[[TargetItem], str]: 提示词生成函数
        """
        def generate_prompt(item: TargetItem) -> str:
            return f"""
你是一位财务和业务指标专家，请根据以下指标信息，补充该指标的别名、常用维度和相关术语。
请以JSON格式返回，不要有任何其他文本。

指标名称: {item.target_item_name}
指标定义: {item.target_remark or '无'}
单位: {item.unit or '无'}

请返回以下格式的JSON:
{{
  "aliases": ["别名1", "别名2", ...],
  "dimensions": ["维度1", "维度2", ...],
  "related_terms": ["相关术语1", "相关术语2", ...]
}}

别名：指该指标的其他常用称呼，包括中英文名称、行业简称等
常用维度：指分析该指标时常用的维度，如时间、地区、产品、客户等
相关术语：与该指标相关的其他指标或业务术语
"""
        return generate_prompt
    
    def get_result_processor(self) -> Callable[[TargetItem, Dict[str, Any]], TargetItem]:
        """
        获取结果处理函数
        
        Returns:
            Callable[[TargetItem, Dict[str, Any]], TargetItem]: 结果处理函数
        """
        def process_result(item: TargetItem, data: Dict[str, Any]) -> TargetItem:
            item.aliases = data.get("aliases", [])
            item.dimensions = data.get("dimensions", [])
            item.related_terms = data.get("related_terms", [])
            return item
        
        return process_result
