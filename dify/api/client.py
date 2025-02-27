"""
Dify API 客户端实现
按照 https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api
实现知识库维护相关接口
"""

import os
from typing import Dict, List, Optional, Union, Any
import os
from scrapy.http import Request
import logging
from urllib.parse import urljoin
import aiohttp
import asyncio
import json
from ..config import BASE_URL as DEFAULT_BASE_URL


class DifyAPIError(Exception):
    """Dify API 异常"""

    pass


class DifyClient:
    """Dify API 客户端"""

    def __init__(self, api_key: str, base_url: str = DEFAULT_BASE_URL):
        """
        初始化 Dify 客户端

        Args:
            api_key: Dify API 密钥
            base_url: API 基础 URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip("/")
        if "#" in self.base_url:  # 移除注释
            self.base_url = self.base_url.split("#")[0].strip()

        self.logger = logging.getLogger(__name__)
        self.logger.info("DifyClient 初始化:")
        self.logger.info(f"Base URL: {self.base_url}")
        self.logger.info(f"API Key: {api_key}")

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        # 确保 endpoint 不以斜杠开头
        endpoint = endpoint.lstrip("/")
        url = urljoin(self.base_url + "/", endpoint)

        try:
            # 设置请求头，添加UTF-8编码
            headers = self.headers.copy()

            # 确保JSON数据使用UTF-8编码
            if "json" in kwargs:
                data = json.dumps(kwargs.pop("json"), ensure_ascii=False).encode("utf-8")
                headers["Content-Type"] = "application/json; charset=utf-8"
            elif "files" in kwargs:
                # 处理文件上传，使用FormData格式
                data = aiohttp.FormData()
                # 如果有data字段，作为普通字段添加到FormData中
                if "data" in kwargs:
                    form_data = kwargs.pop("data")
                    if isinstance(form_data, dict):
                        for key, value in form_data.items():
                            if isinstance(value, str):
                                data.add_field(key, value)
                            else:
                                data.add_field(key, json.dumps(value, ensure_ascii=False))

                # 添加文件字段
                for key, file_tuple in kwargs["files"].items():
                    filename, file_obj, content_type = file_tuple
                    data.add_field(key, file_obj, filename=filename, content_type=content_type)
                kwargs.pop("files")
            else:
                data = None

            async def make_request():
                async with aiohttp.ClientSession() as session:
                    self.logger.info(
                        f"Making {method} request to {url},kwargs:{kwargs},headers:{headers}"
                    )
                    async with session.request(
                        method=method,
                        url=url,
                        headers=headers,
                        data=data,
                        params=kwargs.get("params"),
                        **{k: v for k, v in kwargs.items() if k not in ["json", "params", "data"]},
                    ) as response:
                        if response.status != 200:
                            raise DifyAPIError(f"API请求失败: HTTP {response.status}")
                        return await response.json(encoding="utf-8")

            # 运行异步请求
            loop = asyncio.get_event_loop()
            return loop.run_until_complete(make_request())

        except Exception as e:
            error_msg = f"API 请求失败: {str(e)}"
            raise DifyAPIError(error_msg) from e

    def create_dataset(self, name: str, description: str = "") -> Dict:
        """
        创建数据集（知识库）

        Args:
            name: 数据集名称
            description: 数据集描述

        Returns:
            Dict: 创建的数据集信息

        文档：https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api#%E5%88%9B%E5%BB%BA%E6%95%B0%E6%8D%AE%E9%9B%86
        """
        data = {"name": name, "description": description}
        return self._make_request("POST", "/datasets", json=data)

    def get_dataset(self, dataset_id: str) -> Dict:
        """
        获取数据集信息

        Args:
            dataset_id: 数据集 ID

        Returns:
            Dict: 数据集信息

        文档：https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api#%E8%8E%B7%E5%8F%96%E6%95%B0%E6%8D%AE%E9%9B%86%E8%AF%A6%E6%83%85
        """
        return self._make_request("GET", f"/datasets/{dataset_id}")

    def list_datasets(self, page: int = 1, limit: int = 20) -> Dict:
        """
        获取数据库列表

        Args:
            page: 页码
            limit: 每页数量

        文档：https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api#%E8%8E%B7%E5%8F%96%E6%95%B0%E6%8D%AE%E9%9B%86%E5%88%97%E8%A1%A8
        """
        params = {"page": page, "limit": limit}
        return self._make_request("GET", "/datasets", params=params)

    def create_document(
        self,
        dataset_id: str,
        doc_data: Union[str, Dict[str, Any]],
        doc_type: str = "text",
        doc_name: Optional[str] = None,
        indexing_technique: str = "high_quality",
    ) -> Dict:
        """
        创建文档

        Args:
            dataset_id: 数据集 ID
            doc_data: 文档内容，可以是文本或结构化数据
            doc_type: 文档类型，'text' 或 'qa_pair'
            doc_name: 文档名称（可选）
            indexing_technique: 索引技术，'high_quality' 或 'economy'

        Returns:
            Dict: 创建的文档信息

        文档：https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api#%E5%88%9B%E5%BB%BA%E6%96%87%E6%A1%A3
        """
        if doc_type not in ["text", "qa_pair"]:
            raise ValueError("doc_type must be either 'text' or 'qa_pair'")

        if indexing_technique not in ["high_quality", "economy"]:
            raise ValueError("indexing_technique must be either 'high_quality' or 'economy'")

        data = {"indexing_technique": indexing_technique, "doc_type": doc_type}

        if doc_type == "text":
            if isinstance(doc_data, str):
                data["content"] = doc_data
            else:
                raise ValueError("For doc_type 'text', doc_data must be a string")
        else:  # qa_pair
            if isinstance(doc_data, dict):
                data.update(doc_data)
            else:
                raise ValueError("For doc_type 'qa_pair', doc_data must be a dictionary")

        if doc_name:
            data["name"] = doc_name

        return self._make_request("POST", f"/datasets/{dataset_id}/documents", json=data)

    def upload_file(
        self,
        dataset_id: str,
        file_path: str,
        indexing_technique: str = "high_quality",
        segmentation: Optional[Dict[str, Union[str, int]]] = None,
        retrieval_model: Optional[str] = None,
    ) -> Dict:
        """
        上传文件作为文档

        Args:
            dataset_id: 数据集 ID
            file_path: 本地文件路径
            indexing_technique: 索引技术，'high_quality' 或 'economy'
            segmentation: 分段设置，包含separator和max_tokens字段
            retrieval_model: 检索模式

        Returns:
            Dict: 上传结果
        """
        if indexing_technique not in ["high_quality", "economy"]:
            raise ValueError("indexing_technique must be either 'high_quality' or 'economy'")

        # 构建处理规则配置
        rule_config = {
            "indexing_technique": indexing_technique,
            "doc_form": "text_model",
            # 自动规则处理
            "process_rule": {
                "mode": "automatic",
            },
            "retrieval_model": {
                "search_method": "hybrid_search",
                "reranking_enable": True,
                "top_k": 5,
                "reranking_model": {
                    "reranking_provider_name": "tongyi",
                    "reranking_model_name": "gte-rerank",
                },
                "score_threshold_enabled": False,
            },
            "embedding_model": "text-embedding-v3",
            "embedding_model_provider": "tongyi",
        }

        with open(file_path, "rb") as f:
            files = {"file": (os.path.basename(file_path), f, "application/octet-stream")}
            # 将规则配置转换为JSON字符串
            data = {"data": json.dumps(rule_config)}

            return self._make_request(
                "POST", f"/datasets/{dataset_id}/document/create-by-file", data=data, files=files
            )

    def upload_multiple_files(
        self,
        dataset_id: str,
        file_paths: List[str],
        indexing_technique: str = "high_quality",
    ) -> List[Dict]:
        """
        批量上传多个文件作为文档

        Args:
            dataset_id: 数据集 ID
            file_paths: 本地文件路径列表
            indexing_technique: 索引技术，'high_quality' 或 'economy'
        Returns:
            List[Dict]: 每个文件的上传结果
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.upload_file(dataset_id, file_path, indexing_technique)
                results.append(result)
                self.logger.info(f"成功上传文件: {os.path.basename(file_path)}")

            except Exception as e:
                self.logger.error(f"上传文件失败 {os.path.basename(file_path)}: {str(e)}")
        return results

    def get_document(self, dataset_id: str, document_id: str) -> Dict:
        """
        获取文档详情

        Args:
            dataset_id: 数据集 ID
            document_id: 文档 ID

        Returns:
            Dict: 文档信息

        文档：https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api#%E8%8E%B7%E5%8F%96%E6%96%87%E6%A1%A3%E8%AF%A6%E6%83%85
        """
        return self._make_request("GET", f"/datasets/{dataset_id}/documents/{document_id}")

    def list_documents(
        self, dataset_id: str, page: int = 1, limit: int = 20, keyword: Optional[str] = None
    ) -> Dict:
        """
        获取文档列表

        Args:
            dataset_id: 数据集 ID
            page: 页码
            limit: 每页数量
            keyword: 搜索关键词（可选）

        Returns:
            Dict: 文档列表和分页信息

        文档：https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api#%E8%8E%B7%E5%8F%96%E6%96%87%E6%A1%A3%E5%88%97%E8%A1%A8
        """
        params = {"page": page, "limit": limit}
        if keyword:
            params["keyword"] = keyword

        return self._make_request("GET", f"/datasets/{dataset_id}/documents", params=params)

    def delete_document(self, dataset_id: str, document_id: str) -> Dict:
        """
        删除文档

        Args:
            dataset_id: 数据集 ID
            document_id: 文档 ID

        Returns:
            Dict: 删除结果

        文档：https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api#%E5%88%A0%E9%99%A4%E6%96%87%E6%A1%A3
        """
        return self._make_request("DELETE", f"/datasets/{dataset_id}/documents/{document_id}")
