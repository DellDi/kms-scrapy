"""
Jira爬虫主程序
"""

import logging
import sys
from typing import Optional
from datetime import datetime

from jira.core import (
    config,
    JiraSpider,
    DocumentExporter,
    AuthError,
    ExportError
)

# 配置日志
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(sys.stdout),
        logging.FileHandler(
            f'jira_spider_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
        )
    ]
)

logger = logging.getLogger(__name__)

def run_spider(clear_output: bool = True) -> Optional[bool]:
    """
    运行爬虫程序

    Args:
        clear_output: 是否清空输出目录

    Returns:
        Optional[bool]: 执行是否成功，出错返回None
    """
    try:
        spider = JiraSpider()
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