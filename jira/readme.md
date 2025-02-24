# Jira爬虫工具

一个用于抓取Jira系统问题数据并导出为Markdown文档的爬虫工具。

## 功能特性

- 支持分页获取问题列表
- 自动下载问题附件
- 集成文本优化处理
- 支持命令行参数配置
- 完整的日志记录系统

## 目录结构

```
jira/
├── core/
│   ├── __init__.py
│   ├── auth.py          # 认证管理
│   ├── spider.py        # 爬虫核心逻辑
│   ├── exporter.py      # 文档导出
│   └── config.py        # 配置管理
├── main.py              # 主程序入口
└── readme.md           # 说明文档
```

## 输出结构

```
output-jira/
├── page1/                     # 分页目录
│   ├── PMS-123.md            # 问题文件
│   ├── PMS-123-attachments/  # 问题专属附件目录
│   │   ├── file1.pdf
│   │   └── file2.docx
│   └── PMS-124.md
└── page2/
    ├── PMS-456.md
    └── PMS-456-attachments/  # 仅在有附件时创建
        └── file3.xlsx
```

## 使用方法

### 基本使用

```bash
# 使用默认配置运行
python jira/main.py
```

### 自定义参数

```bash
# 指定每页数量和起始位置
python jira/main.py --page-size 100 --start-at 0

# 自定义JQL查询条件
python jira/main.py --jql "project in (PMS, V10) AND created >= 2024-01-01"
```

## 配置说明

### 环境变量配置

```bash
# 认证信息
JIRA_AUTH_USERNAME=your-username
JIRA_AUTH_PASSWORD=your-password

# API地址
JIRA_SPIDER_BASE_URL=http://your-jira-server
```

### 配置文件

配置类位于 `core/config.py`：

```python
@dataclass
class Config:
    auth: AuthConfig         # 认证配置
    spider: SpiderConfig     # 爬虫配置
    optimizer: OptimizerConfig  # 优化器配置
    exporter: ExporterConfig   # 导出配置
```

## 日志系统

- 日志文件：`logs-jira/jira_spider_[timestamp].log`
- 文件日志级别：DEBUG（完整日志）
- 控制台日志级别：INFO（关键信息）

## 主要功能

### 1. 问题列表获取

- 支持分页获取问题列表
- 自动处理分页逻辑
- 可配置每页数量

### 2. 问题详情处理

- 提取问题基本信息
- 下载相关附件
- 优化问题描述文本

### 3. 文档导出

- Markdown格式导出
- 分页目录管理
- 附件关联管理

## 异常处理

- 网络请求异常自动重试
- 认证失效自动刷新
- 详细的错误日志记录

## 性能优化

- 控制请求频率
- 支持断点续传
- 批量文档处理

## 依赖项目

- requests：网络请求
- beautifulsoup4：HTML解析
- pydantic：数据模型