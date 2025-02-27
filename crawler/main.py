"""
Confluence爬虫主程序
"""

import os
import sys
import logging
from datetime import datetime
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.core.spider import ConfluenceSpider
from core.config import config

def setup_logging():
    """配置日志"""
    # 创建logs目录（如果不存在）
    log_dir = "logs-kms"
    if not os.path.exists(log_dir):
        os.makedirs(log_dir)

    # 生成日志文件路径
    log_file = os.path.join(
        log_dir,
        f'confluence_spider_{datetime.now().strftime("%Y%m%d_%H%M%S")}.log'
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

def main():
    """主函数"""
    try:
        # 配置日志
        logger = setup_logging()
        logger.info("开始运行Confluence爬虫...")

        # 创建输出目录
        output_dir = config.spider.output_dir
        logger.info(f"输出目录: {output_dir}")

        # 检查并清理旧的输出文件
        json_file = f"{output_dir}/{ConfluenceSpider.name}.json"
        if os.path.exists(json_file):
            logger.info(f"删除旧的输出文件: {json_file}")
            os.remove(json_file)

        # 创建输出目录
        os.makedirs(output_dir, exist_ok=True)
        logger.info("已创建输出目录")

        # 配置Scrapy设置
        settings = get_project_settings()
        settings.update({
            "FEEDS": {
                f"{output_dir}/%(name)s.json": {
                    "format": "json",
                    "encoding": "utf8",
                    "indent": 2
                }
            }
        })
        logger.debug(f"Scrapy设置: {settings}")

        # 创建爬虫进程
        process = CrawlerProcess(settings)
        logger.info("已创建爬虫进程")

        # 添加爬虫 智慧大品控-开始
        start_url = "http://kms.new-see.com:8090/pages/viewpage.action?pageId=27363403"
        logger.info(f"添加爬虫任务: {start_url}")
        process.crawl(
            ConfluenceSpider,
            start_url=start_url,
        )

        # 启动爬虫
        logger.info("开始爬取...")
        start_time = datetime.now()

        process.start()

        # 计算执行时间
        end_time = datetime.now()
        duration = end_time - start_time

        # 输出统计信息
        logger.info("-" * 50)
        logger.info("爬虫执行完成!")
        logger.info(f"执行时间: {duration}")
        logger.info("-" * 50)

    except KeyboardInterrupt:
        logger.info("\n用户中断执行")
        sys.exit(1)
    except Exception as e:
        logger.error(f"程序执行失败: {str(e)}")
        sys.exit(1)

if __name__ == "__main__":
    main()
