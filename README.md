# KMS 文档爬虫系统

一个基于 Scrapy 的 Confluence KMS 系统爬虫项目，具有强大的文档处理和内容优化功能。同时支持Jira系统的问题数据抓取，以及Dify知识库的数据集成。

## 功能特性

- 🔐 支持多系统认证
  - Confluence 系统的自动登录认证
  - Jira 系统的 Basic 认证和 Cookie 管理
  - Dify API的密钥认证
- 📑 自动抓取文档内容和结构
  - 智能提取文档标题和正文
  - 保持文档层级关系
  - 支持批量文档爬取
  - 支持 Jira 问题列表和详情抓取
- 📎 智能处理多种附件格式：
  - 图片 OCR 文字识别
  - PDF 文档文本提取
  - Word 文档内容解析
  - PowerPoint 演示文稿内容提取
- 🤖 AI增强功能
  - 集成百川 AI 进行内容优化
    - 文本内容智能总结
    - 关键信息提取
    - 文档结构优化
  - 集成 Dify 知识库
    - 自动创建知识库
    - 批量上传文档
    - 知识库检索和问答
- 💾 结构化数据输出
  - Confluence文档输出（JSON 格式）
  - Jira问题导出（Markdown 格式）
  - Dify知识库同步

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
cd kms-scrapy
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
uv run crawler/main.py
```

爬取的数据将保存在 `output` 目录下的 JSON 文件中。

### Jira 爬虫

1. 运行爬虫：

```bash
uv run jira/main.py
```

爬取的数据将保存在 `output-jira` 目录下，按页码组织的Markdown文件：

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

在 `.env` 文件中设置 Dify API密钥和端点：

```env
DIFY_API_KEY=your-api-key
DIFY_API_ENDPOINT=https://your-dify-instance/v1
```

2. 上传文档到知识库：

```bash
uv run dify/examples/upload_documents.py
```

这将：
- 自动创建知识库（如果不存在）
- 批量上传处理后的文档
- 支持文档更新和版本管理

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
