# Jira导出器设计

## 1. 导出器类设计

```python
class DocumentExporter:
    """文档导出处理类"""

    def __init__(self, config: ExporterConfig):
        self.config = config
        self.base_dir = config.output_dir

    def export_issue(self, issue: JiraIssue, page_num: int) -> tuple[str, str]:
        """
        导出单个问题到Markdown文件

        Args:
            issue: JiraIssue对象
            page_num: 页码

        Returns:
            tuple[str, str]: (markdown文件路径, 目录路径)
        """
```

## 2. 目录结构设计

```
output-jira/                    # 输出根目录
├── page1/                     # 第一页问题
│   ├── PMS-123.md            # 问题文件(使用问题Key命名)
│   └── V10-456.md
├── page2/
│   ├── PMS-124.md
│   └── V10-457.md
└── ...
```

## 3. Markdown文档格式

### 3.1 基本结构
```markdown
# [PMS-123] 问题标题

## 基本信息

- **创建时间**: 2024-01-15 10:30:00
- **解决时间**: 2024-01-16 15:45:00
- **报告人**: 张三
- **经办人**: 李四
- **状态**: 已解决
- **优先级**: 高

## 问题描述

[优化后的描述内容]

## 解决方案

[优化后的解决方案内容]

## 备注

[其他相关信息]
```

### 3.2 附件处理
- 将图片转换为图片链接
- 其他附件转换为下载链接
- 保持原始文件名

## 4. 实现细节

### 4.1 文件路径生成
```python
def generate_paths(self, issue: JiraIssue, page_num: int) -> tuple[str, str]:
    """
    生成文件和目录路径

    Args:
        issue: JiraIssue对象
        page_num: 页码

    Returns:
        tuple[str, str]: (文件路径, 目录路径)
    """
    # 生成分页目录
    page_dir = os.path.join(self.base_dir, f"{self.config.page_dir_prefix}{page_num}")

    # 生成文件路径
    file_path = os.path.join(page_dir, f"{issue.key}.md")

    return file_path, page_dir
```

### 4.2 内容格式化
```python
def format_content(self, issue: JiraIssue) -> str:
    """
    格式化问题内容为Markdown格式

    Args:
        issue: JiraIssue对象

    Returns:
        str: 格式化后的Markdown内容
    """
    template = textwrap.dedent("""
        # [{key}] {summary}

        ## 基本信息

        - **创建时间**: {created_date}
        - **解决时间**: {resolved_date}
        - **报告人**: {reporter}
        - **经办人**: {assignee}
        - **状态**: {status}
        - **优先级**: {priority}

        ## 问题描述

        {description}

        ## 解决方案

        {solution}

        ## 备注

        {notes}
    """)

    return template.format(**issue.__dict__)
```

### 4.3 文件写入
```python
def write_file(self, content: str, file_path: str):
    """
    写入文件内容

    Args:
        content: 文件内容
        file_path: 文件路径
    """
    # 确保目录存在
    os.makedirs(os.path.dirname(file_path), exist_ok=True)

    # 写入文件
    with open(file_path, 'w', encoding=self.config.encoding) as f:
        f.write(content)
```

## 5. 异常处理

### 5.1 潜在异常
1. 文件系统异常
   - 目录创建失败
   - 文件写入失败
   - 权限不足

2. 内容处理异常
   - 编码错误
   - 格式化失败

### 5.2 处理策略
```python
def safe_export(self, issue: JiraIssue, page_num: int) -> bool:
    """
    安全导出问题内容

    Args:
        issue: JiraIssue对象
        page_num: 页码

    Returns:
        bool: 是否导出成功
    """
    try:
        # 生成路径
        file_path, dir_path = self.generate_paths(issue, page_num)

        # 格式化内容
        content = self.format_content(issue)

        # 写入文件
        self.write_file(content, file_path)

        return True

    except Exception as e:
        logger.error(f"导出失败: {str(e)}")
        return False
```

## 6. 性能优化

### 6.1 批量处理
```python
def batch_export(self, issues: list[JiraIssue], page_num: int):
    """
    批量导出问题

    Args:
        issues: JiraIssue对象列表
        page_num: 页码
    """
    # 创建页面目录
    page_dir = os.path.join(self.base_dir, f"{self.config.page_dir_prefix}{page_num}")
    os.makedirs(page_dir, exist_ok=True)

    # 并行处理内容格式化
    with concurrent.futures.ThreadPoolExecutor() as executor:
        futures = {
            executor.submit(self.format_content, issue): issue
            for issue in issues
        }

        # 等待所有格式化完成并写入文件
        for future in concurrent.futures.as_completed(futures):
            issue = futures[future]
            try:
                content = future.result()
                file_path = os.path.join(page_dir, f"{issue.key}.md")
                self.write_file(content, file_path)
            except Exception as e:
                logger.error(f"处理失败 {issue.key}: {str(e)}")
```

### 6.2 缓存优化
- 缓存模板渲染结果
- 复用文件句柄
- 预创建目录结构

## 7. 监控和日志

### 7.1 性能指标
- 文件写入时间
- 内容格式化时间
- 批处理效率

### 7.2 日志记录
- 导出成功/失败统计
- 文件路径记录
- 异常详细信息

### 7.3 状态追踪
- 导出进度
- 文件数量统计
- 存储空间使用