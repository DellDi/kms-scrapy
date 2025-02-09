"""
知识库管理模块
负责知识库（数据集）的创建和管理
"""
import re
from typing import Dict, List, Optional, Any
from ..api.client import DifyClient, DifyAPIError

class DatasetManager:
    """数据集管理器"""

    def __init__(self, client: DifyClient, max_docs: int = 100):
        """
        初始化数据集管理器

        Args:
            client: Dify API 客户端
            max_docs: 每个数据集的最大文档数量
        """
        self.client = client
        self.max_docs = max_docs
        self._current_dataset = None
        self._dataset_number = 0

    def initialize(self) -> Dict:
        """
        初始化管理器
        获取或创建数据集

        Returns:
            Dict: 当前使用的数据集信息
        """
        try:
            # 获取数据集列表
            response = self.client.list_datasets()
            datasets = response.get('data', [])

            if not datasets:
                # 没有数据集，创建第一个
                self._dataset_number = 1
                self._current_dataset = self._create_dataset()
            else:
                # 找到最新的数据集
                latest_dataset, number = self._get_latest_dataset(datasets)
                self._dataset_number = number

                # 获取最新数据集的文档列表
                docs_response = self.client.list_documents(latest_dataset["id"])
                doc_count = docs_response.get('total', 0)

                if doc_count >= self.max_docs:
                    # 创建新数据集
                    self._dataset_number += 1
                    self._current_dataset = self._create_dataset()
                else:
                    self._current_dataset = latest_dataset

            return self._current_dataset

        except DifyAPIError as e:
            raise RuntimeError(f"初始化数据集管理器失败: {str(e)}")

    def _get_latest_dataset(self, datasets: List[dict]) -> tuple[Dict, int]:
        """
        从数据集列表中找到最新的数据集和编号

        Args:
            datasets: 数据集列表

        Returns:
            tuple[Dict, int]: (最新数据集信息, 数据集编号)
        """
        pattern = r"kms-(\d+)"
        max_number = 0
        latest_dataset = None

        for dataset in datasets:
            match = re.search(pattern, dataset["name"])
            if match:
                number = int(match.group(1))
                if number > max_number:
                    max_number = number
                    latest_dataset = dataset

        if not latest_dataset:
            raise ValueError("没有找到有效的数据集")

        return latest_dataset, max_number

    def _create_dataset(self) -> Dict:
        """
        创建新的数据集

        Returns:
            Dict: 新创建的数据集信息
        """
        name = f"kms-{self._dataset_number}"
        description = f"知识管理系统文档库 #{self._dataset_number}"
        return self.client.create_dataset(name, description)

    def get_current_dataset(self) -> Dict:
        """
        获取当前使用的数据集

        Returns:
            Dict: 当前数据集信息
        """
        if not self._current_dataset:
            self._current_dataset = self.initialize()
        return self._current_dataset

    def ensure_dataset_capacity(self) -> Dict:
        """
        确保当前数据集有足够容量
        如果当前数据集已满，创建新的数据集

        Returns:
            Dict: 可用的数据集信息
        """
        current_dataset = self.get_current_dataset()
        docs_response = self.client.list_documents(current_dataset["id"])
        doc_count = docs_response.get('total', 0)

        if doc_count >= self.max_docs:
            self._dataset_number += 1
            self._current_dataset = self._create_dataset()
            return self._current_dataset

        return current_dataset

    def create_document(
        self,
        content: str,
        name: Optional[str] = None,
        indexing_technique: str = "high_quality"
    ) -> Dict:
        """
        创建文档，自动处理数据集容量

        Args:
            content: 文档内容
            name: 文档名称（可选）
            indexing_technique: 索引技术，'high_quality' 或 'economy'

        Returns:
            Dict: 创建的文档信息
        """
        dataset = self.ensure_dataset_capacity()
        return self.client.create_document(
            dataset["id"],
            content,
            doc_type="text",
            doc_name=name,
            indexing_technique=indexing_technique
        )

    def batch_create_documents(
        self,
        documents: List[Dict[str, Any]],
        indexing_technique: str = "high_quality"
    ) -> List[Dict]:
        """
        批量创建文档，自动处理数据集容量

        Args:
            documents: 文档列表，每个文档必须包含 content 字段
            indexing_technique: 索引技术，'high_quality' 或 'economy'

        Returns:
            List[Dict]: 创建的文档信息列表
        """
        results = []
        current_batch = []

        for doc in documents:
            if not isinstance(doc, dict) or 'content' not in doc:
                raise ValueError("每个文档必须是字典类型且包含 'content' 字段")

            # 获取当前数据集状态
            current_dataset = self.get_current_dataset()
            docs_response = self.client.list_documents(current_dataset["id"])
            doc_count = docs_response.get('total', 0)

            # 检查是否需要新建数据集
            if doc_count + len(current_batch) >= self.max_docs:
                # 上传当前批次
                if current_batch:
                    result = self.client.batch_create_documents(
                        current_dataset["id"],
                        current_batch,
                        indexing_technique
                    )
                    results.extend(result.get('data', []))
                    current_batch = []

                # 创建新数据集
                self._dataset_number += 1
                self._current_dataset = self._create_dataset()

            # 添加到当前批次
            current_batch.append(doc)

            # 如果批次达到一定大小，就上传
            if len(current_batch) >= 50:  # 假设每批50个文档
                result = self.client.batch_create_documents(
                    self._current_dataset["id"],
                    current_batch,
                    indexing_technique
                )
                results.extend(result.get('data', []))
                current_batch = []

        # 上传剩余的文档
        if current_batch:
            result = self.client.batch_create_documents(
                self._current_dataset["id"],
                current_batch,
                indexing_technique
            )
            results.extend(result.get('data', []))

        return results