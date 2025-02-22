# 百度热搜爬虫

基于 Scrapy 和 Playwright 的现代爬虫实现，用于抓取百度热搜内容并生成结构化的 Markdown 文档。

## 特性

- 稳定的动态页面处理（使用 Playwright）
- 智能的内容提取和清洗
- 结构化的 Markdown 输出
- 完整的错误处理和重试机制
- 详细的日志记录
- 性能监控和统计

## 环境要求

- Python 3.11+
- Node.js 14+ (Playwright 依赖)
- 操作系统：Linux/macOS/Windows

## 安装指南

1. 安装项目依赖：
```bash
# 使用 pip
pip install -e .

# 或使用 poetry
poetry install

# 或使用 uv（推荐）
uv venv
uv pip install -e .
```

2. 安装 Playwright 浏览器：
```bash
playwright install chromium
```

## 使用方法

1. 基本运行：
```bash
cd scrapy-baidu
python main.py
```

2. 调试模式：
```bash
python main.py --debug
```

## 输出结构

```
scrapy-baidu/
├── output/                    # 输出目录
│   ├── metadata/             # 元数据
│   │   └── stats.json       # 统计信息
│   └── YYYY-MM-DD/          # 按日期组织
│       ├── HH-MM-SS/        # 具体抓取时间
│       │   ├── 01_标题1.md  # 排名_标题.md
│       │   └── 02_标题2.md  # 排名_标题.md
│       └── summary.md       # 当日汇总
├── logs/                     # 日志目录
│   └── spider.log           # 详细日志
└── httpcache/               # 缓存目录
```

## 配置选项

主要配置项（settings.py）：

```python
# 并发控制
CONCURRENT_REQUESTS = 4
DOWNLOAD_DELAY = 1

# Playwright 设置
PLAYWRIGHT_ENABLED = True
PLAYWRIGHT_LAUNCH_OPTIONS = {
    "headless": True,
    "timeout": 30000,
}

# 重试设置
RETRY_TIMES = 3
RETRY_HTTP_CODES = [500, 502, 503, 504, 408, 429, 403]
```

## 常见问题

1. Playwright 初始化失败
```
错误：Executable doesn't exist
解决：运行 playwright install chromium
```

2. 页面加载超时
```
错误：TimeoutError: Navigation timeout
解决：增加 DOWNLOAD_TIMEOUT 或 PLAYWRIGHT_LAUNCH_OPTIONS 的 timeout 值
```

3. 内存使用过高
```
调整 settings.py 中的内存限制：
MEMUSAGE_LIMIT_MB = 512
MEMUSAGE_WARNING_MB = 384
```

## 调试指南

1. 启用调试模式：
```bash
python main.py --debug
```

2. 查看详细日志：
```bash
tail -f logs/spider.log
```

3. 检查统计信息：
```bash
cat output/metadata/stats.json
```

## 性能优化

1. 并发设置
- 调整 CONCURRENT_REQUESTS
- 设置合理的 DOWNLOAD_DELAY

2. 缓存配置
- 启用 HTTPCACHE_ENABLED
- 配置缓存策略

3. 内存管理
- 监控内存使用
- 及时释放资源

## 安全建议

1. 请求限制
- 使用适当的延迟
- 避免过度并发

2. 错误处理
- 使用重试机制
- 记录详细日志

3. 资源管理
- 及时关闭浏览器
- 清理临时文件

## 开发指南

### 目录结构

```
scrapy-baidu/
├── main.py                 # 主入口
├── scrapy.cfg             # Scrapy 配置
└── scrapy_baidu/
    ├── middlewares/      # 中间件
    ├── pipelines/        # 数据管道
    └── spiders/          # 爬虫实现
```

### 扩展开发

1. 添加新的管道：
```python
class NewPipeline:
    def process_item(self, item, spider):
        # 处理逻辑
        return item
```

2. 自定义中间件：
```python
class CustomMiddleware:
    def process_request(self, request, spider):
        # 请求处理
        return None
```

## 贡献指南

1. Fork 项目
2. 创建特性分支
3. 提交改动
4. 发起 Pull Request

## 许可证

MIT License

## 作者

- zengdi