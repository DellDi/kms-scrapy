"""
Dify API 客户端实现
按照 https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api
实现知识库维护相关接口
"""
import os
from typing import Dict, List, Optional, Union, Any
import os
import requests
from urllib.parse import urljoin

class DifyAPIError(Exception):
    """Dify API 异常"""
    pass

class DifyClient:
    """Dify API 客户端"""

    def __init__(self, api_key: str, base_url: str = "https://cloud.dify.ai/console/api"):
        """
        初始化 Dify 客户端

        Args:
            api_key: Dify API 密钥
            base_url: API 基础 URL
        """
        self.api_key = api_key
        self.base_url = base_url.rstrip('/')
        if '#' in self.base_url:  # 移除注释
            self.base_url = self.base_url.split('#')[0].strip()
            
        print(f"\nDifyClient 初始化:")
        print(f"Base URL: {self.base_url}")
        print(f"API Key: {'*' * 20}{api_key[-4:]}")
        
        self.session = requests.Session()
        self.session.headers.update({
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json;charset=utf-8",
            "Accept": "application/json"
        })

    def _make_request(self, method: str, endpoint: str, **kwargs) -> Dict:
        """
        发送 API 请求

        Args:
            method: HTTP 方法
            endpoint: API 端点
            **kwargs: 请求参数

        Returns:
            Dict: API 响应数据
        """
        # 确保 endpoint 不以斜杠开头，避免 urljoin 移除 base_url 的路径部分
        endpoint = endpoint.lstrip('/')
        url = urljoin(self.base_url + '/', endpoint)
        print(f"\n处理url: {url}")
        # 添加编码处理
        if 'json' in kwargs:
            try:
                # 确保所有 JSON 数据都是 UTF-8 编码
                import json
                kwargs['data'] = json.dumps(kwargs.pop('json'), ensure_ascii=False).encode('utf-8')
                kwargs['headers'] = {
                    **kwargs.get('headers', {}),
                    'Content-Type': 'application/json; charset=utf-8'
                }
            except Exception as e:
                raise DifyAPIError(f"JSON 编码失败: {str(e)}") from e

        try:
            response = self.session.request(method, url, **kwargs)
            response.encoding = 'utf-8'  # 确保响应使用 UTF-8 编码
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            error_msg = "API 请求失败"
            try:
                if hasattr(e.response, 'content'):
                    # 尝试解码错误响应
                    error_content = e.response.content.decode('utf-8')
                    try:
                        error_detail = json.loads(error_content)
                        error_msg = f"{error_msg}: {json.dumps(error_detail, ensure_ascii=False)}"
                    except:
                        error_msg = f"{error_msg}: {error_content}"
            except:
                error_msg = f"{error_msg}: {str(e)}"
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
        data = {
            "name": name,
            "description": description
        }
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
        获取数据集列表

        Args:
            page: 页码
            limit: 每页数量

        Returns:
            Dict: 数据集列表和分页信息

        文档：https://docs.dify.ai/zh-hans/guides/knowledge-base/knowledge-and-documents-maintenance/maintain-dataset-via-api#%E8%8E%B7%E5%8F%96%E6%95%B0%E6%8D%AE%E9%9B%86%E5%88%97%E8%A1%A8
        """
        params = {
            "page": page,
            "limit": limit
        }
        return self._make_request("GET", "/datasets", params=params)

    def create_document(
        self,
        dataset_id: str,
        doc_data: Union[str, Dict[str, Any]],
        doc_type: str = "text",
        doc_name: Optional[str] = None,
        indexing_technique: str = "high_quality"
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
        if doc_type not in ['text', 'qa_pair']:
            raise ValueError("doc_type must be either 'text' or 'qa_pair'")

        if indexing_technique not in ['high_quality', 'economy']:
            raise ValueError("indexing_technique must be either 'high_quality' or 'economy'")

        data = {
            "indexing_technique": indexing_technique,
            "doc_type": doc_type
        }

        if doc_type == 'text':
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

        return self._make_request(
            "POST",
            f"/datasets/{dataset_id}/documents",
            json=data
        )

    def upload_file(
        self,
        dataset_id: str,
        file_path: str,
        indexing_technique: str = "high_quality",
        process_rule: str = "custom"
    ) -> Dict:
        """
        上传文件作为文档

        Args:
            dataset_id: 数据集 ID
            file_path: 本地文件路径
            indexing_technique: 索引技术，'high_quality' 或 'economy'
            process_rule: 处理规则，'custom' 或 'advanced'

        Returns:
            Dict: 上传结果
        """
        if indexing_technique not in ['high_quality', 'economy']:
            raise ValueError("indexing_technique must be either 'high_quality' or 'economy'")
        
        if process_rule not in ['custom', 'advanced']:
            raise ValueError("process_rule must be either 'custom' or 'advanced'")

        with open(file_path, 'rb') as f:
            files = {
                'file': (os.path.basename(file_path), f, 'application/octet-stream')
            }
            data = {
                'indexing_technique': indexing_technique,
                'process_rule': process_rule
            }
            
            return self._make_request(
                "POST",
                f"/datasets/{dataset_id}/documents/upload",
                data=data,
                files=files
            )

    def upload_multiple_files(
        self,
        dataset_id: str,
        file_paths: List[str],
        indexing_technique: str = "high_quality",
        process_rule: str = "custom"
    ) -> List[Dict]:
        """
        批量上传多个文件作为文档

        Args:
            dataset_id: 数据集 ID
            file_paths: 本地文件路径列表
            indexing_technique: 索引技术，'high_quality' 或 'economy'
            process_rule: 处理规则，'custom' 或 'advanced'

        Returns:
            List[Dict]: 每个文件的上传结果
        """
        results = []
        for file_path in file_paths:
            try:
                result = self.upload_file(dataset_id, file_path, indexing_technique, process_rule)
                results.append(result)
                print(f"成功上传文件: {os.path.basename(file_path)}")
            except Exception as e:
                print(f"上传文件失败 {os.path.basename(file_path)}: {str(e)}")
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
        return self._make_request(
            "GET",
            f"/datasets/{dataset_id}/documents/{document_id}"
        )

    def list_documents(
        self,
        dataset_id: str,
        page: int = 1,
        limit: int = 20,
        keyword: Optional[str] = None
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
        params = {
            "page": page,
            "limit": limit
        }
        if keyword:
            params["keyword"] = keyword

        return self._make_request(
            "GET",
            f"/datasets/{dataset_id}/documents",
            params=params
        )

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
        return self._make_request(
            "DELETE",
            f"/datasets/{dataset_id}/documents/{document_id}"
        )    
       