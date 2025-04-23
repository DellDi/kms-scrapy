# 知识库生成工具使用手册

## 1. 概述

知识库生成工具是一个灵活、可扩展的框架，用于从数据库中提取数据并生成结构化的知识库文档。目前支持指标知识库生成，未来可扩展到项目知识库等其他类型。

本工具基于插件架构设计，可以轻松添加新的知识库类型，而不需要修改核心代码。

## 2. 安装与配置

### 2.1 依赖安装

确保已安装以下依赖：

```bash
# 使用uv安装依赖
uv pip install pymysql openai python-dotenv
```

### 2.2 环境变量配置

在项目根目录创建`.env`文件，配置以下环境变量：

```
# 数据库配置
MYSQL_HOST=localhost
MYSQL_PORT=3306
MYSQL_USER=root
MYSQL_PASSWORD=your_password
MYSQL_DATABASE=newsee-view

# OpenAI配置
OPENAI_API_KEY=your_api_key
OPENAI_MODEL=gpt-3.5-turbo
OPENAI_BASE_URL=https://api.openai.com/v1
```

## 3. 基本使用

### 3.1 生成指标知识库

默认情况下，工具会生成指标知识库：

```bash
# 生成所有类型的指标文档
uv run -m tools.gen-target --output ./output/docs

# 只生成特定类型的指标文档
uv run -m tools.gen-target --category 1 --output ./output/docs

# 限制每种类型处理的指标数量（用于测试）
uv run -m tools.gen-target --limit 10 --output ./output/docs

# 不使用LLM丰富指标数据
uv run -m tools.gen-target --no-llm --output ./output/docs
```

### 3.2 命令行参数说明

| 参数 | 简写 | 描述 | 默认值 |
|------|------|------|--------|
| `--output` | `-o` | 输出目录 | `./output/docs` |
| `--generator` | `-g` | 生成器类型 | `target` |
| `--category` | `-c` | 指定要处理的类别ID | 无（处理所有类别） |
| `--limit` | `-l` | 限制每种类别处理的项目数量 | `0`（不限制） |
| `--no-llm` | 无 | 不使用LLM增强内容 | `false` |
| `--concurrency` | 无 | LLM请求并发数 | `1` |
| `--delay` | 无 | LLM请求间隔延迟(秒) | `0.5` |

## 4. 输出格式

### 4.1 指标知识库

生成的指标知识库文档格式如下：

```markdown
# Type_1 指标知识库

生成时间: 2025-04-23 15:30:00

本文档包含 50 个指标项

## 指标 ID: metric_net_profit
标准名称: 净利润
别名: 纯利润, 税后利润, Net Profit, Net Income, 利润
定义: 总收入减去所有费用，包括税费和利息。
单位: 元
常用维度: 项目, 时间, 产品线
相关术语: 收入, 成本, 费用, 盈利

---

## 指标 ID: metric_gross_margin
...
```

### 4.2 索引文档

同时会生成一个索引文档，列出所有类别：

```markdown
# 知识库索引

生成时间: 2025-04-23 15:30:00

## 目录

- [Type_1](./Type_1.md) (50 个项目)
- [Type_2](./Type_2.md) (30 个项目)
- ...
```

## 5. 扩展新的知识库类型

要添加新的知识库类型，需要按照以下步骤操作：

### 5.1 创建新的生成器类

在`generators`目录下创建新的生成器文件，例如`project_generator.py`：

```python
from core.base_generator import BaseGenerator
from core.db import MySQLConnector
from core.llm import LLMEnricher
from core.doc_generator import DocGenerator

class ProjectItem:
    """项目数据模型"""
    
    def __init__(self, data):
        # 初始化项目数据
        self.id = data.get("id")
        self.name = data.get("name", "")
        # ...其他属性
    
    def to_markdown(self):
        # 转换为Markdown格式
        return f"""## 项目 ID: {self.id}
名称: {self.name}
...
"""

class ProjectGenerator(BaseGenerator):
    """项目知识库生成器"""
    
    async def initialize(self):
        # 初始化代码
        return True
    
    async def get_categories(self):
        # 获取项目类别
        # 例如：按项目状态、类型等分类
        return {1: "进行中项目", 2: "已完成项目"}
    
    async def get_items(self, category_id=None):
        # 获取项目数据
        # ...SQL查询代码
        return []
    
    def create_item(self, data):
        # 创建项目对象
        return ProjectItem(data)
    
    def get_prompt_generator(self):
        # 返回提示词生成函数
        def generate_prompt(item):
            return f"""
请根据以下项目信息，补充该项目的关键词、技术栈和相关项目。
...
"""
        return generate_prompt
    
    def get_result_processor(self):
        # 返回结果处理函数
        def process_result(item, data):
            # 处理LLM返回的结果
            return item
        return process_result
```

### 5.2 注册新的生成器

在`__main__.py`中注册新的生成器：

```python
def register_generators():
    """注册所有知识库生成器"""
    factory.register("target", TargetGenerator)
    factory.register("project", ProjectGenerator)  # 添加这一行
```

### 5.3 使用新的生成器

现在可以使用新的生成器类型：

```bash
uv run -m tools.gen-target --generator project --output ./output/project-docs
```

## 6. 故障排除

### 6.1 数据库连接问题

如果遇到数据库连接问题，请检查：
- `.env`文件中的数据库配置是否正确
- 数据库服务是否运行
- 网络连接是否正常

### 6.2 LLM调用问题

如果遇到LLM调用问题，请检查：
- OpenAI API密钥是否正确
- 网络连接是否正常
- 可以尝试使用`--no-llm`参数跳过LLM增强

### 6.3 日志查看

工具会输出详细的日志信息，可以通过查看日志了解执行过程和可能的错误：

```
2025-04-23 15:30:00 - gen-target.db - INFO - 成功连接到数据库 newsee-view
2025-04-23 15:30:01 - gen-target.target - INFO - 获取到 5 个类别
2025-04-23 15:30:02 - gen-target.target - INFO - 获取到类别 1 的 50 个项目
...
```

## 7. 最佳实践

- 首次运行时，建议使用`--limit`参数限制处理的项目数量，以验证配置是否正确
- 使用`--no-llm`参数可以加快生成速度，但会缺少AI增强的内容
- 对于大量数据，可以考虑增加`--concurrency`参数提高并发数，但注意不要超过API限制
- 定期备份生成的知识库文档
