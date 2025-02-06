# KMS 文档爬虫系统

一个基于 Scrapy 的 Confluence KMS 系统爬虫项目，具有强大的文档处理和内容优化功能。

## 功能特性

- 🔐 支持 Confluence 系统的自动登录认证
- 📑 自动抓取文档内容和结构
  - 智能提取文档标题和正文
  - 保持文档层级关系
  - 支持批量文档爬取
- 📎 智能处理多种附件格式：
  - 图片 OCR 文字识别
  - PDF 文档文本提取
  - Word 文档内容解析
  - PowerPoint 演示文稿内容提取
- 🤖 集成百川 AI 进行内容优化
  - 文本内容智能总结
  - 关键信息提取
  - 文档结构优化
- 💾 结构化数据输出（JSON 格式）

## 环境要求

- Python >= 3.11
- 系统依赖：
  - **Tesseract OCR**
    - 用于图片和PDF文字识别
    - macOS: `brew install tesseract tesseract-lang`
    - Ubuntu: `sudo apt-get install tesseract-ocr tesseract-ocr-chi-sim`
    - Windows: 下载安装[Tesseract安装包](https://github.com/UB-Mannheim/tesseract/wiki)
  - **Poppler**
    - 用于PDF文件处理
    - macOS: `brew install poppler`
    - Ubuntu: `sudo apt-get install poppler-utils`
    - Windows: 下载[Poppler for Windows](http://blog.alivate.com.au/poppler-windows/)
  - **LibMagic**
    - 用于文件类型检测
    - macOS: `brew install libmagic`
    - Ubuntu: `sudo apt-get install libmagic1`
    - Windows: 包含在Windows版Python包中

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

或者使用传统的pip安装：

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
# 编辑 .env 文件，填入必要的配置信息
```

## 使用方法

1. 配置爬虫参数：

在 `main.py` 中设置目标 URL 和认证信息：

```python
process.crawl(
    ConfluenceSpider,
    start_url='your-confluence-url'
)
```

2. 运行爬虫：

```bash
python main.py
```

爬取的数据将保存在 `output` 目录下的 JSON 文件中。

## 项目结构

```
├── crawler/
│   ├── core/         # 爬虫核心逻辑
│   │   ├── auth.py   # 认证模块
│   │   ├── content.py # 内容解析模块
│   │   ├── spider.py  # 爬虫主模块
│   │   └── optimizer.py # AI优化模块
│   └── test/         # 测试用例
├── main.py          # 程序入口
└── pyproject.toml   # 项目配置和依赖管理
```

## 开发

安装开发依赖：

```bash
uv pip install -e ".[dev]"
```

运行测试：

```bash
pytest
```

## 许可证

MIT License