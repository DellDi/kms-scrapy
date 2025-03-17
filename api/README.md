# KMS-Scrapy API服务

这个目录包含了KMS-Scrapy的API服务实现，用于提供Jira爬虫的启动、状态查询和结果获取功能。

## 目录结构

```
api/
├── README.md        - 主要说明文档
├── README_LOGS.md   - 日志系统说明文档
├── api_service.py   - API服务主要实现
├── test_api.py      - API测试脚本
├── test_api_logs.py - 日志测试脚本
├── database/        - 数据库相关
│   ├── db.py       - 数据库连接
│   └── models.py    - 数据模型
├── middleware/      - 中间件
│   └── logging.py   - 日志中间件
└── models/          - API模型
    ├── request.py   - 请求模型
    └── response.py  - 响应模型
```

## API文档

服务启动后，可以通过以下地址访问API文档：

- **ReDoc文档**：http://localhost:8000/api/redoc
  - 清晰、优雅的API文档界面
  - 支持分组展示和搜索
  - 包含详细的参数说明和示例

- **Swagger UI**：http://localhost:8000/api/docs
  - 交互式API文档界面
  - 支持直接在页面测试API
  - 提供OpenAPI规范下载

- **OpenAPI JSON**：http://localhost:8000/api/openapi.json
  - OpenAPI规范的JSON格式
  - 可用于生成客户端代码
  - 支持第三方工具导入

- **OpenAPI YAML**：http://localhost:8000/api/openapi.yaml
  - OpenAPI规范的YAML格式
  - 更易于阅读和编辑
  - 适合版本控制和文档管理
  - 支持导入到API设计工具

## 主要功能

### 1. 爬虫任务管理
- 启动爬虫任务（POST /api/jira/crawl）
- 查询任务状态（GET /api/jira/task/{task_id}）
- 下载爬取结果（GET /api/jira/download/{task_id}）

### 2. 系统监控
- 查询API日志（GET /api/logs）
- 支持按路径、状态码筛选
- 支持分页查询

## 日志系统

集成了基于SQLite的日志系统，详见 [日志系统说明](./README_LOGS.md)。

## 运行服务

使用以下命令启动API服务：

```bash
uv run -m api.main
```

服务默认在 http://localhost:8000 启动。

## 测试

运行测试脚本：

```bash
# 测试基本API功能
uv run -m api.test_api

# 测试日志系统
uv run -m api.test_api_logs
```

## 依赖

主要依赖包括：
- fastapi - API框架
- uvicorn - ASGI服务器
- sqlalchemy - ORM框架
- pydantic - 数据验证

安装依赖：

```bash
uv pip install -e .
```

## 错误处理

API服务提供标准的错误响应：
- 404 - 资源未找到
- 400 - 请求参数错误
- 500 - 服务器内部错误

## 安全性

- 所有API请求都会被记录
- 支持CORS跨域请求
- 可配置API访问限制

## 后续计划

1. 添加用户认证
2. 实现任务取消功能
3. 添加任务优先级
4. 支持批量任务处理