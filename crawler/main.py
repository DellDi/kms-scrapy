import os
from scrapy.crawler import CrawlerProcess
from scrapy.utils.project import get_project_settings
from crawler.core.spider import ConfluenceSpider
from .core.config import SpiderConfig


def main():
    # 创建输出目录
    output_dir = SpiderConfig.output_dir
    # 先判断输出的output目录下是否存在管道记录confluence.json,存在那么先删除掉
    if os.path.exists(f"{output_dir}/{ConfluenceSpider.name}.json"):
        os.remove(f"{output_dir}/{ConfluenceSpider.name}.json")

    os.makedirs(output_dir, exist_ok=True)

    # 配置Scrapy设置
    settings = get_project_settings()
    settings.update(
        {
            "FEEDS": {
                f"{output_dir}/%(name)s.json": {"format": "json", "encoding": "utf8", "indent": 2}
            }
        }
    )

    # 创建爬虫进程
    process = CrawlerProcess(settings)

    # 添加爬虫 智慧数据-开始
    process.crawl(
        ConfluenceSpider,
        start_url="http://kms.new-see.com:8090/pages/viewpage.action?pageId=122356823",
    )

    # 启动爬虫
    process.start()


if __name__ == "__main__":
    main()
