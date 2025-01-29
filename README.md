# KMS 文档爬虫系统

一个基于 Scrapy 的 Confluence KMS 系统爬虫项目，具有强大的文档处理和内容优化功能。

## 功能特性

- 🔐 支持 Confluence 系统的自动登录认证
- 📑 自动抓取文档内容和结构
- 📎 智能处理多种附件格式：
  - 图片 OCR 文字识别
  - PDF 文档解析
  - Word 文档处理
  - PowerPoint 演示文稿提取
- 🤖 集成百川 AI 进行内容优化
- 💾 结构化数据输出（JSON 格式）

## 环境要求

- Python >= 3.11
- 系统依赖：
  - Tesseract OCR（用于图片文字识别）
  - LibMagic（用于文件类型检测）
  - Poppler（用于 PDF 处理）

## 安装

1. 克隆项目并进入目录：

```bash
git clone [项目地址]
cd kms
```

2. 创建并激活虚拟环境：

```bash
python -m venv .venv
source .venv/bin/activate  # Linux/macOS
# 或
.venv\Scripts\activate  # Windows
```

3. 安装依赖：

```bash
pip install -r requirements.txt
```

4. 配置环境变量：

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
│   ├── storage/      # 数据存储模块
│   ├── utils/        # 爬虫专用工具
│   └── __init__.py
├── config/
│   └── settings.py   # 配置中心
└── tests/            # 测试用例
```

## 开发

安装开发依赖：

```bash
pip install -e ".[dev]"
```

运行测试：

```bash
pytest
```

## 许可证

MIT License