# 附件过滤流程

下面的流程图展示了附件过滤功能的工作流程：

```mermaid
flowchart TD
    A[开始处理附件] --> B{是否启用过滤?}
    B -->|否| G[创建下载请求]
    B -->|是| C[检查文件扩展名]
    C --> D{扩展名是否在排除列表?}
    D -->|是| E[跳过此附件]
    D -->|否| F[检查URL中的MIME类型]
    F --> H{MIME类型是否在排除列表?}
    H -->|是| E
    H -->|否| G
    G --> I[下载附件]
    I --> J[检查实际MIME类型]
    J --> K{实际MIME类型是否在排除列表?}
    K -->|是| E
    K -->|否| L[检查文件大小]
    L --> M{是否超过大小限制?}
    M -->|是| E
    M -->|否| N[处理附件内容]
    N --> O[结束]
    E --> O
```

## 配置说明

在 `crawler/core/config.py` 中的 `SpiderConfig` 类中，可以通过 `attachment_filters` 配置项来自定义附件过滤规则：

```python
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

## 过滤逻辑

1. **预过滤**：在下载前，根据文件扩展名和URL中的MIME类型提示进行初步过滤
2. **后过滤**：在下载后，根据实际的MIME类型和文件大小进行进一步过滤
3. **日志记录**：所有被过滤的附件都会在日志中记录，包括过滤原因
