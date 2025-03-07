"""
Dify API 客户端实现
按照 https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api
实现知识库维护相关接口
"""

import os
from typing import Dict, List, Optional, Union, Any
import os
import json
import logging
import requests
from ..config import (
    BASE_URL as DEFAULT_BASE_URL,
    EMBEDDING_PROVIDER_DICT,
    EMBEDDING_DEFAULT_PROCESS_RULE,
    EMBEDDING_PROCESS_PARENT_RULE,
    AttachmentSizeLimit,
)


class DifyClient:
    """Dify API 客户端"""

    def __init__(
        self,
        api_key: str,
        base_url: str = None,
        logger: Optional[logging.Logger] = None,
    ):
        """
        初始化 Dify 客户端

        Args:
            api_key: API密钥
            base_url: API基础URL
        """
        self.api_key = api_key
        self.base_url = base_url or DEFAULT_BASE_URL
        # 移除末尾斜杠
        self.base_url = self.base_url.rstrip("/")
        if "#" in self.base_url:  # 移除注释
            self.base_url = self.base_url.split("#")[0].strip()

        self.logger = logger or logging.getLogger(__name__)
        self.logger.info("DifyClient 初始化:")
        self.logger.info(f"Base URL: {self.base_url}")
        self.logger.info(f"API Key: {api_key}")

        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Accept": "*/*",
            "Accept-Encoding": "gzip, deflate, br",
        }

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        发送API请求

        Args:
            method: HTTP方法（GET, POST等）
            endpoint: API端点
            **kwargs: 请求参数

        Returns:
            Dict: 响应数据
        """
        url = f"{self.base_url}{endpoint}"
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Accept": "application/json",
        }

        # 合并自定义headers
        if "headers" in kwargs:
            headers.update(kwargs.pop("headers"))

        self.logger.info(f"Making {method} request to {url}")

        # 处理不同类型的请求体
        if "json" in kwargs:
            # 标准JSON请求，使用json参数
            headers["Content-Type"] = "application/json"
            data = None
            json_data = kwargs.pop("json")
            files = None
        elif "files" in kwargs:
            # 处理文件上传
            data = kwargs.pop("data", {}) if "data" in kwargs else {}
            files = kwargs.pop("files")

            json_data = None
        else:
            # 默认为无请求体
            data = kwargs.pop("data", None) if "data" in kwargs else None
            json_data = None
            files = None

        # 记录请求信息
        self.logger.debug(f"Headers: {headers}")
        if json_data:
            self.logger.info(f"JSON Data: {json.dumps(json_data, indent=4)}")

        # 发送请求
        try:
            response = requests.request(
                method, url, headers=headers, json=json_data, data=data, files=files, **kwargs
            )

            # 强制响应使用UTF-8编码
            response.encoding = "utf-8"

            # 检查响应状态
            response.raise_for_status()

            # 尝试解析JSON响应
            try:
                # 先记录原始响应
                result = response.json()
            except ValueError:
                # 如果不是有效的JSON，返回文本内容
                result = {"text": response.text}

            self.logger.debug(f"Response: {result}")
            return result

        except requests.exceptions.RequestException as e:
            self.logger.error(f"Request failed: {e}")
            # 尝试提取错误响应
            error_response = {}
            try:
                if hasattr(e, "response") and e.response is not None:
                    error_response = e.response.json()
            except ValueError:
                if hasattr(e, "response") and e.response is not None:
                    error_response = {"text": e.response.text}

            self.logger.error(f"Error response: {error_response}")
            # 重新抛出异常并附加响应信息
            raise RuntimeError(f"API request failed: {str(e)}") from e

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
            "doc_form": "hierarchical_model",  # hierarchical_model  qa_model
            "doc_language": "Chinese",
            # 自动规则处理
            "process_rule": EMBEDDING_PROCESS_PARENT_RULE,
            "retrieval_model": {
                "reranking_enable": True,
                "search_method": "hybrid_search",
                "reranking_mode": "reranking_model",
                "top_k": 5,
                "reranking_model": EMBEDDING_PROVIDER_DICT["reranking_model"],
                "score_threshold_enabled": False,
                "score_threshold": 0.5,
            },
            "weight_type": "customized",
            "vector_setting": {
                "vector_weight": 0.7,
                "embedding_provider_name": EMBEDDING_PROVIDER_DICT["embedding_model_provider"],
                "embedding_model_name": EMBEDDING_PROVIDER_DICT["embedding_model"],
            },
            "keyword_setting": {"keyword_weight": 0.3},
            "embedding_model": EMBEDDING_PROVIDER_DICT["embedding_model"],
            "embedding_model_provider": EMBEDDING_PROVIDER_DICT["embedding_model_provider"],
        }

        # 获取文件名，直接使用原始文件名
        filename = os.path.basename(file_path)

        # 通过文件类型限制上传的文件类型的大小，超过则跳过本次上传
        file_type = filename.split(".")[-1].lower()
        file_size_limit = AttachmentSizeLimit.get(file_type, None)
        if file_size_limit is not None and os.path.getsize(file_path) > file_size_limit:
            self.logger.error(
                f"File size exceeds limit: {os.path.getsize(file_path)} > {file_size_limit}"
            )
            raise ValueError(f"File size exceeds limit: {file_size_limit}")

        # 准备请求数据
        data = {"data": json.dumps(rule_config, ensure_ascii=False)}

        # 打开文件并发送请求
        with open(file_path, "rb") as file_obj:
            files = {"file": (filename, file_obj, "application/octet-stream")}
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
