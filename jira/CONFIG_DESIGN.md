# Jira爬虫配置设计

## 1. 配置结构

```python
@dataclass
class AuthConfig:
    username: str = "newsee"
    password: str = "newsee"
    basic_auth: str = "bmV3c2VlOm5ld3NlZQ=="  # base64(newsee:newsee)

@dataclass
class SpiderConfig:
    base_url: str = "http://bug.new-see.com:8088"
    download_delay: float = 1.0
    concurrent_requests: int = 1
    retry_times: int = 3
    retry_http_codes: list = [500, 502, 503, 504, 400]

    # 默认请求头
    default_headers: dict = {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Atlassian-Token": "no-check",
        "X-Requested-With": "XMLHttpRequest",
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
    }

    # 默认Cookie
    default_cookies: dict = {
        "ajs_user_id": "b855f69db6d93f0a1a50b21008c841d7416fc802",
        "ajs_anonymous_id": "5a3663bd-29d6-4df5-abc0-a5bb2358e422"
    }

@dataclass
class OptimizerConfig:
    api_key: str = ""  # 优化器API密钥
    api_url: str = ""  # 优化器API地址
    optimizer_type: str = "html2md"  # 使用的优化器类型

@dataclass
class ExporterConfig:
    output_dir: str = "output-jira"  # 输出根目录
    page_dir_prefix: str = "page"    # 分页目录前缀

@dataclass
class Config:
    auth: AuthConfig = AuthConfig()
    spider: SpiderConfig = SpiderConfig()
    optimizer: OptimizerConfig = OptimizerConfig()
    exporter: ExporterConfig = ExporterConfig()

# 全局配置实例
config = Config()
```

## 2. 配置说明

### 2.1 身份认证配置 (AuthConfig)
- username/password: Jira系统登录凭证
- basic_auth: Base64编码的认证信息

### 2.2 爬虫配置 (SpiderConfig)
- base_url: Jira系统基础URL
- download_delay: 请求延迟时间(秒)
- concurrent_requests: 并发请求数
- retry_times: 重试次数
- retry_http_codes: 需要重试的HTTP状态码
- default_headers: 默认请求头
- default_cookies: 默认Cookie信息

### 2.3 优化器配置 (OptimizerConfig)
- api_key: API密钥
- api_url: API服务地址
- optimizer_type: 使用的优化器类型(html2md/xunfei/baichuan/compatible等)

### 2.4 导出器配置 (ExporterConfig)
- output_dir: 输出目录路径
- page_dir_prefix: 分页目录名称前缀

## 3. 配置加载机制

1. 环境变量优先级：
   - 系统环境变量优先
   - .env文件配置次之
   - 默认配置最后

2. 配置文件位置：
   - 项目根目录下的.env文件
   - 测试配置可放在test/settings.py

3. 环境变量命名规范：
```
JIRA_AUTH_USERNAME=xxx
JIRA_AUTH_PASSWORD=xxx
JIRA_SPIDER_BASE_URL=xxx
JIRA_OPTIMIZER_API_KEY=xxx
```

## 4. 使用示例

```python
from jira.core.config import config

# 使用配置
auth_headers = {
    "Authorization": f"Basic {config.auth.basic_auth}",
    **config.spider.default_headers
}

# 获取完整URL
full_url = f"{config.spider.base_url}/rest/issueNav/1/issueTable"

# 获取输出路径
output_path = f"{config.exporter.output_dir}/page1/bug-001.md"