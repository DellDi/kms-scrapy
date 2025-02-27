# KMS-Scrapy API服务

这个目录包含了KMS-Scrapy的API服务实现，用于提供Jira爬虫的启动、状态查询和结果获取功能。

## 目录结构

- `design_doc.md` - API服务设计文档
- `api_service.py` - API服务主要实现（待开发）
- `models/` - 数据模型目录（待开发）

## 设计概述

API服务采用简单的三接口设计：
1. 启动爬虫任务接口
2. 查询任务状态接口
3. 获取爬虫结果接口(ZIP包)

详细设计请参考 [设计文档](./design_doc.md)。

## 开发计划

1. 实现API服务基础框架
2. 实现爬虫任务管理
3. 实现ZIP打包功能
4. 集成现有爬虫

## 使用方法

待开发完成后更新。

## 开发环境

本项目使用uv进行Python依赖管理。添加新依赖时，请更新`pyproject.toml`文件，然后运行：

```bash
uv pip install -e .
```

API服务将需要以下依赖：
- FastAPI
- Uvicorn
- Pydantic
- Requests

这些依赖将在实现阶段添加到项目的`pyproject.toml`文件中。

## 启动服务

开发完成后，可以使用以下命令启动API服务：

```bash
uv run -m api.api_service
```
