"""
Jira爬虫主程序
"""

import logging
import sys
from typing import Optional
from datetime import datetime
import os

from jira.core import (
    JiraSpider,
    DocumentExporter,
    AuthManager,
    AuthError,
    ExportError
)

def setup_logging():
    """配置日志"""
    # 创建logs目录（如果不存在）
    log_dir = "logs"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件路径
    log_file = os.path.join(
        log_dir,
        f'jira_spider_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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
        '%(asctime)s - %(levelname)s - %(message)s',
        datefmt='%H:%M:%S'
    )
    console_handler.setFormatter(console_format)
    root_logger.addHandler(console_handler)

    return logging.getLogger(__name__)

# 配置日志
logger = setup_logging()

def run_spider(clear_output: bool = True) -> Optional[bool]:
    """
    运行爬虫程序

    Args:
        clear_output: 是否清空输出目录

    Returns:
        Optional[bool]: 执行是否成功，出错返回None
    """
    try:
        # 初始化认证管理器
        auth_manager = AuthManager()
        
        # 检查认证状态
        logger.info("检查认证状态...")
        auth_valid = auth_manager.check_authentication()
        
        if not auth_valid:
            # 认证失败，尝试刷新认证
            logger.info("认证已失效，尝试刷新认证...")
            auth_valid = auth_manager.refresh_authentication()
            if not auth_valid:
                logger.error("认证刷新失败，无法继续")
                return None
            logger.info("认证刷新成功，继续执行...")

        # 初始化爬虫和导出器
        spider = JiraSpider(auth_manager)
        exporter = DocumentExporter()

        # 清空输出目录
        if clear_output:
            logger.info("清空输出目录...")
            exporter.clear_output_directory()

        # 创建计数器
        total_issues = 0
        successful_exports = 0
        current_page = 1
        current_page_issues = []

        logger.info("开始爬取Jira问题...")
        start_time = datetime.now()

        # 遍历所有问题
        for issue in spider.crawl():
            total_issues += 1
            current_page_issues.append(issue)

            # 每50个问题作为一页
            if len(current_page_issues) >= 50:
                logger.info(f"导出第 {current_page} 页问题...")
                results = exporter.batch_export(current_page_issues, current_page)
                successful_exports += len(results)

                # 清空当前页面列表
                current_page_issues = []
                current_page += 1

        # 处理最后一页
        if current_page_issues:
            logger.info(f"导出最后一页问题...")
            results = exporter.batch_export(current_page_issues, current_page)
            successful_exports += len(results)

        # 计算执行时间
        end_time = datetime.now()
        duration = end_time - start_time

        # 输出统计信息
        logger.info("-" * 50)
        logger.info("爬虫执行完成!")
        logger.info(f"总问题数: {total_issues}")
        logger.info(f"成功导出: {successful_exports}")
        logger.info(f"失败数量: {total_issues - successful_exports}")
        logger.info(f"总页数: {current_page}")
        logger.info(f"执行时间: {duration}")
        logger.info("-" * 50)

        return successful_exports > 0

    except AuthError as e:
        logger.error(f"认证错误: {str(e)}")
        return None

    except ExportError as e:
        logger.error(f"导出错误: {str(e)}")
        return None

    except KeyboardInterrupt:
        logger.info("\n用户中断执行")
        return None

    except Exception as e:
        logger.error(f"执行出错: {str(e)}")
        return None

def main():
    """主函数"""
    try:
        success = run_spider()
        sys.exit(0 if success else 1)

    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
