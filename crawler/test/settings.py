# Scrapy settings

BOT_NAME = 'kms-newsee'

SPIDER_MODULES = ['crawler.test']
NEWSPIDER_MODULE = 'crawler.test'

# 爬虫设置
DOWNLOAD_DELAY = 2
COOKIES_ENABLED = True
CONCURRENT_REQUESTS = 1
RETRY_TIMES = 5
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429]

# 默认请求头
DEFAULT_REQUEST_HEADERS = {
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
}