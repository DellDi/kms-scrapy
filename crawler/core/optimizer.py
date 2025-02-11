from abc import ABC, abstractmethod
import json
import requests
from typing import Optional
from .config import config


class ContentOptimizer(ABC):
    """内容优化器的抽象基类"""

    SYSTEM_PROMPT = f"""
        你是一个智能的语义化提炼分析小助手，我可以帮你提取和优化网页内容。
        
        ⭐️<重要>⭐️如果得到的内容是空白或者没有任何语义的内容，请直接响应输出```md ```即可。
        
        如果是类似的HTML结构的内容，请转换为适合嵌入向量数据库的Markdown格式，请参照一下要求

        要求：
        
        1.  尽可能保留HTML的语义结构和层级关系，并将其转换为Markdown语法。
        2.  对转换后的Markdown内容进行清洗、优化和结构化处理，使其更适合嵌入向量数据库。
            *   去除无用信息和噪声，例如HTML标签、注释、脚本等。
            *   优化Markdown结构，使其更清晰易读，例如正确使用标题、列表、链接、图片等。
            *   将Markdown内容分块，每块大小适中，包含完整语义信息。
            *   为每个Markdown块添加元数据，如标题、关键词、摘要等。

        3.  最终有内容可输出的Markdown文件应包含以下内容：

            *   标题
            *   摘要
            *   正文（分章节和小节）
            *   链接
            *   图片
            *   元数据（标题、关键词、摘要等）

        4.  请注意：

            *   需要考虑向量数据库的限制，如最大向量维度、chunk大小等。
            *   可以根据实际需求调整处理规则和元数据内容。
    """

    @abstractmethod
    def optimize(self, content: str) -> str:
        """优化内容的抽象方法"""
        pass


class BaichuanOptimizer(ContentOptimizer):
    """使用百川API的内容优化器实现"""

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key or config.baichuan.api_key
        self.api_url = api_url or config.baichuan.api_url

    def optimize(self, content: str) -> str:
        """使用百川API优化内容"""
        if not self.api_key:
            return content

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        data = {
            "model": "Baichuan4-Air",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "temperature": 0.2,
            "stream": False,
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            # 如果API调用失败，返回原始内容
            return content


class XunfeiOptimizer(ContentOptimizer):
    """使用讯飞API的内容优化器实现 Spark Max"""

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key or config.xunfei.api_key
        self.api_url = api_url or config.xunfei.api_url

    def optimize(self, content: str) -> str:
        """使用讯飞API优化内容"""
        if not self.api_key:
            return content

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        data = {
            # 'model': '4.0Ultra',
            "model": "generalv3.5",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "temperature": 0.2,
            "stream": False,
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except Exception as e:
            # 如果API调用失败，返回原始内容
            return content


class OptimizerFactory:
    """优化器工厂类"""

    @staticmethod
    def create_optimizer(optimizer_type: str = "xunfei", **kwargs) -> ContentOptimizer:
        """创建优化器实例"""
        optimizers = {"baichuan": BaichuanOptimizer, "xunfei": XunfeiOptimizer}

        optimizer_class = optimizers.get(optimizer_type)
        if not optimizer_class:
            raise ValueError(f"不支持的优化器类型: {optimizer_type}")

        return optimizer_class(**kwargs)
