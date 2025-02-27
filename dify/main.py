"""
Dify 知识库导入工具
"""

import os
import sys
import logging
from typing import Optional
from datetime import datetime
from pathlib import Path

from dify import DifyClient, DatasetManager
from config import API_KEY, BASE_URL, DEFAULT_INPUT_DIR, SUPPORTED_FILE_EXTENSIONS

# 配置日志
def setup_logging():
    """配置日志"""
    # 创建logs目录（如果不存在）
    log_dir = "logs-dify"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件路径
    log_file = os.path.join(
        log_dir, f'dify_uploader_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设置为DEBUG以捕获所有级别的日志

    # 创建并配置文件处理器
    file_handler = logging.FileHandler(log_file, encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # 创建并配置控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别
    console_format = logging.Formatter(
        "%(asctime)s - %(name)s - %(levelname)s - %(message)s", datefmt="%H:%M:%S"
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    return logging.getLogger(__name__)


def process_documents(client: DifyClient) -> Optional[bool]:
    """
    处理文档上传

    Args:
        client: Dify客户端实例

    Returns:
        Optional[bool]: 处理是否成功，出错返回None
    """
    try:
        logger.info(f"开始处理目录: {DEFAULT_INPUT_DIR}")
        start_time = datetime.now()

        # 创建数据集管理器
        dataset_manager = DatasetManager(client)

        # 初始化或获取当前数据集
        logger.info("初始化数据集...")
        current_dataset = dataset_manager.initialize()
        logger.info(f"当前使用数据集: {current_dataset['name'] if current_dataset else '新建中'}")

        # 获取要处理的文件列表
        input_path = Path(DEFAULT_INPUT_DIR)
        if not input_path.exists():
            logger.error(f"输入目录不存在: {DEFAULT_INPUT_DIR}")
            return None

        # 收集所有要上传的文件
        files_to_upload = []

        # 遍历目录收集文件
        for file_path in input_path.rglob("*"):
            if file_path.is_file():
                try:
                    # 收集支持的文件
                    if file_path.suffix in SUPPORTED_FILE_EXTENSIONS:
                        files_to_upload.append(str(file_path))
                        logger.info(f"添加待上传文件: {file_path.name}")
                    else:
                        logger.info(f"跳过不支持的文件类型: {file_path}")
                except Exception as e:
                    logger.error(f"处理文件 {file_path} 失败: {str(e)}")
                    logger.error(f"错误类型: {type(e)}")
                    continue

        # 上传文件
        successful_uploads = 0
        if files_to_upload:
            logger.info(f"开始上传 {len(files_to_upload)} 个文件...")
            results = dataset_manager.upload_files(
                files_to_upload, indexing_technique="high_quality", process_rule="custom"
            )
            successful_uploads = len([r for r in results if r is not None])
            logger.info(f"成功上传 {successful_uploads} 个文件")
        else:
            logger.info("没有找到可上传的文件")

            # 获取当前数据集状态
            docs_response = client.list_documents(current_dataset["id"])
            doc_count = docs_response.get("total", 0)
            logger.info(f"\n当前数据集状态:")
            logger.info(f"- 名称: {current_dataset['name']}")
            logger.info(f"- 文档数量: {doc_count}")
            logger.info(f"- 剩余容量: {dataset_manager.max_docs - doc_count}")

        # 计算执行时间
        end_time = datetime.now()
        duration = end_time - start_time

        # 输出统计信息
        logger.info("-" * 50)
        logger.info("处理完成!")
        logger.info(f"总文件数: {len(files_to_upload)}")
        logger.info(f"成功上传: {successful_uploads}")
        logger.info(f"失败数量: {len(files_to_upload) - successful_uploads}")
        logger.info(f"执行时间: {duration}")
        logger.info("-" * 50)

        return successful_uploads > 0

    except KeyboardInterrupt:
        logger.info("\n用户中断执行")
        return None
    except Exception as e:
        logger.error(f"处理出错: {str(e)}")
        return None


def main():
    """主函数"""
    try:
        # 创建Dify客户端
        client = DifyClient(api_key=API_KEY, base_url=BASE_URL)
        logger.info("Dify客户端初始化完成")
        logger.info(f"API密钥: {'*' * 16}{API_KEY[-4:] if len(API_KEY) > 4 else API_KEY}")
        logger.info(f"API地址: {BASE_URL}")
        logger.info(f"输入目录: {DEFAULT_INPUT_DIR}")
        # 处理文档
        success = process_documents(client)
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)


# 配置日志
logger = setup_logging()

if __name__ == "__main__":
    main()
