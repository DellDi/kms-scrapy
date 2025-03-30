# 目录扁平化工具使用示例

本文档展示了目录扁平化工具的各种使用场景和命令行示例。

## 基础用法

将嵌套目录中的所有文件提取到一个扁平化的输出目录中，自动处理文件名冲突。

```bash
uv run -m tools.flatten_directory [输入目录] [参数选项]
```

## 参数说明

- `[输入目录]`: 要扁平化的目录路径（必填）
- `-o, --output-dir`: 输出目录路径（默认为: [输入目录]_flattened）
- `--include-hidden`: 包含隐藏文件（默认忽略）
- `--include-system-files`: 包含系统文件如.DS_Store（默认忽略）
- `--ignore`: 额外的忽略文件模式，支持正则表达式

## 常用示例

### 简单扁平化

最基本的用法，使用默认参数扁平化目录：

```bash
uv run -m tools.flatten_directory ./docs
```

### 指定输出目录

将扁平化结果输出到指定目录：

```bash
uv run -m tools.flatten_directory ./docs -o ./flat_docs
```

### 包含隐藏文件

处理时包含隐藏文件（以 `.` 开头的文件和目录）：

```bash
uv run -m tools.flatten_directory ./docs --include-hidden
```

### 忽略特定文件类型

设置忽略特定类型的文件：

```bash
uv run -m tools.flatten_directory ./docs --ignore "*.tmp" "*.bak" "*.log"
```

### 包含系统文件

处理时包含系统文件（如 .DS_Store）：

```bash
uv run -m tools.flatten_directory ./docs --include-system-files
```

### 组合使用多个选项

可以组合使用多个选项：

```bash
uv run -m tools.flatten_directory ./docs -o ./flat_output --include-hidden --ignore "*.tmp" "*.bak"
```

## 处理大型目录

对于包含大量文件的目录，工具会自动处理文件名冲突并报告处理结果：

```bash
uv run -m tools.flatten_directory ./large_docs -o ./flattened_large_docs
```

## 使用相对路径

可以使用相对路径指定输入和输出目录：

```bash
# 将当前目录下的 docs 扁平化到 flat 目录
uv run -m tools.flatten_directory ./docs -o ./flat
```

## 常见问题解决

### 权限问题

如果遇到权限不足的问题，可以使用:

```bash
sudo uv run -m tools.flatten_directory /path/to/restricted/dir -o /accessible/output/dir
```

### 文件名冲突

工具会自动为冲突的文件名添加哈希值后缀，可以在日志中看到详细信息。
