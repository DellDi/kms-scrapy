"""
示例：使用 Dify API 上传文档到数据集
"""
import os
from typing import Dict, List
import json
from pathlib import Path
from dotenv import load_dotenv

from dify import DifyClient, DatasetManager

# 加载环境变量（强制重新加载）
load_dotenv(override=True)

def upload_to_dify():
    """上传文档到 Dify 数据集"""

    def clean_env_value(value: str) -> str:
        """清理环境变量值（移除注释和空格）"""
        if value and '#' in value:
            value = value.split('#')[0]
        return value.strip() if value else ''

    # 获取并清理配置
    api_key = clean_env_value(os.getenv('DIFY_API_KEY', ''))
    base_url = clean_env_value(os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1"))

    print("\n使用的 API 配置:")
    print(f"Base URL: {base_url}")
    print(f"API Key: {'*' * 20}{api_key[-4:]}")

    if not api_key:
        raise ValueError("请设置 DIFY_API_KEY 环境变量")

    # 初始化 Dify 客户端
    client = DifyClient(api_key, base_url)

    # documents
    dataset_manager = DatasetManager(client)

    # 初始化或获取当前数据集
    print("\n初始化数据集...")
    current_dataset = dataset_manager.initialize()
    print(f"当前使用数据集: {current_dataset['name'] if current_dataset else '新建中'}")

    # 示例：读取 output 目录中的内容并上传
    def process_output_directory() -> None:
        """处理 output 目录中的文档"""
        output_dir = Path(os.path.dirname(__file__)).parent.parent / 'output'

        if not output_dir.exists():
            raise ValueError(f"output 目录不存在: {output_dir}")

        # 收集所有要上传的文件
        files_to_upload = []

        # 遍历目录
        for file_path in output_dir.rglob('*'):
            if file_path.is_file():
                try:
                    # 收集支持的文件
                    if file_path.suffix in ['.md', '.txt', '.json']:
                        files_to_upload.append(str(file_path))
                        print(f"添加待上传文件: {file_path.name}")
                    else:
                        print(f"跳过不支持的文件类型: {file_path}")

                except Exception as e:
                    print(f"处理文件 {file_path} 失败: {str(e)}")
                    print(f"错误类型: {type(e)}")
                    continue

        # 上传文件
        if files_to_upload:
            print(f"\n开始上传 {len(files_to_upload)} 个文件...")
            results = dataset_manager.upload_files(
                files_to_upload,
                indexing_technique="high_quality",
                process_rule="custom"
            )
            successful_uploads = len([r for r in results if r is not None])
            print(f"成功上传 {successful_uploads} 个文件")
        else:
            print("没有找到可上传的文件")

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
        # 检查环境变量
        api_key = os.getenv('DIFY_API_KEY')
        base_url = os.getenv('DIFY_BASE_URL')
        print(f"配置信息:")
        print(f"- API URL: {base_url}")
        print(f"- API Key: {'已设置' if api_key else '未设置'}")
        
        upload_to_dify()
    except Exception as e:
        error_msg = str(e)
        print(f"错误: {error_msg}")
        if isinstance(e, ValueError):
            print("\n提示: 请确保在 .env 文件中设置了必要的环境变量:")
            print("DIFY_API_KEY=your_api_key")
            print("DIFY_BASE_URL=https://api.dify.ai/v1")
