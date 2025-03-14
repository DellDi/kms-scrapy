# 更新日志

## [0.3.1] - 2025-03-05

- 修改 Dify 知识库导入 API 服务逻辑：
  - 修改 `/api/dify/upload` 接口为 `/api/dify/upload/{crawler_task_id}`，要求指定已存在的爬虫任务
  - 使用爬虫任务的输出目录作为 Dify 导入的输入源，不再创建新的临时目录
  - 添加对爬虫任务存在性和目录存在性的检查
  - 在 `DifyTask` 的 `extra_data` 中记录关联的爬虫任务 ID
  - 删除任务时不再删除目录，因为目录可能被其他任务使用
  - 移除未实现的文件上传接口

## [0.3.0] - 2025-03-06

- 添加 Dify 知识库导入 API 服务：
  - 新增 `/api/dify/upload` 接口，支持异步启动知识库导入任务
  - 新增 `/api/dify/task/{task_id}` 接口，支持查询任务状态
  - 新增 `/api/dify/tasks` 接口，支持分页查询任务列表
  - 新增 `/api/dify/task/{task_id}` DELETE 接口，支持删除任务
  - 集成到主应用，支持定期清理过期任务
- 添加 `DifyTask` 数据模型，用于记录任务状态和进度
- 支持异步执行导入任务，不阻塞 API 响应

## [0.2.0] - 2025-03-05

- 新增命令行参数解析功能，支持以下参数：
  - `--dataset-prefix`: 控制数据集名称前缀
  - `--max-docs`: 控制每个数据集的最大文档数量
  - `--input-dir`: 控制输入目录路径
- 修改 `DatasetManager` 类，支持外部传入参数
- 添加 README.md 文件，包含使用说明和参数说明

## [0.1.0] - 初始版本

- 实现基本的 Dify 知识库导入功能
- 支持自动创建和管理数据集
- 支持批量上传文档
- 支持自动分割大型知识库
