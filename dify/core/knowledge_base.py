"""知识库管理模块
负责知识库（数据集）的创建和管理
"""
import os
import re
import logging
from typing import Dict, List, Optional, Any
from ..api.client import DifyClient, DifyAPIError
from ..config import MAX_DOCS_PER_DATASET, DATASET_NAME_PREFIX, DATASET_NAME_PATTERN

class DatasetManager:
    """数据集管理器"""

    def __init__(self, client: DifyClient, max_docs: int = MAX_DOCS_PER_DATASET):
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
        self.logger = logging.getLogger(__name__)

    def initialize(self) -> Dict:
        """
        初始化管理器
        获取或创建数据集

        Returns:
            Dict: 当前使用的数据集信息
        """
        try:
            self.logger.info("开始获取数据集列表...111")
            # 获取数据集列表
            response = self.client.list_datasets()

            datasets = response.get('data', [])
            self.logger.info(f"找到 {len(datasets)} 个数据集")

            if not datasets:
                self.logger.info("没有找到数据集，创建第一个...")
                # 没有数据集，创建第一个
                self._dataset_number = 1
                self._current_dataset = self._create_dataset()
                self.logger.info(f"已创建新数据集: {self._current_dataset['name']}")
            else:
                self.logger.info("处理现有数据集...")
                # 找到最新的数据集
                latest_dataset, number = self._get_latest_dataset(datasets)
                self._dataset_number = number

                if latest_dataset:
                    self.logger.info(f"找到最新数据集: {latest_dataset['name']}")
                    # 获取最新数据集的文档列表
                    docs_response = self.client.list_documents(latest_dataset["id"])
                    doc_count = docs_response.get('total', 0)
                    self.logger.info(f"当前数据集文档数量: {doc_count}/{self.max_docs}")

                    if doc_count >= self.max_docs:
                        self.logger.info("数据集已满，创建新数据集...")
                        # 创建新数据集
                        self._dataset_number += 1
                        self._current_dataset = self._create_dataset()
                        self.logger.info(f"已创建新数据集: {self._current_dataset['name']}")
                    else:
                        self._current_dataset = latest_dataset
                else:
                    self.logger.info("没有找到有效数据集，创建新数据集...")
                    self._dataset_number = 1
                    self._current_dataset = self._create_dataset()
                    self.logger.info(f"已创建新数据集: {self._current_dataset['name']}")

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
        max_number = 0
        latest_dataset = None

        for dataset in datasets:
            match = re.search(DATASET_NAME_PATTERN, dataset["name"])
            if match:
                number = int(match.group(1))
                if number > max_number:
                    max_number = number
                    latest_dataset = dataset

        if not latest_dataset:
            # 如果没有找到任何数据集，返回 None 和 0
            return None, 0

        return latest_dataset, max_number

    def _create_dataset(self) -> Dict:
        """
        创建新的数据集

        Returns:
            Dict: 新创建的数据集信息
        """
        name = f"{DATASET_NAME_PREFIX}-{self._dataset_number}"
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

    def upload_files(
        self,
        file_paths: List[str],
        indexing_technique: str = "high_quality",
        process_rule: str = "custom"
    ) -> List[Dict]:
        """
        上传文件，自动处理数据集容量

        Args:
            file_paths: 文件路径列表
            indexing_technique: 索引技术，'high_quality' 或 'economy'
            process_rule: 处理规则，'custom' 或 'advanced'

        Returns:
            List[Dict]: 上传的文档信息列表
        """
        results = []

        for file_path in file_paths:
            # 获取当前数据集状态
            current_dataset = self.get_current_dataset()
            docs_response = self.client.list_documents(current_dataset["id"])
            doc_count = docs_response.get('total', 0)

            # 检查是否需要新建数据集
            if doc_count >= self.max_docs:
                # 创建新数据集
                self._dataset_number += 1
                self._current_dataset = self._create_dataset()
                self.logger.info(f"创建新数据集: {self._current_dataset['name']}")

            try:
                # 上传文件
                result = self.client.upload_file(
                    self._current_dataset["id"],
                    file_path,
                    indexing_technique,
                    process_rule
                )
                results.append(result)
                self.logger.info(f"成功上传文件: {os.path.basename(file_path)}")
            except Exception as e:
                self.logger.info(f"上传文件失败 {os.path.basename(file_path)}: {str(e)}")

        return results
