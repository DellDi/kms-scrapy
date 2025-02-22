#!/usr/bin/env python3
"""
百度热搜爬虫
用法: python main.py [--debug]

功能：抓取百度热搜内容，生成结构化的 Markdown 文档
"""

import os
import sys
import logging
from pathlib import Path
from colorama import init, Fore, Style
from scrapy.utils.project import get_project_settings
from scrapy.crawler import CrawlerProcess
from playwright.sync_api import sync_playwright
import traceback
from scrapy_baidu.spiders.baidu_spider import BaiduSpider

# 初始化 colorama
init(autoreset=True)

def setup_logging(debug: bool = False):
    """配置日志系统"""
    try:
        # 获取项目设置
        settings = get_project_settings()
        log_dir = settings.get('LOG_DIR')

        # 设置日志级别
        level = logging.DEBUG if debug else logging.INFO

        # 配置根日志器
        logging.basicConfig(
            level=level,
            format='%(asctime)s [%(name)s] %(levelname)s: %(message)s',
            handlers=[
                logging.StreamHandler(sys.stdout),  # 控制台输出
            ]
        )

        # 如果配置了日志文件，则添加文件处理器
        if log_dir:
            log_file = Path(log_dir) / 'spider.log'
            file_handler = logging.FileHandler(log_file, encoding='utf-8')
            file_handler.setFormatter(formatter)
            handlers.append(file_handler)

        # 设置 Scrapy 和其他库的日志级别
        logging.getLogger('scrapy').setLevel(level)
        logging.getLogger('playwright').setLevel(level)
        logging.getLogger('urllib3').setLevel(logging.INFO)
        logging.getLogger('asyncio').setLevel(logging.INFO)

        if debug:
            logging.info(f"{Fore.GREEN}调试模式已启用{Style.RESET_ALL}")

    except Exception as e:
        print(f"{Fore.RED}错误：配置日志系统失败{Style.RESET_ALL}")
        print(f"详细信息: {str(e)}")
        sys.exit(1)

def check_playwright() -> None:
    """检查并安装 Playwright"""
    try:
        with sync_playwright() as p:
            logging.info("检查 Playwright 浏览器...")
            try:
                browser = p.chromium.launch()
                browser.close()
                logging.info(f"{Fore.GREEN}Playwright 浏览器检查通过{Style.RESET_ALL}")
            except Exception as e:
                if "Executable doesn't exist" in str(e):
                    logging.warning(f"{Fore.YELLOW}Playwright 浏览器未安装，正在安装...{Style.RESET_ALL}")
                    try:
                        p.chromium.download()
                        logging.info(f"{Fore.GREEN}Playwright 浏览器安装完成{Style.RESET_ALL}")
                    except Exception as download_error:
                        logging.error(f"{Fore.RED}Playwright 浏览器下载失败: {str(download_error)}{Style.RESET_ALL}")
                        raise
                else:
                    raise
    except Exception as e:
        logging.error(f"{Fore.RED}Playwright 初始化失败: {str(e)}{Style.RESET_ALL}")
        if '--debug' in sys.argv:
            traceback.print_exc()
        sys.exit(1)

def setup_environment() -> None:
    """设置运行环境"""
    try:
        settings = get_project_settings()

        # 创建工作目录
        work_dir = Path(settings.get('WORK_DIR'))
        work_dir.mkdir(parents=True, exist_ok=True)

        # 创建必要的子目录
        dirs = {
            'OUTPUT_DIR': 'output',
            'LOG_DIR': 'logs',
            'CACHE_DIR': 'cache'
        }

        for key, name in dirs.items():
            path = work_dir / name
            path.mkdir(parents=True, exist_ok=True)
            logging.debug(f"创建目录: {path}")

        logging.info(f"{Fore.GREEN}环境初始化完成{Style.RESET_ALL}")

    except Exception as e:
        logging.error(f"{Fore.RED}环境初始化失败: {str(e)}{Style.RESET_ALL}")
        if '--debug' in sys.argv:
            traceback.print_exc()
        sys.exit(1)

def main():
    """爬虫主函数"""
    try:
        # 处理命令行参数
        debug_mode = '--debug' in sys.argv
        if debug_mode:
            sys.argv.remove('--debug')

        # 设置日志
        setup_logging(debug_mode)

        # 显示启动信息
        logger = logging.getLogger(__name__)
        logger.info("="*50)
        logger.info("百度热搜爬虫")
        logger.info("="*50)

        # 确保在正确的目录中
        os.chdir(os.path.dirname(os.path.abspath(__file__)))

        # 初始化环境
        setup_environment()

        # 检查 Playwright
        check_playwright()

        # 获取项目设置
        settings = get_project_settings()

        # 调整调试模式设置
        if debug_mode:
            settings.set('LOG_LEVEL', 'DEBUG')
            settings.set('CONCURRENT_REQUESTS', 1)
            settings.set('DOWNLOAD_DELAY', 2)
            logger.debug("调整为调试配置：降低并发，增加延迟")

        # 创建爬虫进程
        logger.info(f"{Fore.GREEN}初始化爬虫进程...{Style.RESET_ALL}")
        process = CrawlerProcess(settings)

        # 添加爬虫
        process.crawl(BaiduSpider)

        # 启动进程
        logger.info(f"{Fore.GREEN}开始抓取百度热搜...{Style.RESET_ALL}")
        process.start()

    except KeyboardInterrupt:
        logger.info(f"\n{Fore.YELLOW}手动停止爬虫{Style.RESET_ALL}")
        sys.exit(0)
    except Exception as e:
        logger.error(f"{Fore.RED}爬虫运行出错: {str(e)}{Style.RESET_ALL}")
        if debug_mode:
            traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
