# Scrapy-Baidu 项目实现计划

## 1. 项目架构

```
scrapy-baidu/
├── scrapy.cfg                     # Scrapy 项目配置文件
└── scrapy_baidu/
    ├── __init__.py
    ├── items.py                   # 数据模型定义
    ├── middlewares/
    │   ├── __init__.py
    │   ├── playwright_middleware.py  # Playwright 集成中间件
    │   └── retry_middleware.py    # 重试机制中间件
    ├── pipelines/
    │   ├── __init__.py
    │   ├── content_pipeline.py    # 内容清洗管道
    │   ├── markdown_pipeline.py   # Markdown 转换管道
    │   └── storage_pipeline.py    # 数据存储管道
    ├── settings.py               # 项目配置
    └── spiders/
        ├── __init__.py
        └── baidu_spider.py      # 百度热搜爬虫实现

```

## 2. 核心组件设计

### 2.1 Spider 设计
```python
# baidu_spider.py
class BaiduSpider(scrapy.Spider):
    name = 'baidu'
    custom_settings = {
        'PLAYWRIGHT_LAUNCH_OPTIONS': {
            'headless': True,
            'timeout': 20 * 1000  # 页面加载超时设置
        },
        'CONCURRENT_REQUESTS': 4,  # 并发请求数
        'DOWNLOAD_DELAY': 1,       # 请求间隔
        'PLAYWRIGHT_MAX_PAGES': 8  # 最大页面数
    }
```

### 2.2 Playwright 中间件
```python
# playwright_middleware.py
class PlaywrightMiddleware:
    async def process_request(self, request, spider):
        page = await self.browser.new_page()
        try:
            # 等待热搜内容加载
            await page.wait_for_selector('#hotsearch-content-wrapper')
            # 点击展开更多
            await page.click('.title-content')
            # 获取页面内容
            content = await page.content()
            return HtmlResponse(url=request.url, body=content, encoding='utf-8')
        finally:
            await page.close()
```

### 2.3 数据模型
```python
# items.py
class HotSearchItem(scrapy.Item):
    title = scrapy.Field()          # 标题
    rank = scrapy.Field()           # 排名
    heat_score = scrapy.Field()     # 热度值
    content = scrapy.Field()        # 详细内容
    url = scrapy.Field()            # 原文链接
    crawl_time = scrapy.Field()     # 爬取时间
```

### 2.4 Pipeline 设计
```python
# content_pipeline.py
class ContentCleaningPipeline:
    """内容清洗管道"""
    def process_item(self, item, spider):
        # 去除 HTML 标签
        # 规范化文本格式
        return item

# markdown_pipeline.py
class MarkdownPipeline:
    """Markdown 转换管道"""
    def process_item(self, item, spider):
        # 转换为 Markdown 格式
        # 保存文件
        return item
```

## 3. 性能优化策略

### 3.1 并发控制
- 使用 CONCURRENT_REQUESTS 控制并发数
- 实现 DOWNLOAD_DELAY 避免请求过密
- 使用 PLAYWRIGHT_MAX_PAGES 限制浏览器页面数

### 3.2 资源管理
- 实现页面生命周期管理
- 定期清理未使用的页面
- 内存使用监控

### 3.3 错误处理
- 自定义 RetryMiddleware
- 异常日志记录
- 失败重试机制

## 4. 数据存储结构

### 4.1 Markdown 文件组织
```
output/
├── {date}/                    # 按日期组织
│   ├── {timestamp}/          # 具体时间点
│   │   ├── 1_标题.md        # 排名_标题
│   │   ├── 2_标题.md
│   │   └── ...
│   └── summary.md           # 汇总信息
└── README.md                # 项目说明
```

### 4.2 Markdown 模板
```markdown
# {标题}

## 基本信息
- 排名：{rank}
- 热度：{heat_score}
- 爬取时间：{crawl_time}
- 原文链接：{url}

## 详细内容
{content}
```

## 5. 后续优化方向

1. 数据增强
   - 添加历史趋势分析
   - 实现关键词提取
   - 集成情感分析

2. 性能提升
   - 实现分布式爬取
   - 添加代理池支持
   - 优化资源使用

3. 监控告警
   - 添加性能监控
   - 实现异常告警
   - 集成数据质量检查

4. 部署方案
   - Docker 容器化
   - CI/CD 集成
   - 自动化测试