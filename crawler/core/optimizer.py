from abc import ABC, abstractmethod
import json
import requests
from typing import Optional
from .config import config

class ContentOptimizer(ABC):
    """内容优化器的抽象基类"""
    SYSTEM_PROMPT = f'你是一个专业的文档优化助手，需要对输入的文档内容进行结构化处理. 使其更加清晰易读.阻止大块内容粘连在一起,保证内容、层级有序、段落分明/视觉工整，响应成一个良好的md格式的返回输出(充分利用md语法的特性大纲、标题、序号、表格、加粗,引用,分层等常用的md语法).2.如果内容本身是空白的，则返回空白.'
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

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
            'model': 'Baichuan4-Air',
            'messages': [
                {
                    'role': 'system',
                    'content': self.SYSTEM_PROMPT
                },
                {
                    'role': 'user',
                    'content': content
                }
            ],
            'temperature': 0.2,
            'stream': False
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
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

        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.api_key}'
        }

        data = {
            # 'model': '4.0Ultra',
            'model': 'generalv3.5',
            'messages': [
                {
                    'role': 'system',
                    'content': self.SYSTEM_PROMPT
                },
                {
                    'role': 'user',
                    'content': content
                }
            ],
            'stream': False
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            # 如果API调用失败，返回原始内容
            return content

class OptimizerFactory:
    """优化器工厂类"""
    
    @staticmethod
    def create_optimizer(optimizer_type: str = 'xunfei', **kwargs) -> ContentOptimizer:
        """创建优化器实例"""
        optimizers = {
            'baichuan': BaichuanOptimizer,
            'xunfei': XunfeiOptimizer
        }

        optimizer_class = optimizers.get(optimizer_type)
        if not optimizer_class:
            raise ValueError(f'不支持的优化器类型: {optimizer_type}')

        return optimizer_class(**kwargs)