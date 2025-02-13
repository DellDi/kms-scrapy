"""
示例：使用 Dify API 上传文档到数据集
"""
import os
from typing import Dict, List
import json
from pathlib import Path
from dotenv import load_dotenv

from dify import DifyClient, DatasetManager

# 加载环境变量
load_dotenv()

def upload_to_dify():
    """上传文档到 Dify 数据集"""

    # 获取配置
    api_key = os.getenv('DIFY_API_KEY')
    base_url = os.getenv('DIFY_BASE_URL', 'https://api.dify.ai/v1')
    
    if not api_key:
        raise ValueError("请设置 DIFY_API_KEY 环境变量")

    # 初始化 Dify 客户端
    client = DifyClient(api_key, base_url)

    # documents
    dataset_manager = DatasetManager(client)

    # 初始化或获取当前数据集
    current_dataset = dataset_manager.initialize()
    print(f"当前使用数据集: {current_dataset['name']}")

    # 示例：读取 output 目录中的内容并上传
    def process_output_directory() -> None:
        """处理 output 目录中的文档"""
        output_dir = Path(os.path.dirname(__file__)).parent.parent / 'output'

        if not output_dir.exists():
            raise ValueError(f"output 目录不存在: {output_dir}")

        # 收集所有要上传的文档
        documents_to_upload = []

        # 遍历目录
        for file_path in output_dir.rglob('*'):
            if file_path.is_file():
                try:
                    # 如果是 JSON 文件
                    if file_path.suffix == '.json':
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = json.load(f)
                            # 假设 JSON 文件包含文本内容
                            if isinstance(content, dict) and 'text' in content:
                                documents_to_upload.append({
                                    'content': content['text'],
                                    'name': file_path.name
                                })

                    # 如果是 Markdown 或其他文本文件
                    elif file_path.suffix in ['.md', '.txt']:
                        with open(file_path, 'r', encoding='utf-8') as f:
                            content = f.read()
                            documents_to_upload.append({
                                'content': content,
                                'name': file_path.name
                            })

                except Exception as e:
                    print(f"处理文件 {file_path} 失败: {str(e)}")
                    continue

        # 批量上传文档
        if documents_to_upload:
            print(f"\n开始批量上传 {len(documents_to_upload)} 个文档...")
            results = dataset_manager.batch_create_documents(
                documents_to_upload,
                indexing_technique="high_quality"
            )
            print(f"成功上传 {len(results)} 个文档")
        else:
            print("没有找到可上传的文档")

        # 获取当前数据集状态
        docs_response = client.list_documents(current_dataset["id"])
        doc_count = docs_response.get('total', 0)
        print(f"\n当前数据集状态:")
        print(f"- 名称: {current_dataset['name']}")
        print(f"- 文档数量: {doc_count}")
        print(f"- 剩余容量: {dataset_manager.max_docs - doc_count}")

    # 运行处理
    process_output_directory()

if __name__ == "__main__":
    try:
        upload_to_dify()
    except Exception as e:
        print(f"错误: {str(e)}")
