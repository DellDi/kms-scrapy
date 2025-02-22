# Scrapy settings for scrapy-baidu project
import os
from pathlib import Path

# 基本路径配置
BASE_DIR = Path(__file__).parent.parent.absolute()

# 用户主目录下创建工作目录
USER_HOME = Path.home()
WORK_DIR = USER_HOME / '.scrapy-baidu'
WORK_DIR.mkdir(parents=True, exist_ok=True)

# 子目录配置
OUTPUT_DIR = WORK_DIR / 'output'
LOG_DIR = WORK_DIR / 'logs'
CACHE_DIR = WORK_DIR / 'cache'

# 确保目录存在
for directory in [OUTPUT_DIR, LOG_DIR, CACHE_DIR]:
    directory.mkdir(parents=True, exist_ok=True)

# 爬虫基本设置
BOT_NAME = "scrapy-baidu"
SPIDER_MODULES = ["scrapy_baidu.spiders"]
NEWSPIDER_MODULE = "scrapy_baidu.spiders"

# User-Agent配置
USER_AGENT = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36"

# 并发设置
CONCURRENT_REQUESTS = 4
CONCURRENT_REQUESTS_PER_DOMAIN = 4
DOWNLOAD_DELAY = 1
RANDOMIZE_DOWNLOAD_DELAY = True

# 下载器中间件
DOWNLOADER_MIDDLEWARES = {
    "scrapy_baidu.middlewares.playwright_middleware.PlaywrightMiddleware": 725,
    "scrapy_baidu.middlewares.retry_middleware.CustomRetryMiddleware": 550,
    "scrapy.downloadermiddlewares.retry.RetryMiddleware": None,
}

# 数据管道
ITEM_PIPELINES = {
    "scrapy_baidu.pipelines.content_pipeline.ContentCleaningPipeline": 300,
    "scrapy_baidu.pipelines.markdown_pipeline.MarkdownPipeline": 800,
}

# Playwright 设置
PLAYWRIGHT_ENABLED = True
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 30000,
    "args": [
        "--disable-gpu",
        "--no-sandbox",
        "--disable-dev-shm-usage",
        "--disable-setuid-sandbox",
        "--no-first-run",
        "--no-zygote",
        "--single-process",
        "--disable-extensions"
    ]
}
PLAYWRIGHT_MAX_PAGES = 8
PLAYWRIGHT_CONTEXT_ARGS = {
    "viewport": {"width": 1920, "height": 1080},
    "user_agent": USER_AGENT,
}
PLAYWRIGHT_INSTALL_IF_MISSING = True

# 重试设置
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]
RETRY_PRIORITY_ADJUST = -1
RETRY_DELAY = 1

# 输出设置
MARKDOWN_OUTPUT_DIR = str(OUTPUT_DIR)
FEED_EXPORT_ENCODING = "utf-8"

# HTTP缓存设置
HTTPCACHE_ENABLED = True
HTTPCACHE_EXPIRATION_SECS = 0
HTTPCACHE_DIR = str(CACHE_DIR)
HTTPCACHE_IGNORE_HTTP_CODES = list(range(400, 600))

# 日志设置
LOG_LEVEL = "INFO"
LOG_FORMAT = "%(asctime)s [%(name)s] %(levelname)s: %(message)s"
LOG_FILE = str(LOG_DIR / "spider.log") if LOG_DIR else None  # 确保 LOG_DIR 有值
LOG_STDOUT = True

# 内存监控
MEMDEBUG_ENABLED = True
MEMUSAGE_ENABLED = True
MEMUSAGE_LIMIT_MB = 512
MEMUSAGE_WARNING_MB = 384

# 请求设置
DOWNLOAD_TIMEOUT = 30
COOKIES_ENABLED = True
COOKIES_DEBUG = False

# robots.txt设置
ROBOTSTXT_OBEY = False

# 请求头设置
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'Accept-Encoding': 'gzip, deflate, br',
    'Connection': 'keep-alive',
    'Cache-Control': 'max-age=0',
    'Upgrade-Insecure-Requests': '1'
}

# DNS设置
DNS_TIMEOUT = 10
DNSCACHE_ENABLED = True
DNSCACHE_SIZE = 10000

# 下载设置
DOWNLOAD_WARNSIZE = 33554432  # 32MB
DOWNLOAD_MAXSIZE = 1073741824  # 1GB
AJAXCRAWL_ENABLED = True

# 项目自定义设置
STATS_DUMP = True  # 统计信息导出
COOKIES_PERSISTENCE = True  # Cookie持久化
TELNETCONSOLE_ENABLED = True  # Telnet控制台