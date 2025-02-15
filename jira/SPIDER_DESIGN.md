# Jira爬虫核心设计

## 1. 类设计

### 1.1 爬虫主类 (JiraSpider)
```python
class JiraSpider:
    """Jira系统爬虫主类"""
    name = "jira"

    def __init__(self):
        self.auth_manager = AuthManager()
        self.content_parser = ContentParser()
        self.exporter = DocumentExporter()
```

### 1.2 认证管理类 (AuthManager)
```python
class AuthManager:
    """认证管理类"""
    def __init__(self):
        self.cookies = {}
        self.headers = {}

    def get_headers(self) -> dict:
        """获取认证头信息"""

    def update_cookies(self, cookies: dict):
        """更新Cookie信息"""
```

### 1.3 内容解析类 (ContentParser)
```python
class ContentParser:
    """内容解析处理类"""
    def __init__(self):
        self.optimizer = OptimizerFactory.create_optimizer()

    def parse_issue_table(self, html: str) -> tuple:
        """解析问题列表表格"""

    def parse_pagination(self, html: str) -> tuple:
        """解析分页信息"""

    def parse_issue_detail(self, html: str) -> dict:
        """解析问题详情"""
```

### 1.4 文档导出类 (DocumentExporter)
```python
class DocumentExporter:
    """文档导出类"""
    def export_issue(self, issue_data: dict, page_num: int):
        """导出单个问题数据"""

    def create_page_directory(self, page_num: int) -> str:
        """创建分页目录"""
```

## 2. 核心流程设计

### 2.1 初始化流程
```python
def initialize(self):
    """初始化爬虫"""
    # 1. 加载配置
    # 2. 初始化认证管理器
    # 3. 初始化内容解析器
    # 4. 初始化导出器
```

### 2.2 问题列表处理流程
```python
def process_issue_table(self):
    """处理问题列表"""
    # 1. 构建初始请求
    url = f"{config.spider.base_url}/rest/issueNav/1/issueTable"
    data = {
        "startIndex": 0,
        "filterId": 37131,
        "jql": "project in (PMS, V10) AND created >= 2024-01-01 AND resolved <= 2025-01-01 ORDER BY created ASC"
    }

    # 2. 发送请求获取数据
    # 3. 解析问题列表
    # 4. 解析分页信息
    # 5. 提取问题链接
    # 6. 处理下一页
```

### 2.3 问题详情处理流程
```python
def process_issue_detail(self, issue_url: str, page_num: int):
    """处理问题详情"""
    # 1. 发送请求获取详情页
    # 2. 解析问题详情内容
    # 3. 使用优化器处理文本
    # 4. 导出为Markdown文档
```

## 3. 数据模型

### 3.1 问题数据模型
```python
@dataclass
class JiraIssue:
    """Jira问题数据模型"""
    id: str                 # 问题ID
    key: str               # 问题Key
    summary: str           # 标题
    description: str       # 描述
    created_date: str      # 创建时间
    resolved_date: str     # 解决时间
    reporter: str          # 报告人
    assignee: str          # 经办人
    status: str            # 状态
    priority: str          # 优先级
    optimized_content: str # 优化后的内容
```

## 4. 异常处理

### 4.1 自定义异常类
```python
class JiraSpiderError(Exception):
    """Jira爬虫基础异常"""
    pass

class AuthenticationError(JiraSpiderError):
    """认证相关异常"""
    pass

class ParseError(JiraSpiderError):
    """解析相关异常"""
    pass

class ExportError(JiraSpiderError):
    """导出相关异常"""
    pass
```

### 4.2 异常处理策略

1. 认证异常处理：
   - 重试认证
   - 更新认证信息
   - 记录失败原因

2. 网络请求异常：
   - 实现退避重试机制
   - 记录失败的URL
   - 保存已处理的进度

3. 解析异常处理：
   - 记录解析失败的内容
   - 尝试使用备选解析方案
   - 跳过严重错误继续执行

4. 导出异常处理：
   - 确保目录存在
   - 处理文件命名冲突
   - 保存错误日志

## 5. 性能优化

1. 请求优化：
   - 控制并发数
   - 实现请求延迟
   - 使用会话保持

2. 解析优化：
   - 缓存解析结果
   - 优化选择器
   - 避免重复解析

3. 导出优化：
   - 批量写入文件
   - 异步导出
   - 压缩存储

## 6. 监控指标

1. 性能指标：
   - 请求响应时间
   - 解析处理时间
   - 导出处理时间

2. 业务指标：
   - 已处理问题数
   - 成功率统计
   - 错误分布

3. 资源指标：
   - 内存使用
   - CPU使用
   - 磁盘IO