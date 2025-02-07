import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.core.spider import ConfluenceSpider

def main():
    # 创建输出目录
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)
    # 先判断输出的output目录下是否存在管道记录文件,存在那么先删除掉
    if os.path.exists(os.path.join(output_dir, f'${ConfluenceSpider.name}.json')):
        os.remove(os.path.join(output_dir, f'${ConfluenceSpider.name}.json'))
    # 配置Scrapy设置
    settings = get_project_settings()
    settings.update({
        'FEEDS': {
            f'{output_dir}/%(name)s.json': {
                'format': 'json',
                'encoding': 'utf8',
                'indent': 2
            }
        }
    })

    # 创建爬虫进程
    process = CrawlerProcess(settings)

    # 添加爬虫 2024-2月功能时间轴开始
    process.crawl(
        ConfluenceSpider,
        start_url="http://kms.new-see.com:8090/pages/viewpage.action?pageId=27364154",
    )

    # 启动爬虫
    process.start()

if __name__ == "__main__":
    main()
