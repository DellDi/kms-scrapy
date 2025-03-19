# 文档爬虫与知识库管理系统

一个基于 FastAPI 和 Scrapy 的综合文档管理系统，提供统一的 API 服务和多源数据采集能力。支持 Confluence 文档爬取、Jira 数据抓取、以及 Dify 知识库管理，并提供完整的 RESTful API 接口。

## 功能特性

- 支持多系统认证
  - Confluence 系统的自动登录认证
  - Jira 系统的 Basic 认证和 Cookie 管理
  - Dify API 的密钥认证
- 自动抓取文档内容和结构
  - 智能提取文档标题和正文
  - 保持文档层级关系
  - 支持批量文档爬取
  - 支持 Jira 问题列表和详情抓取
- 智能处理多种附件格式：
  - 图片 OCR 文字识别
  - PDF 文档文本提取
  - Word 文档内容解析
  - PowerPoint 演示文稿内容提取
- AI 增强功能
  - 集成百川 AI 进行内容优化
    - 文本内容智能总结
    - 关键信息提取
    - 文档结构优化
  - 集成 Dify 知识库
    - 自动创建知识库
    - 批量上传文档
    - 知识库检索和问答
- 结构化数据输出

  - Confluence 文档输出（JSON 格式）
  - Jira 问题导出（Markdown 格式）
  - Dify 知识库同步

- 统一 API 服务
  - RESTful API 接口设计
  - Swagger/ReDoc 接口文档
  - 多源数据任务管理
  - 自动任务清理机制
  - 完整的日志追踪系统
  - 跨域请求支持(CORS)

## 环境要求

- Python >= 3.11
- 系统依赖：
  - **Tesseract OCR**
    - 用于图片和 PDF 文字识别
    - macOS: `brew install tesseract tesseract-lang`
    - Ubuntu: `sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim`
    - Windows: 下载安装[Tesseract 安装包](https://github.com/UB-Mannheim/tesseract/wiki)
  - **Poppler**
    - 用于 PDF 文件处理
    - macOS: `brew install poppler`
    - Ubuntu: `sudo apt-get install poppler-utils`
    - Windows: 下载[Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)
  - **LibMagic**
    - 用于文件类型检测
    - macOS: `brew install libmagic`
    - Ubuntu: `sudo apt-get install libmagic1`
    - Windows: 需要预先安装 Visual C++ Build Tools，然后通过 pip 安装 pylibmagic
      ```bash
      # 安装 Visual C++ Build Tools
      # 1. 下载 Visual Studio Build Tools: https://visualstudio.microsoft.com/visual-cpp-build-tools/
      # 2. 运行安装程序，选择"Desktop development with C++"
      # 3. 安装完成后再安装 pylibmagic
      pip install pylibmagic
      ```

## 安装

1. 克隆项目并进入目录：

```bash
git clone [项目地址]
cd kms
```

2. 使用 uv 安装依赖（推荐）：

```bash
pip install uv  # 首先安装 uv
uv venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

uv pip install -e .  # 通过 pyproject.toml 安装项目及其依赖
```

或者使用传统的 pip 安装：

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows

pip install -r requirements.txt
```

3. 配置环境变量：

```bash
cp .env.template .env
# 编辑 .env 文件，填入必要的配置信息，包括：
# - Confluence认证信息
# - Jira认证信息
# - Dify API密钥
```

## 使用方法

### Confluence 爬虫

1. 配置爬虫参数：

在 `main.py` 中设置目标 URL 和认证信息：

```python
process.crawl(
    ConfluenceSpider,
    start_url='your-confluence-url'
)
```

2. 配置附件过滤（可选）：

在 `crawler/core/config.py` 中修改 `SpiderConfig` 类的 `attachment_filters` 配置：

```python
# 附件过滤配置
attachment_filters: Dict[str, Any] = {
    # 排除的MIME类型列表
    "excluded_mime_types": ["image/jpeg", "image/png", "image/gif", "image/svg+xml"],
    # 排除的文件扩展名列表
    "excluded_extensions": [".jpg", ".jpeg", ".png", ".gif", ".svg"],
    # 最大附件大小(MB)，超过此大小的附件将被跳过
    "max_size_mb": 50,
    # 是否启用附件过滤
    "enabled": True,
}
```

3. 运行爬虫：

```bash
uv run crawler/main.py [参数选项]
```

支持的命令行参数：

- `--output_dir`: 输出目录路径（默认：output）
- `--start_url`: 起始知识库 URL
- `--callback_url`: 爬取完成后的回调 URL

例如：

```bash
uv run crawler/main.py \
  --output_dir="./output" \
  --start_url="http://kms.example.com/pages/123" \
  --callback_url="http://localhost:8000/api/callback"
```

爬取的数据将保存在 `output` 目录下的 JSON 文件中。

### Jira 爬虫

1. 运行爬虫：

```bash
uv run jira/main.py [参数选项]
```

支持的命令行参数：

- `--page_size`: 每页问题数量
- `--start_at`: 起始页码
- `--jql`: JQL 查询条件
- `--description_limit`: 问题描述截断长度
- `--comments_limit`: 问题评论个数
- `--output_dir`: 输出目录
- `--callback_url`: 爬取完成后的回调 URL

例如：

```bash
uv run jira/main.py \
  --page_size=50 \
  --start_at=0 \
  --jql="project = PMS" \
  --description_limit=1000 \
  --comments_limit=10 \
  --output_dir="./output-jira" \
  --callback_url="http://localhost:8000/api/callback"
```

爬取的数据将保存在 `output-jira` 目录下，按页码组织的 Markdown 文件：

```
output-jira/
├── page1/
│   ├── PMS-123.md  # 使用问题Key作为文件名
│   └── V10-456.md
└── page2/
    ├── PMS-124.md
    └── V10-457.md
```

### Dify 集成

1. 配置 Dify API：

在 `.env` 文件中设置 Dify API 密钥和端点：

```env
DIFY_API_KEY=your-api-key
DIFY_API_ENDPOINT=https://your-dify-instance/v1
```

2. 上传文档到知识库：

```bash
uv run dify/main.py [参数选项]
```

支持的命令行参数：

- `--dataset-prefix`: 数据集名称前缀，用于创建或识别知识库（默认：KMS-）
- `--max-docs`: 每个数据集的最大文档数量（默认: 100）
- `--input-dir`: 输入目录路径，包含要上传的文档（默认: ./output）

例如：

```bash
uv run dify/main.py \
  --dataset-prefix="KMS-" \
  --max-docs=200 \
  --input-dir="./output"
```

这将：

- 自动创建知识库（如果不存在）
- 批量上传处理后的文档
- 支持文档更新和版本管理

### API 服务

统一的 API 服务提供了对爬虫任务和知识库管理的集中控制。

1. 配置服务：

在 `.env` 文件中设置 API 服务配置：

```env
API_ROOT_PATH=/api  # API根路径（可选）
API_ROOT_PORT=8000  # API服务端口
```

2. 启动服务：

```bash
uv run api/main.py
```

3. 访问 API 文档：

- Swagger UI: http://localhost:8000/api/docs
- ReDoc: http://localhost:8000/api/redoc

4. 主要端点：

- `/api/jira/tasks`: Jira 爬虫任务管理
- `/api/kms/tasks`: KMS 爬虫任务管理
- `/api/dify/tasks`: Dify 知识库任务管理
- `/api/logs`: API 请求日志查询

5. 特性：

- RESTful API 设计
- 自动的任务清理（7 天）
- 详细的请求日志记录
- 支持跨域请求(CORS)
- OpenAPI/Swagger 文档

### 工具集

#### 目录扁平化工具

将嵌套目录中的所有文件提取到一个扁平化的输出目录中，自动处理文件名冲突。

```bash
uv run -m tools.flatten_directory [输入目录] [参数选项]
```

支持的命令行参数：

- `[输入目录]`: 要扁平化的目录路径（必填）
- `-o, --output-dir`: 输出目录路径（默认为: [输入目录]\_flattened）
- `--include-hidden`: 包含隐藏文件（默认忽略）
- `--include-system-files`: 包含系统文件如.DS_Store（默认忽略）
- `--ignore`: 额外的忽略文件模式，支持正则表达式

例如：

```bash
# 基本用法
uv run -m tools.flatten_directory ./docs

# 指定输出目录
uv run -m tools.flatten_directory ./docs -o ./flat_docs

# 包含隐藏文件但忽略特定模式
uv run -m tools.flatten_directory ./docs --include-hidden --ignore "*.tmp" "*.bak"
```

工具会自动：

- 忽略系统文件（如 .DS_Store）和隐藏文件
- 处理文件名冲突（通过添加文件哈希值）
- 保留原始文件的元数据（修改时间等）

#### Markdown 转 Word 工具

将 Markdown 文件转换为 Word 文档格式，支持保留格式和样式。

```bash
# 基本用法
uv run -m tools.md_to_word ./docs

# 指定输出目录
uv run -m tools.md_to_word ./docs -o ./word_docs

# 扁平化输出（不保留目录结构）
uv run -m tools.md_to_word ./docs --flat

# 使用自定义模板
uv run -m tools.md_to_word ./docs --template ./template.docx
```

工具支持：

- 保留 Markdown 格式（标题、列表、表格、代码块等）
- 保留原始目录结构或扁平化输出
- 使用自定义 Word 模板
- 中文内容优化

#### 一键扁平化并转换为 Word

结合上述两个工具的功能，一键完成目录扁平化和 Markdown 转 Word 的处理流程。

```bash
# 基本用法
uv run -m tools.flatten_and_convert ./docs

# 指定最终输出目录
uv run -m tools.flatten_and_convert ./docs -o ./processed_docs

# 跳过扁平化步骤，直接转换为 Word
uv run -m tools.flatten_and_convert ./docs --skip-flatten

# 只执行扁平化，不转换为 Word
uv run -m tools.flatten_and_convert ./docs --skip-word

# 使用分页功能，每页100个文件，保留目录结构
uv run -m tools.flatten_and_convert 输入目录 -o 输出目录 --page-size 100 --preserve-structure

# 跳过转换，直接复制文件，覆盖输出目录
uv run -m tools.flatten_and_convert 输入目录 -o 输出目录 --no-convert --overwrite

# 转换为Word文档，保留目录结构，覆盖输出目录
uv run -m tools.flatten_and_convert 输入目录 -o 输出目录 --preserve-structure --overwrite

# 转换为Word文档，同时复制非Markdown文件到目标目录
uv run -m tools.flatten_and_convert 输入目录 -o 输出目录 --copy-non-md

# 转换为Word文档，保留目录结构，同时复制非Markdown文件到目标目录
uv run -m tools.flatten_and_convert 输入目录 -o 输出目录 --preserve-structure --copy-non-md
uv run -m tools.flatten_and_convert api/temp_scrapy/2ea4d312-12b8-496a-b941-dbdc5ce08b22 -o temp_word_with_non_md --page-size 100 --preserve-structure --overwrite --copy-non-md
```

工具支持：

- 一键完成从嵌套目录到 Word 文档的转换
- 灵活控制处理流程和输出位置
- 保留所有子工具的高级选项

## 项目结构

```
├── crawler/          # Confluence爬虫模块
│   ├── core/           # 爬虫核心逻辑
│   │   ├── auth.py     # 认证和会话管理
│   │   ├── config.py   # 配置管理模块
│   │   ├── content.py  # 内容解析和处理
│   │   ├── exporter.py # 文档导出工具
│   │   ├── optimizer.py # AI 内容优化
│   │   └── spider.py   # 爬虫主程序
│   └── test/           # 测试用例
├── jira/            # Jira爬虫模块
│   ├── core/          # 核心实现
│   │   ├── auth.py    # 认证管理
│   │   ├── config.py  # 配置管理
│   │   ├── spider.py  # 爬虫实现
│   │   └── exporter.py # 导出功能
│   └── main.py      # Jira爬虫入口
├── dify/            # Dify集成模块
│   ├── api/          # API客户端
│   ├── core/         # 核心功能
│   │   └── knowledge_base.py # 知识库管理
│   ├── examples/     # 使用示例
│   └── utils/        # 工具函数
├── tools/           # 实用工具集合
│   └── flatten_directory.py # 目录扁平化工具
│   └── md_to_word.py # Markdown 转 Word 工具
│   └── flatten_and_convert.py # 一键扁平化并转换为 Word
├── api/             # API服务模块
│   ├── database/     # 数据库模型和配置
│   │   ├── db.py      # 数据库连接管理
│   │   └── models.py  # SQLModel数据模型
│   ├── middleware/   # 中间件组件
│   │   └── logging.py # 请求日志中间件
│   ├── models/      # 请求响应模型
│   ├── api_service.py    # Jira接口服务
│   ├── api_kms_service.py # KMS接口服务
│   ├── dify_service.py   # Dify接口服务
│   └── common.py    # 通用功能模块
├── output/          # Confluence输出目录
│   ├── docs/          # Markdown 文档
│   └── attachments/   # 附件文件
├── output-jira/     # Jira输出目录
├── .env            # 环境变量配置
├── .env.template   # 环境变量模板
├── main.py        # Confluence爬虫入口
├── pyproject.toml # 项目配置和依赖
├── requirements.txt # 依赖清单
└── uv.lock       # UV 锁定文件
```

## 开发

安装开发依赖：

```bash
uv pip install -e .
```

运行测试：

```bash
pytest
```

## 许可证

MIT License
