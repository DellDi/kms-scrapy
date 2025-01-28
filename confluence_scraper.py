import os
from typing import List
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from scrapegraphai.graphs import ScriptCreatorMultiGraph
from scrapegraphai.utils import prettify_exec_info
from playwright.sync_api import sync_playwright

load_dotenv()

class KMSContent(BaseModel):
    title: str = Field(description="文档标题")
    content: str = Field(description="文档内容")

class KMSContents(BaseModel):
    infos: List[KMSContent]

def get_authenticated_html(url: str) -> str:
    """获取经过认证的页面内容"""
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=False)
        context = browser.new_context(
            http_credentials={
                "username": "newsee",
                "password": "newsee"
            }
        )
        page = context.new_page()
        page.goto(url)

        # 处理登录页面
        page.fill("#os_username", "zengdi")
        page.fill("#os_password", "808611")
        page.click("input[type='submit']")
        page.wait_for_load_state("networkidle")

        # 获取左侧导航树中的所有链接
        links = page.locator(".plugin-tabmeta-details a").all()
        urls = []
        for link in links:
            href = link.get_attribute("href")
            if href and "pageId" in href:
                urls.append(f"http://kms.new-see.com:8090{href}")

        browser.close()
        return urls

def main():
    # 配置爬虫
    graph_config = {
        "llm": {
            "api_key": os.getenv("DEEPSEEK_API_KEY"),
            "model": "deepseek/deepseek-chat",
        },
        "library": "beautifulsoup",
        "verbose": True,
        "headless": True,
    }

    # 获取所有需要爬取的URL
    start_url = "http://kms.new-see.com:8090/pages/viewpage.action?pageId=145719805"
    urls = get_authenticated_html(start_url)

    # 创建爬虫实例
    scraper = ScriptCreatorMultiGraph(
        prompt="提取页面的标题和完整内容，包括代码块，输出为md格式",
        source=urls,
        config=graph_config,
        schema=KMSContents,
    )

    # 运行爬虫
    result = scraper.run()

    # 创建输出目录
    output_dir = "output"
    os.makedirs(output_dir, exist_ok=True)

    # 保存结果
    for item in result.infos:
        filename = f"{output_dir}/{item.title}.md"
        with open(filename, "w", encoding="utf-8") as f:
            f.write(item.content)

    # 打印执行信息
    graph_exec_info = scraper.get_execution_info()
    print(prettify_exec_info(graph_exec_info))

if __name__ == "__main__":
    main()