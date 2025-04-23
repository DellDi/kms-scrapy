#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
LLM集成模块

提供通用的大语言模型集成功能，用于知识库内容增强
"""

import logging
import json
import asyncio
from typing import Dict, Any, Optional, List, Callable, TypeVar, Generic

try:
    from openai import AsyncOpenAI
except ImportError:
    raise ImportError("请安装openai: uv pip install openai")

logger = logging.getLogger("gen-target.llm")

T = TypeVar("T")


class LLMEnricher(Generic[T]):
    """通用LLM内容增强器"""

    def __init__(self, api_key: str, model: str, base_url: str):
        """
        初始化LLM增强器

        Args:
            api_key: OpenAI API密钥
            model: 模型名称
            base_url: API基础URL
        """
        self.client = AsyncOpenAI(api_key=api_key, base_url=base_url)
        self.model = model

    async def enrich_item(
        self,
        item: T,
        prompt_generator: Callable[[T], str],
        result_processor: Callable[[T, Dict[str, Any]], T],
    ) -> T:
        """
        使用LLM增强项目内容

        Args:
            item: 要增强的项目
            prompt_generator: 提示词生成函数，接收项目返回提示词
            result_processor: 结果处理函数，接收项目和LLM结果，返回增强后的项目

        Returns:
            T: 增强后的项目
        """
        prompt = prompt_generator(item)

        try:
            response = await self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {
                        "role": "system",
                        "content": "你是一位专业的知识库内容生成专家，请提供准确、专业的信息补充。",
                    },
                    {"role": "user", "content": prompt},
                ],
                temperature=0.3,
            )

            content = response.choices[0].message.content
            if content:
                try:
                    data = json.loads(content)
                    return result_processor(item, data)
                except json.JSONDecodeError as e:
                    logger.error(f"解析LLM响应失败: {e}")
                    logger.debug(f"原始响应: {content}")

        except Exception as e:
            logger.error(f"调用LLM失败: {e}")

        return item

    async def batch_enrich(
        self,
        items: List[T],
        prompt_generator: Callable[[T], str],
        result_processor: Callable[[T, Dict[str, Any]], T],
        concurrency: int = 1,
        delay: float = 0.5,
    ) -> List[T]:
        """
        批量增强项目内容

        Args:
            items: 要增强的项目列表
            prompt_generator: 提示词生成函数
            result_processor: 结果处理函数
            concurrency: 并发数量
            delay: 请求间隔延迟(秒)

        Returns:
            List[T]: 增强后的项目列表
        """
        results = []
        semaphore = asyncio.Semaphore(concurrency)

        async def process_with_semaphore(item: T) -> T:
            async with semaphore:
                result = await self.enrich_item(item, prompt_generator, result_processor)
                await asyncio.sleep(delay)
                return result

        tasks = [process_with_semaphore(item) for item in items]
        results = await asyncio.gather(*tasks)

        return results
