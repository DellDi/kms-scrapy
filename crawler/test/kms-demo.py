import scrapy
from scrapy.http import Request
from bs4 import BeautifulSoup

class KMSDemoSpider(scrapy.Spider):
    name = 'kms-newsee'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = ['http://kms.new-see.com:8090/pages/viewpage.action?pageId=145719805']

    def start_requests(self):
        for url in self.start_urls:
            headers = {
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Authorization': 'Basic bmV3c2VlOm5ld3NlZQ==',
                'Connection': 'keep-alive',
                'Cookie': 'confluence.list.pages.cookie=list-content-tree;JSESSIONID=F93704C0156F50D975D63EC8DF23EE62;seraph.confluence=149782566%3Adcc80dc3aa14b0a5f57223027a87f61e56afa47d',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
            }
            yield Request(
                url,
                callback=self.parse,
                headers=headers,
                dont_filter=True,
                meta={
                    'dont_merge_cookies': True,
                    'handle_httpstatus_list': [302]
                }
            )

    def parse(self, response):
        # 解析页面内容
        soup = BeautifulSoup(response.text, 'html.parser')
        title = soup.select_one('#title-text').get_text(strip=True)
        content = soup.select_one('#main-content').get_text()

        # 输出结果
        print('Title:', title)
        print('Content:', content)
        yield {
            'title': title,
            'content': content
        }

def main():
    # 配置Scrapy设置
    settings = {
        'BOT_NAME': 'kms-newsee',
        'SPIDER_MODULES': ['crawler.test'],
        'NEWSPIDER_MODULE': 'crawler.test',
        'DOWNLOAD_DELAY': 2,
        'COOKIES_ENABLED': True,
        'CONCURRENT_REQUESTS': 1,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
        }
    }

    # 创建爬虫进程
    from scrapy.crawler import CrawlerProcess
    process = CrawlerProcess(settings)

    # 添加爬虫
    process.crawl(KMSDemoSpider)

    # 启动爬虫
    process.start()

if __name__ == '__main__':
    main()