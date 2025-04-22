#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
指标知识库生成工具

连接MySQL数据库，查询指标数据，并生成结构化的知识库文档。
根据targetType分类生成不同的文档，使用LLM补充指标的别名、相关术语等信息。
"""

import os
import argparse
import logging
from typing import Dict, List, Optional, Any
from pathlib import Path
import asyncio
import re
from datetime import datetime

try:
    import pymysql
    from pymysql.cursors import DictCursor
except ImportError:
    raise ImportError("请安装pymysql: uv pip install pymysql")

try:
    from openai import AsyncOpenAI
except ImportError:
    raise ImportError("请安装openai: uv pip install openai")

from dotenv import load_dotenv

# 配置日志
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("gen-target")

# 加载环境变量
load_dotenv()

# 数据库配置
DB_CONFIG = {
    "host": os.getenv("MYSQL_HOST", "localhost"),
    "port": int(os.getenv("MYSQL_PORT", "3306")),
    "user": os.getenv("MYSQL_USER", "root"),
    "password": os.getenv("MYSQL_PASSWORD", ""),
    "db": os.getenv("MYSQL_DATABASE", "newsee-view"),
    "charset": "utf8mb4",
}

# OpenAI配置
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_API_MODEL = os.getenv("OPENAI_API_MODEL", "gpt-3.5-turbo")
OPENAI_API_URL = os.getenv("OPENAI_API_URL", "https://api.openai.com/v1")

# 指标类型映射
TARGET_TYPE_MAPPING = {}  # 将在运行时填充


class TargetItem:
    """指标项数据模型"""

    def __init__(self, data: Dict[str, Any]):
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
        """生成指标ID"""
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
            "日": "day",
        }

        for cn, en in replacements.items():
            name = name.replace(cn, en)

        # 移除非字母数字字符，并用下划线替换空格
        name = re.sub(r"[^\w\s]", "", name)
        name = re.sub(r"\s+", "_", name)

        # 如果处理后仍有中文或为空，则使用ID
        if re.search(r"[\u4e00-\u9fff]", name) or not name:
            return f"metric_{self.id}"

        return f"metric_{name}"

    def to_markdown(self) -> str:
        """转换为Markdown格式"""
        aliases_str = ", ".join(self.aliases) if self.aliases else "无"
        dimensions_str = ", ".join(self.dimensions) if self.dimensions else "无"
        related_terms_str = ", ".join(self.related_terms) if self.related_terms else "无"

        md = f"""## 指标 ID: {self.metric_id}
标准名称: {self.target_item_name}
别名: {aliases_str}
定义: {self.target_remark[:100] or "无"}
单位: {self.unit or "无"}
常用维度: {dimensions_str}
相关术语: {related_terms_str}
"""
        return md


class MySQLConnector:
    """MySQL数据库连接器"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.conn = None

    def connect(self):
        """连接数据库"""
        try:
            self.conn = pymysql.connect(**self.config, cursorclass=DictCursor)
            logger.info(f"成功连接到数据库 {self.config['db']}")
            return True
        except Exception as e:
            logger.error(f"数据库连接失败: {e}")
            return False

    def disconnect(self):
        """断开数据库连接"""
        if self.conn:
            self.conn.close()
            logger.info("数据库连接已关闭")

    def query(self, sql: str, params: Optional[tuple] = None) -> List[Dict[str, Any]]:
        """执行查询"""
        if not self.conn:
            if not self.connect():
                return []

        try:
            with self.conn.cursor() as cursor:
                cursor.execute(sql, params or ())
                return cursor.fetchall()
        except Exception as e:
            logger.error(f"查询执行失败: {e}")
            return []

    def get_target_types(self) -> Dict[int, str]:
        """获取所有指标类型"""
        sql = """
        SELECT DISTINCT targetType, COUNT(*) as count 
        FROM target_targetitem 
        GROUP BY targetType
        """
        results = self.query(sql)
        return {row["targetType"]: f"Type_{row['targetType']}" for row in results}

    def get_target_items(self, target_type: Optional[int] = None) -> List[Dict[str, Any]]:
        """获取指标项数据"""
        if target_type is not None:
            sql = """
            SELECT * FROM target_targetitem 
            WHERE targetType = %s AND status = 1
            ORDER BY orderID
            """
            return self.query(sql, (target_type,))
        else:
            sql = """
            SELECT * FROM target_targetitem 
            WHERE status = 1
            ORDER BY targetType, orderID
            """
            return self.query(sql)


class LLMEnricher:
    """使用LLM丰富指标数据"""

    def __init__(self, api_key: str, model: str, base_url: str):
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def enrich_target_item(self, item: TargetItem) -> TargetItem:
        """使用LLM丰富指标项信息"""
        if not item.target_item_name:
            return item

        prompt = f"""
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

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位财务和业务指标专家，请提供准确、专业的指标信息补充。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
                # response_format={"type": "json_object"},
            )

            content = response.choices[0].message.content
            if content:
                try:
                    import json

                    data = json.loads(content)
                    item.aliases = data.get("aliases", [])
                    item.dimensions = data.get("dimensions", [])
                    item.related_terms = data.get("related_terms", [])
                except Exception as e:
                    logger.error(f"解析LLM响应失败: {e}")

        except Exception as e:
            logger.error(f"调用LLM失败: {e}")

        return item


class TargetDocGenerator:
    """指标文档生成器"""

    def __init__(self, output_dir: str):
        self.output_dir = Path(output_dir)
        self.output_dir.mkdir(parents=True, exist_ok=True)

    def generate_doc_for_type(self, type_id: int, type_name: str, items: List[TargetItem]):
        """为指定类型生成文档"""
        if not items:
            logger.warning(f"指标类型 {type_id} 没有指标项，跳过文档生成")
            return

        file_path = self.output_dir / f"{type_name}.md"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write(f"# {type_name} 指标知识库\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")
            f.write(f"本文档包含 {len(items)} 个指标项\n\n")

            for item in items:
                f.write(item.to_markdown())
                f.write("\n---\n\n")

        logger.info(f"已生成文档: {file_path}")

    def generate_index(self, type_mapping: Dict[int, str], item_counts: Dict[int, int]):
        """生成索引文档"""
        file_path = self.output_dir / "index.md"

        with open(file_path, "w", encoding="utf-8") as f:
            f.write("# 指标知识库索引\n\n")
            f.write(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n")

            f.write("## 指标类型目录\n\n")
            for type_id, type_name in type_mapping.items():
                count = item_counts.get(type_id, 0)
                f.write(f"- [{type_name}](./{type_name}.md) ({count} 个指标)\n")

        logger.info(f"已生成索引文档: {file_path}")


async def process_target_items(
    items: List[Dict[str, Any]], enricher: LLMEnricher
) -> List[TargetItem]:
    """处理指标项数据"""
    target_items = [TargetItem(item) for item in items]

    # 使用LLM丰富指标数据
    enriched_items = []
    for item in target_items:
        enriched_item = await enricher.enrich_target_item(item)
        enriched_items.append(enriched_item)
        # 添加一些延迟以避免API限制
        await asyncio.sleep(0.5)

    return enriched_items


async def main():
    """主函数"""
    parser = argparse.ArgumentParser(description="指标知识库生成工具")
    parser.add_argument("--output", "-o", default="./output/target-docs", help="输出目录")
    parser.add_argument("--type", "-t", type=int, help="指定要处理的指标类型ID")
    parser.add_argument(
        "--limit", "-l", type=int, default=0, help="限制每种类型处理的指标数量，0表示不限制"
    )
    parser.add_argument("--no-llm", action="store_true", help="不使用LLM丰富指标数据")
    args = parser.parse_args()

    # 检查OpenAI API密钥
    if not args.no_llm and not OPENAI_API_KEY:
        logger.warning("未设置OPENAI_API_KEY环境变量，将不使用LLM丰富指标数据")
        args.no_llm = True

    # 连接数据库
    db = MySQLConnector(DB_CONFIG)
    if not db.connect():
        return

    try:
        # 获取指标类型
        global TARGET_TYPE_MAPPING
        TARGET_TYPE_MAPPING = db.get_target_types()
        logger.info(f"获取到 {len(TARGET_TYPE_MAPPING)} 种指标类型")

        # 创建文档生成器
        doc_generator = TargetDocGenerator(args.output)

        # 创建LLM丰富器
        enricher = None
        if not args.no_llm:
            enricher = LLMEnricher(OPENAI_API_KEY, OPENAI_API_MODEL, OPENAI_API_URL)

        # 处理指定类型或所有类型
        item_counts = {}
        if args.type is not None:
            if args.type not in TARGET_TYPE_MAPPING:
                logger.error(f"指定的指标类型 {args.type} 不存在")
                return

            # 获取指定类型的指标项
            items = db.get_target_items(args.type)
            if args.limit > 0:
                items = items[: args.limit]

            logger.info(f"获取到类型 {args.type} 的 {len(items)} 个指标项")
            item_counts[args.type] = len(items)

            # 处理指标项
            if enricher:
                target_items = await process_target_items(items, enricher)
            else:
                target_items = [TargetItem(item) for item in items]

            # 生成文档
            doc_generator.generate_doc_for_type(
                args.type, TARGET_TYPE_MAPPING[args.type], target_items
            )
        else:
            # 处理所有类型
            for type_id, type_name in TARGET_TYPE_MAPPING.items():
                items = db.get_target_items(type_id)
                if args.limit > 0:
                    items = items[: args.limit]

                logger.info(f"获取到类型 {type_id} 的 {len(items)} 个指标项")
                item_counts[type_id] = len(items)

                # 处理指标项
                if enricher:
                    target_items = await process_target_items(items, enricher)
                else:
                    target_items = [TargetItem(item) for item in items]

                # 生成文档
                doc_generator.generate_doc_for_type(type_id, type_name, target_items)

        # 生成索引文档
        doc_generator.generate_index(TARGET_TYPE_MAPPING, item_counts)

    finally:
        # 断开数据库连接
        db.disconnect()


if __name__ == "__main__":
    asyncio.run(main())
