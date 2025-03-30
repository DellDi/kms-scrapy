# 一键扁平化并转换为 Word 工具使用示例

本文档展示了一键扁平化并转换工具的各种使用场景和命令行示例。该工具结合了目录扁平化和 Markdown 转 Word 的功能。

## 基础用法

一键完成目录扁平化和 Markdown 转 Word 处理流程：

```bash
uv run -m tools.flatten_and_convert [输入目录] [参数选项]
```

## 参数说明

- `[输入目录]`: 要处理的目录路径（必填）
- `-o, --output-dir`: 输出目录路径（默认为: [输入目录]_converted）
- `--skip-flatten`: 跳过扁平化步骤，直接转换为 Word
- `--skip-word`: 只执行扁平化，不转换为 Word
- `--no-convert`: 不转换，直接复制文件
- `--preserve-structure`: 保留目录结构
- `--page-size`: 分页功能，每页文件数量
- `--overwrite`: 覆盖输出目录
- `--copy-non-md`: 复制非 Markdown 文件到目标目录

## 常用示例

### 基本用法

最基本的用法，使用默认参数进行扁平化和转换：

```bash
uv run -m tools.flatten_and_convert ./docs

```

### 指定输出目录

将处理结果输出到指定目录：

```bash
uv run -m tools.flatten_and_convert ./docs -o ./processed_docs
```

### 跳过扁平化步骤

直接将 Markdown 文件转换为 Word，保持原有目录结构：

```bash
uv run -m tools.flatten_and_convert ./docs --skip-flatten
```

### 只执行扁平化

只进行目录扁平化，不转换为 Word 文档：

```bash
uv run -m tools.flatten_and_convert ./docs --skip-word
```

### 保留目录结构

在转换过程中保留原始目录结构：

```bash
uv run -m tools.flatten_and_convert ./docs --preserve-structure
```

### 分页功能

使用分页功能，每页包含指定数量的文件：

```bash
uv run -m tools.flatten_and_convert ./docs --page-size 100
```

### 覆盖输出目录

覆盖已存在的输出目录：

```bash
uv run -m tools.flatten_and_convert ./docs -o ./existing_output --overwrite
```

### 复制非 Markdown 文件

同时将非 Markdown 文件（如图片、PDF等）复制到输出目录：

```bash
uv run -m tools.flatten_and_convert ./docs --copy-non-md
```

### 不转换直接复制

跳过 Markdown 转 Word 步骤，直接复制文件到输出目录：

```bash
uv run -m tools.flatten_and_convert ./docs --no-convert
```

## 高级组合用法

### 转换并保留目录结构

转换为 Word 文档，保留目录结构，覆盖输出目录：

```bash
uv run -m tools.flatten_and_convert ./docs -o ./word_output --preserve-structure --overwrite
```

### 带分页的文档处理

使用分页功能，每页100个文件，保留目录结构：

```bash
uv run -m tools.flatten_and_convert ./docs -o ./paged_output --page-size 100 --preserve-structure
```

### 完整文档处理流程

转换为 Word 文档，保留目录结构，同时复制非 Markdown 文件到目标目录：

```bash
uv run -m tools.flatten_and_convert ./docs -o ./complete_output --preserve-structure --copy-non-md
```

### 实际案例

处理爬虫输出目录，转换为带分页的 Word 文档集合：

```bash
uv run -m tools.flatten_and_convert api/temp_scrapy/2ea4d312-12b8-496a-b941-dbdc5ce08b22 -o temp_word_with_non_md --page-size 100 --preserve-structure --overwrite --copy-non-md
```

## 常见问题解决

### 内存问题

对于非常大的目录，建议使用分页功能减少内存占用：

```bash
uv run -m tools.flatten_and_convert ./very_large_docs --page-size 50
```

### 文件覆盖

如果需要重复运行工具处理同一目录，可以使用 `--overwrite` 参数覆盖已有输出：

```bash
uv run -m tools.flatten_and_convert ./docs -o ./output --overwrite
```

### 复杂结构处理

对于具有深层嵌套结构的目录，建议使用保留结构模式：

```bash
uv run -m tools.flatten_and_convert ./complex_docs --preserve-structure
```
