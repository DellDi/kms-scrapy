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

# 默认配置
DEFAULT_INPUT_DIR = "output"  # 默认从output目录读取文件
API_KEY = os.getenv("DIFY_API_KEY", "your-api-key")
BASE_URL = os.getenv("DIFY_BASE_URL", "https://api.dify.ai/v1")

def setup_logging():
    """配置日志"""
    # 创建logs目录（如果不存在）
    log_dir = "logs-dify"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件路径
    log_file = os.path.join(
        log_dir,
        f'dify_uploader_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
    )

    # 配置根日志记录器
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)  # 设置为DEBUG以捕获所有级别的日志

    # 创建并配置文件处理器
    file_handler = logging.FileHandler(log_file, encoding='utf-8')
    file_handler.setLevel(logging.DEBUG)
    file_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )
    file_handler.setFormatter(file_format)
    root_logger.addHandler(file_handler)

    # 创建并配置控制台处理器
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.INFO)  # 控制台只显示INFO及以上级别
    console_format = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
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
        
        # 获取要处理的文件列表
        input_path = Path(DEFAULT_INPUT_DIR)
        if not input_path.exists():
            logger.error(f"输入目录不存在: {DEFAULT_INPUT_DIR}")
            return None

        files_to_process = list(input_path.rglob("*"))

        # 统计计数
        total_files = len(files_to_process)
        processed_files = 0
        successful_uploads = 0

        logger.info(f"找到 {total_files} 个文件待处理")

        # 处理每个文件
        for file_path in files_to_process:
            try:
                if file_path.is_file():
                    logger.info(f"处理文件: {file_path}")
                    # TODO: 根据文件类型选择适当的处理器
                    # TODO: 实现文件处理和上传逻辑
                    successful_uploads += 1
                processed_files += 1
            except Exception as e:
                logger.error(f"处理文件失败 ({file_path}): {str(e)}")
                continue

            # 输出进度
            progress = (processed_files / total_files) * 100
            logger.info(f"进度: {progress:.2f}% ({processed_files}/{total_files})")

        # 计算执行时间
        end_time = datetime.now()
        duration = end_time - start_time

        # 输出统计信息
        logger.info("-" * 50)
        logger.info("处理完成!")
        logger.info(f"总文件数: {total_files}")
        logger.info(f"成功上传: {successful_uploads}")
        logger.info(f"失败数量: {total_files - successful_uploads}")
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
        client = DifyClient(
            api_key=API_KEY,
            base_url=BASE_URL
        )

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