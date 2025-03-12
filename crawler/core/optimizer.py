from abc import ABC, abstractmethod
import textwrap
import re
import json
import requests
import logging
import html2text
from datetime import datetime
from typing import Optional, Generator, Dict, Any, Union
from crawler.core.config import config


class ContentOptimizer(ABC):
    """内容优化器的抽象基类"""

    SYSTEM_PROMPT = f"""
        你是一个智能的语义化提炼分析小助手，我可以帮你提取和优化网页内容。

        <重要>如果得到的内容是空白或者没有任何语义的内容，请直接响应输出```md ```即可。

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
    def optimize(
        self, content: str, stream: bool = False, spiderUrl="", title=""
    ) -> Union[str, Generator[Dict[str, Any], None, None]]:
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
        self.api_url = api_url
        self.model = model
        self.headers = {"Content-Type": "application/json", "Authorization": f"Bearer {api_key}"}

    def process_response(
        self, response: requests.Response, stream: bool = True
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
        self, response: requests.Response
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
                        data = json.loads(line.decode("utf-8").strip())
                    except:
                        # 处理以"data: "开头的SSE格式
                        if line.startswith(b"data: "):
                            data = json.loads(line.decode("utf-8")[6:])
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
                        "choices": [
                            {
                                "delta": {"content": content},
                                "finish_reason": "stop" if is_end else None,
                                "index": 0,
                            }
                        ],
                        "object": "chat.completion.chunk",
                    }

                    if is_end:
                        break
                except json.JSONDecodeError:
                    continue
                except Exception as e:
                    print(f"处理流式响应时出错: {str(e)}")
                    continue

    def get_completion(
        self, messages: list, stream: bool = True, temperature: float = 0.2, **kwargs
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
            **kwargs,
        }

        try:
            response = requests.post(self.api_url, headers=self.headers, json=data, stream=stream)
            response.raise_for_status()
            return self.process_response(response, stream)
        except Exception as e:
            raise Exception(f"API请求失败: {str(e)}")


class StreamingResponseAdapter:
    """讯飞星火API流式响应适配器，转换为OpenAI格式"""

    @staticmethod
    def adapt_streaming_response(
        response: requests.Response,
    ) -> Generator[Dict[str, Any], None, None]:
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
                        "choices": [
                            {
                                "delta": {"content": text},
                                "finish_reason": "stop" if is_end else None,
                                "index": 0,
                            }
                        ],
                        "object": "chat.completion.chunk",
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

    def optimize(
        self,
        content: str,
        stream: bool = False,
    ) -> str:
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

    def optimize(
        self,
        content: str,
        spiderUrl: str = "",
        title: str = "",
        stream: bool = False,
    ) -> Union[str, Generator[Dict[str, Any], None, None]]:
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
                # 添加当前爬虫的url
                return f"{result["choices"][0]["message"]["content"]}\n\n> 原始页面地址：[{spiderUrl}]({spiderUrl})\n\n"

        except Exception as e:
            # 如果API调用失败，返回原始内容
            return content


class OpenAICompatibleOptimizer(ContentOptimizer):
    """通用的OpenAI兼容优化器实现"""

    def __init__(
        self,
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
    ):
        """
        初始化通用优化器

        Args:
            api_key: API密钥
            api_url: API URL
            model: 模型名称
        """
        self.api_key = api_key or config.openai.api_key
        self.api_url = api_url or config.openai.api_url
        self.model = model or config.openai.model

        self.adapter = OpenAICompatibleAdapter(
            api_key=self.api_key, api_url=self.api_url, model=self.model
        )

    def optimize(
        self, content: str, stream: bool = True
    ) -> Union[str, Generator[Dict[str, Any], None, None]]:
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
                temperature=0.2,
            )

            if not stream:
                return result["choices"][0]["message"]["content"]
            return result

        except Exception as e:
            # 如果API调用失败，返回原始内容
            print(f"优化内容时出错: {str(e)}")
            return content


class HTMLToMarkdownOptimizer(ContentOptimizer):
    """使用html2text库的内容优化器实现"""

    def __init__(self):
        self.operator = "@delldi"
        self.logger = logging.getLogger(__name__)
        self.h = html2text.HTML2Text()
        # 基础配置
        self.h.body_width = 0  # 不限制行宽
        self.h.unicode_snob = True  # 使用 unicode 字符
        self.h.bypass_tables = False  # 不跳过表格处理
        self.h.protect_links = True  # 保护链接

        # 格式化配置
        self.h.ignore_links = False  # 保留链接
        self.h.ignore_images = False  # 保留图片
        self.h.ignore_emphasis = False  # 保留强调格式（加粗、斜体）
        self.h.ignore_tables = False  # 保留表格
        self.h.single_line_break = False  # 单行换行
        self.h.mark_code = True  # 标记代码块

        # 标记符号配置
        self.h.ul_item_mark = "-"  # 无序列表标记
        self.h.emphasis_mark = "*"  # 强调标记
        self.h.strong_mark = "**"  # 加粗标记

        # 基础表格配置 - 标准Markdown表格
        self.h.tables = True
        self.h.preserve_tables = True

        # 更美观的表格样式
        self.h.table_border_style = "pipe"

        # 增强表格处理配置
        self.h.table_prefer_style = True
        self.h.skip_internal_links = True
        self.h.pad_tables = True  # 添加表格填充

    def optimize(self, content: str, spiderUrl="", title="") -> str:
        """将HTML内容转换为Markdown格式

        Args:
            content: HTML内容
            spiderUrl: 爬取的原始URL，用于处理相对链接
            title: 文档标题
        Returns:
            str: Markdown格式的文本
        """
        try:
            # 基础HTML清理
            content = content.replace("<br>", "<br/>")
            content = content.replace("<hr>", "<hr/>")

            # 预处理视频标签，将其转换为可被 html2text 处理的链接格式
            video_pattern = r'<video\s+[^>]*src="([^"]+)"[^>]*>(.*?)</video>'

            def video_replacer(match):
                video_src = match.group(1)
                # 提取视频文件名作为链接文本
                video_name = video_src.split('/')[-1]
                return f'<a href="{video_src}">[视频] {video_name}</a>'

            content = re.sub(video_pattern, video_replacer, content, flags=re.DOTALL)

            # 处理 Confluence 风格的相对链接
            if spiderUrl:
                # 提取基础URL（域名部分）
                base_url_match = re.match(r"(https?://[^/]+)", spiderUrl)
                if base_url_match:
                    base_url = base_url_match.group(1)
                    # 将相对路径链接转换为绝对路径
                    content = re.sub(r'href="(/[^"]+)"', f'href="{base_url}\\1"', content)
                    # 同样处理视频的 src 属性
                    content = re.sub(r'src="(/[^"]+)"', f'src="{base_url}\\1"', content)

            # 配置 html2text 转换器的 baseurl
            if spiderUrl:
                base_url_match = re.match(r"(https?://[^/]+)", spiderUrl)
                if base_url_match:
                    self.h.baseurl = base_url_match.group(1)

            # 使用内置转换器处理
            markdown = self.h.handle(content)

            # 简单的后处理
            markdown = markdown.strip()
            markdown = re.sub(r"\n{3,}", "\n\n", markdown)  # 清理多余空行

            # 修复嵌套链接问题 - 处理格式如 [text](http://domain.com/<http://domain.com/path>) 的链接
            markdown = re.sub(r"\[([^\]]+)\]\(([^)]+)<(http[^>]+)>\)", r"[\1](\3)", markdown)

            # 修复视频链接中的嵌套URL问题
            markdown = re.sub(r"\[\[视频\] ([^\]]+)\]\((http[^)]+)<(http[^>]+)>\)", r"[[视频] \1](\3)", markdown)

            # 匹配形如 ![图片名](链接) 的模式，将其转换为[图片名](链接)
            markdown = re.sub(r"(\s+)!\[(.*?)\](\(.*?\))", r"\1[\2]\3", markdown)

            # 处理空的链接文本，使用链接URL作为链接文本
            def empty_link_replacer(match):
                url = match.group(1)
                # 从URL中提取文件名或最后一部分作为链接文本
                url_text = url.strip("()")
                filename = url_text.split("/")[-1].split("?")[0]  # 提取文件名并去除查询参数
                return f"[{filename}]{url}"

            markdown = re.sub(r"\[\](\([^)]+\))", empty_link_replacer, markdown)

            # 后处理 Confluence 风格链接，将 [链接文本](/pages/viewpage.action?pageId=xxx) 转换为 [链接文本](完整URL)
            if spiderUrl and base_url_match:
                base_url = base_url_match.group(1)
                # 匹配 Markdown 格式的相对链接
                markdown = re.sub(r"\[([^\]]+)\]\((/[^)]+)\)", f"[\\1]({base_url}\\2)", markdown)

            # 后处理添加爬虫说明和时间记录、操作人记录、对应页面地址以md格式输出
            markdown += f"\n\n> 此内容由爬虫自动生成\n"
            markdown += f"> 爬取时间：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
            markdown += f"> 操作人：{self.operator} \n"
            markdown += f"> 原始页面地址：[{spiderUrl}]({spiderUrl}) \n"

            markdown = textwrap.dedent(markdown)

            return markdown.strip()  # 移除首尾多余空白

        except Exception as e:
            self.logger.error(f"HTML转Markdown失败: {str(e)}")
            return content


class OptimizerFactory:
    """优化器工厂类"""

    @staticmethod
    def create_optimizer(
        optimizer_type: str = "html2md",  # 修改默认值为html2md
        api_key: Optional[str] = None,
        api_url: Optional[str] = None,
        model: Optional[str] = None,
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
            "html2md": HTMLToMarkdownOptimizer,  # 添加HTML转Markdown优化器
            "baichuan": BaichuanOptimizer,
            "xunfei": XunfeiOptimizer,
            "compatible": OpenAICompatibleOptimizer,
        }

        optimizer_class = optimizers.get(optimizer_type.lower())
        if not optimizer_class:
            # 如果类型不支持，使用默认的html2md
            logger = logging.getLogger(__name__)
            logger.warning(f"不支持的优化器类型: {optimizer_type}，使用默认的html2md优化器")
            return HTMLToMarkdownOptimizer()

        if optimizer_type == "compatible":
            if not api_key or not api_url:
                raise ValueError("compatible 优化器需要提供 api_key 和 api_url")
            return optimizer_class(api_key, api_url, model or "default")
        elif optimizer_type == "html2md":
            return optimizer_class()
        else:
            return optimizer_class(api_key, api_url)
