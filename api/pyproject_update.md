# pyproject.toml 更新建议

在实现API服务时，需要在项目的`pyproject.toml`文件中添加以下依赖：

```toml
# 在[project]的dependencies列表中添加
"fastapi>=0.100.0",
"uvicorn>=0.23.0",
```

完整的依赖部分将类似于：

```toml
[project]
# ... 其他配置 ...
dependencies = [
    # ... 现有依赖 ...
    "fastapi>=0.100.0",
    "uvicorn>=0.23.0",
]
```

添加依赖后，使用以下命令安装：

```bash
uv pip install -e .
```

这将安装项目及其所有依赖，包括新添加的FastAPI和Uvicorn。

## 启动服务

使用uv启动API服务：

```bash
uv run -m api.api_service
```

这将使用uv运行api.api_service模块，启动API服务。
