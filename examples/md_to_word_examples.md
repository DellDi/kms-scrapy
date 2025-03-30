# Markdown 转 Word 工具使用示例

本文档展示了 Markdown 转 Word 工具的各种使用场景和命令行示例。

## 基础用法

将 Markdown 文件转换为 Word 文档格式，支持保留格式和样式。

```bash
uv run -m tools.md_to_word [输入目录] [参数选项]
```

## 参数说明

- `[输入目录]`: 包含 Markdown 文件的目录路径（必填）
- `-o, --output-dir`: 输出 Word 文档的目录路径（默认为: [输入目录]_word）
- `--flat`: 扁平化输出，不保留原始目录结构
- `--template`: 自定义 Word 模板路径
- `--preserve-structure`: 保留原始目录结构（默认）
- `--page-size`: 分页大小，每个文件夹包含的最大文件数

## 常用示例

### 基本转换

最基本的用法，使用默认参数将目录中的 Markdown 文件转换为 Word 文档：

```bash
uv run -m tools.md_to_word ./docs
```

### 指定输出目录

将转换结果输出到指定目录：

```bash
uv run -m tools.md_to_word ./docs -o ./word_docs
```

### 扁平化输出

不保留原始目录结构，将所有 Markdown 文件转换为同一目录下的 Word 文档：

```bash
uv run -m tools.md_to_word ./docs --flat
```

### 使用自定义模板

使用自定义的 Word 模板进行转换：

```bash
uv run -m tools.md_to_word ./docs --template ./template.docx
```

### 分页输出

设置分页大小，每个子目录最多包含指定数量的文件：

```bash
uv run -m tools.md_to_word ./docs --page-size 100
```

### 组合使用多个选项

可以组合使用多个选项：

```bash
uv run -m tools.md_to_word ./docs -o ./formatted_docs --template ./template.docx --flat
```

## 处理大型文档集

对于包含大量 Markdown 文件的目录，使用分页功能可以更好地组织输出：

```bash
uv run -m tools.md_to_word ./large_docs -o ./word_output --page-size 50 --preserve-structure
```

## 转换单个文件

也可以转换单个 Markdown 文件（工具会自动处理）：

```bash
# 将单个 Markdown 文件转换为 Word
uv run -m tools.md_to_word ./docs/single_file.md -o ./word_output
```

## 常见问题解决

### 样式问题

如果转换后的样式不符合预期，可以尝试使用自定义模板：

```bash
uv run -m tools.md_to_word ./docs --template ./better_template.docx
```

### 中文内容支持

工具已针对中文内容进行优化，无需额外参数：

```bash
uv run -m tools.md_to_word ./chinese_docs
```

### 图片处理

工具会自动处理 Markdown 中的图片引用，确保在 Word 中正确显示：

```bash
uv run -m tools.md_to_word ./docs_with_images
```
