# Dify 知识库导入 API 工作流程

## 任务创建与执行流程

```mermaid
sequenceDiagram
    participant Client as 客户端
    participant API as API 服务
    participant DB as 数据库
    participant Worker as 任务处理器
    participant Dify as Dify API

    Client->>API: POST /api/dify/upload/{crawler_task_id}
    API->>DB: 检查爬虫任务是否存在
    API->>API: 检查爬虫任务目录是否存在
    API->>DB: 创建Dify任务记录
    API->>Client: 返回任务ID
    
    API->>Worker: 异步启动任务
    Worker->>DB: 更新任务状态为"running"
    
    loop 处理文档
        Worker->>Worker: 处理爬虫任务目录中的文档
        Worker->>Dify: 上传文档到知识库
        Dify-->>Worker: 上传结果
    end
    
    alt 成功完成
        Worker->>DB: 更新任务状态为"completed"
        Worker->>DB: 记录处理统计信息
    else 失败
        Worker->>DB: 更新任务状态为"failed"
        Worker->>DB: 记录错误信息
    end
    
    Client->>API: GET /api/dify/task/{task_id}
    API->>DB: 查询任务状态
    API->>Client: 返回任务详情
```

## 任务状态流转图

```mermaid
stateDiagram-v2
    [*] --> pending: 任务创建
    pending --> running: 开始执行
    
    running --> completed: 成功完成
    running --> failed: 执行出错
    
    completed --> [*]: 任务结束
    failed --> [*]: 任务结束
    
    pending --> deleted: 手动删除
    running --> deleted: 手动删除
    completed --> deleted: 手动删除
    failed --> deleted: 手动删除
    
    deleted --> [*]: 清理资源
```

## 系统组件关系图

```mermaid
graph TD
    A[客户端] -->|请求| B[FastAPI 应用]
    B -->|读写| C[SQLModel 数据库]
    B -->|异步调用| D[任务处理器]
    D -->|执行| E[Dify 主程序]
    E -->|调用| F[Dify API]
    D -->|更新| C
    B -->|响应| A
    
    subgraph 数据模型
        C1[Task]
        C2[DifyTask]
        C3[DifyUploadRequest]
        C4[DifyTaskStatus]
    end
    
    subgraph API 路由
        B1[/api/dify/upload/{crawler_task_id}]
        B2[/api/dify/task/{task_id}]
        B3[/api/dify/tasks]
        B4[/api/dify/task/{task_id} DELETE]
    end
    
    C -.-> C1
    C -.-> C2
    C -.-> C3
    C -.-> C4
    
    B -.-> B1
    B -.-> B2
    B -.-> B3
    B -.-> B4
    
    C1 -->|关联| C2
```

## 文件处理流程

```mermaid
flowchart TD
    A[开始] --> B{检查爬虫任务是否存在}
    B -->|存在| C{检查爬虫任务目录是否存在}
    B -->|不存在| Z[返回错误]
    
    C -->|存在| D[创建Dify任务]
    C -->|不存在| Z
    
    D --> E[扫描爬虫任务目录中的文件]
    E --> F[按类型分组文件]
    F --> G[创建数据集]
    
    G --> H{文件数超过max_docs?}
    H -->|是| I[创建多个数据集]
    H -->|否| J[使用单个数据集]
    
    I --> K[上传文件到Dify]
    J --> K
    
    K --> L{上传成功?}
    L -->|是| M[记录成功]
    L -->|否| N[记录失败]
    
    M --> O[统计结果]
    N --> O
    
    O --> P[结束]
    Z --> P
```

## 任务关联关系

```mermaid
graph LR
    A[爬虫任务 Task] -->|产生| B[输出目录]
    B -->|作为输入| C[Dify导入任务]
    C -->|记录关联| D[extra_data.crawler_task_id]
    C -->|使用| E[Dify API]
    E -->|创建| F[Dify知识库数据集]
