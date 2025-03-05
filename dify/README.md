# Dify 知识库导入工具

这是一个用于将文档导入到 Dify 知识库的工具。

## 功能特性

- 自动创建和管理 Dify 知识库数据集
- 支持批量上传文档
- 自动分割大型知识库，控制每个数据集的文档数量
- 支持命令行参数配置
- 提供 API 接口，支持异步任务管理

## 使用方法

### 环境变量配置

在使用工具前，需要设置以下环境变量：

```bash
# 必须设置的环境变量
export DIFY_API_KEY="your-api-key"
export DIFY_BASE_URL="https://api.dify.ai/v1"  # 或者您的自定义 API 地址

# 以下环境变量即使不使用 AI 功能也必须存在（可以为空字符串）
export BAI_CH_API_KEK=""
export XUNFEI_API_KEY=""
```

您可以使用项目中的 `.env.crawler.template` 模板文件和 `setup_env.sh` 脚本来简化配置过程。

### 命令行参数

工具支持以下命令行参数：

```
usage: main.py [-h] [--dataset-prefix DATASET_PREFIX] [--max-docs MAX_DOCS] [--input-dir INPUT_DIR]

Dify 知识库导入工具

options:
  -h, --help            显示帮助信息并退出
  --dataset-prefix DATASET_PREFIX
                        数据集名称前缀 (默认: 大品控父子检索知识库)
  --max-docs MAX_DOCS   每个数据集的最大文档数量 (默认: 12000)
  --input-dir INPUT_DIR
                        输入目录路径 (默认: output-kms)
```

### 示例

基本用法：

```bash
python main.py
```

自定义参数：

```bash
python main.py --dataset-prefix "我的知识库" --max-docs 5000 --input-dir "my-documents"
```

## API 接口

工具提供了 RESTful API 接口，支持通过 HTTP 请求管理 Dify 知识库导入任务。

### 创建导入任务

```
POST /api/dify/upload/{crawler_task_id}
```

参数说明：
- `crawler_task_id`: 爬虫任务ID (UUID)，必须是已存在的爬虫任务，将使用该任务的输出作为导入源

请求体：

```json
{
  "dataset_prefix": "我的知识库",
  "max_docs": 5000
}
```

响应：

```json
{
  "task_id": "uuid-task-id",
  "message": "Dify知识库导入任务已建立，将处理爬虫任务 crawler-task-id 的输出"
}
```

### 查询任务状态

```
GET /api/dify/task/{task_id}
```

响应：

```json
{
  "task_id": "uuid-task-id",
  "status": "running|completed|failed|pending",
  "input_dir": "/path/to/task/dir",
  "dataset_prefix": "我的知识库",
  "max_docs": 5000,
  "created_at": "2023-03-06T10:00:00",
  "updated_at": "2023-03-06T10:05:00",
  "message": "任务状态描述",
  "total_files": 100,
  "successful_uploads": 95,
  "duration_seconds": 300
}
```

### 获取任务列表

```
GET /api/dify/tasks?skip=0&limit=10&status=completed
```

响应：

```json
{
  "tasks": [
    {
      "task_id": "uuid-task-id-1",
      "status": "completed",
      "input_dir": "/path/to/task/dir/1",
      "dataset_prefix": "我的知识库",
      "max_docs": 5000,
      "created_at": "2023-03-06T10:00:00",
      "updated_at": "2023-03-06T10:05:00",
      "message": "任务状态描述",
      "total_files": 100,
      "successful_uploads": 95,
      "duration_seconds": 300
    },
    {
      "task_id": "uuid-task-id-2",
      "status": "completed",
      "input_dir": "/path/to/task/dir/2",
      "dataset_prefix": "我的知识库2",
      "max_docs": 5000,
      "created_at": "2023-03-07T10:00:00",
      "updated_at": "2023-03-07T10:05:00",
      "message": "任务状态描述",
      "total_files": 50,
      "successful_uploads": 50,
      "duration_seconds": 150
    }
  ],
  "total": 2,
  "skip": 0,
  "limit": 10
}
```

### 删除任务

```
DELETE /api/dify/task/{task_id}
```

响应：

```json
{
  "task_id": "uuid-task-id",
  "message": "任务已成功删除"
}
```

## 支持的文件类型

工具支持以下文件类型：
- TXT
- MARKDOWN/MD
- MDX
- PDF
- HTML/HTM
- XLSX/XLS
- DOCX
- CSV

每个文件大小不应超过 15MB。

## 注意事项

- 确保您有足够的 Dify API 权限
- 大型文件可能需要更长的处理时间
- 特定类型的文件有大小限制，请参考配置文件
- API 任务会在 7 天后自动清理
- 创建 Dify 导入任务需要指定已存在的爬虫任务 ID
