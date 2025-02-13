from abc import ABC, abstractmethod
import json
import requests
from typing import Optional, Generator, Dict, Any, Union
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
    def optimize(self, content: str, stream: bool = False) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """优化内容的抽象方法"""
        pass


class OpenAICompatibleAdapter:
    """通用OpenAI兼容适配器，支持任何符合OpenAI接口格式的API"""

    def __init__(self, api_key: str, api_url: str, model: str = "default"):
        """
        初始化OpenAI兼容适配器
        
        Args:
            api_key: API密钥
            api_url: API端点URL
            model: 模型名称，默认为"default"
        """
        self.api_key = api_key
        self.api_url = api_url.rstrip('/')
        self.model = model
        self.headers = {
            "Content-Type": "application/json",
            "Authorization": f"Bearer {api_key}"
        }

    def process_response(
        self, 
        response: requests.Response, 
        stream: bool = True
    ) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        处理API响应
        
        Args:
            response: requests.Response对象
            stream: 是否使用流式响应
            
        Returns:
            如果stream=True，返回响应生成器
            如果stream=False，返回完整响应
        """
        if stream:
            return self._handle_streaming_response(response)
        return response.json()

    def _handle_streaming_response(
        self, 
        response: requests.Response
    ) -> Generator[Dict[str, Any], None, None]:
        """
        处理流式响应
        
        Args:
            response: requests.Response对象
            
        Yields:
            Dict: OpenAI格式的响应块
        """
        for line in response.iter_lines():
            if line:
                try:
                    # 支持多种响应格式
                    try:
                        data = json.loads(line.decode('utf-8').strip())
                    except:
                        # 处理以"data: "开头的SSE格式
                        if line.startswith(b'data: '):
                            data = json.loads(line.decode('utf-8')[6:])
                        else:
                            continue

                    # 如果已经是OpenAI格式，直接yield
                    if "choices" in data and isinstance(data["choices"], list):
                        yield data
                        continue

                    # 否则转换为OpenAI格式
                    content = ""
                    is_end = False

                    # 处理不同的响应格式
                    if "payload" in data:  # 讯飞格式
                        content = data.get("payload", {}).get("choices", [{}])[0].get("text", "")
                        is_end = data.get("header", {}).get("status") == 2
                    else:  # 其他格式，根据实际情况扩展
                        content = data.get("content", "")
                        is_end = data.get("end", False)

                    yield {
                        "choices": [{
                            "delta": {
                                "content": content
                            },
                            "finish_reason": "stop" if is_end else None,
                            "index": 0
                        }],
                        "object": "chat.completion.chunk"
                    }

                    if is_end:
                        break
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"处理流式响应时出错: {str(e)}")
                    continue

    def get_completion(
        self,
        messages: list,
        stream: bool = True,
        temperature: float = 0.2,
        **kwargs
    ) -> Union[Dict[str, Any], Generator[Dict[str, Any], None, None]]:
        """
        获取完成结果
        
        Args:
            messages: 消息列表
            stream: 是否使用流式响应，默认为True
            temperature: 温度参数
            **kwargs: 其他参数
            
        Returns:
            如果stream=True，返回响应生成器
            如果stream=False，返回完整响应
        """
        data = {
            "model": self.model,
            "messages": messages,
            "temperature": temperature,
            "stream": stream,
            **kwargs
        }

        try:
            response = requests.post(
                self.api_url,
                headers=self.headers,
                json=data,
                stream=stream
            )
            response.raise_for_status()
            return self.process_response(response, stream)
        except Exception as e:
            raise Exception(f"API请求失败: {str(e)}")


class StreamingResponseAdapter:
    """讯飞星火API流式响应适配器，转换为OpenAI格式"""
    
    @staticmethod
    def adapt_streaming_response(response: requests.Response) -> Generator[Dict[str, Any], None, None]:
        """
        将讯飞星火API的流式响应转换为OpenAI格式
        
        Args:
            response: requests.Response对象
        
        Yields:
            Dict: OpenAI格式的响应块
        """
        for line in response.iter_lines():
            if line:
                try:
                    # 解析讯飞API响应
                    xunfei_data = json.loads(line)
                    
                    # 检查是否是最后一条消息
                    is_end = xunfei_data.get("header", {}).get("status") == 2
                    
                    # 获取文本内容
                    text = xunfei_data.get("payload", {}).get("choices", [{}])[0].get("text", "")
                    
                    # 转换为OpenAI格式
                    yield {
                        "choices": [{
                            "delta": {
                                "content": text
                            },
                            "finish_reason": "stop" if is_end else None,
                            "index": 0
                        }],
                        "object": "chat.completion.chunk"
                    }
                    
                    if is_end:
                        break
                except json.JSONDecodeError:
                    continue


class BaichuanOptimizer(ContentOptimizer):
    """使用百川API的内容优化器实现"""

    def __init__(self, api_key: Optional[str] = None, api_url: Optional[str] = None):
        self.api_key = api_key or config.baichuan.api_key
        self.api_url = api_url or config.baichuan.api_url

    def optimize(self, content: str, stream: bool = False) -> str:
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
        self.adapter = StreamingResponseAdapter()

    def optimize(self, content: str, stream: bool = False) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """
        使用讯飞API优化内容
        
        Args:
            content: 要优化的内容
            stream: 是否使用流式响应
            
        Returns:
            如果stream=False，返回优化后的内容字符串
            如果stream=True，返回一个生成器，产生OpenAI格式的流式响应
        """
        if not self.api_key:
            return content

        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.api_key}"}

        data = {
            "model": "generalv3.5",
            "messages": [
                {"role": "system", "content": self.SYSTEM_PROMPT},
                {"role": "user", "content": content},
            ],
            "temperature": 0.2,
            "stream": stream,
        }

        try:
            response = requests.post(self.api_url, headers=headers, json=data, stream=stream)
            response.raise_for_status()
            
            if stream:
                return self.adapter.adapt_streaming_response(response)
            else:
                result = response.json()
                return result["choices"][0]["message"]["content"]
                
        except Exception as e:
            # 如果API调用失败，返回原始内容
            return content


class OpenAICompatibleOptimizer(ContentOptimizer):
    """通用的OpenAI兼容优化器实现"""

    def __init__(self, api_key: str, api_url: str, model: str = "default"):
        """
        初始化通用优化器
        
        Args:
            api_key: API密钥
            api_url: API端点URL
            model: 模型名称
        """
        self.adapter = OpenAICompatibleAdapter(api_key, api_url, model)

    def optimize(self, content: str, stream: bool = True) -> Union[str, Generator[Dict[str, Any], None, None]]:
        """
        使用通用适配器优化内容
        
        Args:
            content: 要优化的内容
            stream: 是否使用流式响应，默认为True
            
        Returns:
            如果stream=False，返回优化后的内容字符串
            如果stream=True，返回一个生成器，产生OpenAI格式的流式响应
        """
        try:
            result = self.adapter.get_completion(
                messages=[
                    {"role": "system", "content": self.SYSTEM_PROMPT},
                    {"role": "user", "content": content},
                ],
                stream=stream,
                temperature=0.2
            )
            
            if not stream:
                return result["choices"][0]["message"]["content"]
            return result
                
        except Exception as e:
            # 如果API调用失败，返回原始内容
            print(f"优化内容时出错: {str(e)}")
            return content


class OptimizerFactory:
    """优化器工厂类"""

    @staticmethod
    def create_optimizer(
        optimizer_type: str = "xunfei",
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
        **kwargs
    ) -> ContentOptimizer:
        """
        创建优化器实例
        
        Args:
            optimizer_type: 优化器类型
            api_key: API密钥（可选）
            api_url: API URL（可选）
            model: 模型名称（可选）
            **kwargs: 其他参数
            
        Returns:
            ContentOptimizer: 优化器实例
        """
        optimizers = {
            "baichuan": BaichuanOptimizer,
            "xunfei": XunfeiOptimizer,
            "compatible": OpenAICompatibleOptimizer
        }

        optimizer_class = optimizers.get(optimizer_type)
        if not optimizer_class:
            raise ValueError(f"不支持的优化器类型: {optimizer_type}")

        if optimizer_type == "compatible":
            if not api_key or not api_url:
                raise ValueError("compatible 优化器需要提供 api_key 和 api_url")
            return optimizer_class(api_key, api_url, model or "default")
            
        return optimizer_class(api_key, api_url)
