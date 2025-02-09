# Dify 知识库集成实现方案

## 1. 系统架构

### 1.1 模块结构
```
dify/
├── __init__.py
├── api/
│   ├── __init__.py
│   ├── client.py          # Dify API 客户端
│   └── models.py          # 数据模型
├── core/
│   ├── __init__.py
│   ├── knowledge_base.py  # 知识库管理
│   ├── document.py        # 文档处理
│   └── file_processor.py  # 文件处理器
└── utils/
    ├── __init__.py
    └── helpers.py         # 辅助函数
```

## 2. 核心功能实现

### 2.1 知识库管理 (knowledge_base.py)
1. 知识库创建
   - 自动命名规则: kms-${number}
   - 维护知识库计数器
   - 文档数量监控

2. 知识库查询
   - 获取现有知识库列表
   - 查询知识库文档数量
   - 判断是否需要创建新知识库

### 2.2 文档处理 (document.py)
1. 文档上传流程
   - 读取文档内容
   - 处理文档元数据
   - 调用 Dify API 上传

2. 文档计数管理
   - 维护每个知识库的文档数量
   - 触发新知识库创建

### 2.3 文件处理器 (file_processor.py)
支持以下文件类型：
- Markdown (.md)
- PDF (.pdf)
- Excel (.xlsx, .xls)
- Word (.docx, .doc)
- PowerPoint (.pptx, .ppt)

## 3. API 集成 (client.py)

### 3.1 基础功能
1. 认证管理
   - API 密钥管理
   - 请求认证

2. 知识库操作
   - 创建知识库
   - 上传文档
   - 查询知识库信息

3. 错误处理
   - 请求重试机制
   - 错误日志记录

### 3.2 API 接口封装
```python
class DifyClient:
    def create_knowledge_base(self, name: str) -> dict
    def upload_document(self, kb_id: str, file_path: str, meta: dict) -> dict
    def get_knowledge_base(self, kb_id: str) -> dict
    def list_knowledge_bases(self) -> list
```

## 4. 实现流程

### 4.1 初始化过程
1. 配置 Dify API 凭证
2. 初始化客户端实例
3. 验证现有知识库状态

### 4.2 文档处理流程
1. 扫描 output 目录
2. 对每个文件：
   - 确定文件类型
   - 提取内容
   - 准备元数据
   - 选择目标知识库
   - 上传到 Dify

### 4.3 知识库管理流程
1. 检查现有知识库文档数量
2. 当文档数量接近 100 时：
   - 创建新知识库
   - 更新知识库计数器
   - 切换上传目标

## 5. 错误处理和日志

### 5.1 错误处理策略
- API 调用失败重试
- 文件处理错误恢复
- 状态同步机制

### 5.2 日志记录
- 操作日志
- 错误记录
- 状态变更跟踪

## 6. 配置管理

### 6.1 配置项
```python
CONFIG = {
    'api_key': 'your-dify-api-key',
    'api_base_url': 'https://api.dify.ai/v1',
    'max_docs_per_kb': 100,
    'retry_attempts': 3,
    'retry_delay': 1,  # seconds
}
```

### 6.2 环境变量
```
DIFY_API_KEY=your-api-key
DIFY_BASE_URL=https://api.dify.ai/v1
```

## 后续步骤

1. 实现基础框架
2. 编写单元测试
3. 进行集成测试
4. 部署和监控
5. 编写使用文档

## 示例

```python
from dify import DifyClient, DatasetManager

# 初始化客户端
client = DifyClient(api_key='your_api_key')

# 创建数据集管理器
dataset_manager = DatasetManager(client)

# 上传文档
dataset_manager.create_document(
    content="文档内容",
    name="文档名称"
)

# 批量上传
documents = [
    {"content": "文档1内容", "name": "文档1"},
    {"content": "文档2内容", "name": "文档2"}
]
dataset_manager.batch_create_documents(documents)
```