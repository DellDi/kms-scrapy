# API日志系统说明

## 功能概述

API服务现已集成SQLite数据库日志系统，可以记录所有API请求的详细信息，包括：

- 客户端IP地址
- 请求路径和方法
- 请求参数和内容
- 响应状态码和内容
- 处理时长
- 错误信息等

## 初始化数据库

首次使用前，需要初始化数据库：

```bash
# 初始化数据库（这会创建数据库文件和所需的表）
uv run -m api.init_db
```

初始化脚本会：
1. 如果存在旧的数据库文件，先删除它
2. 创建新的数据库文件（api.db）
3. 创建所需的表结构
4. 显示创建的表和字段信息

## 数据库结构

日志数据存储在`api.db`文件中的`api_logs`表中，主要字段包括：

```sql
CREATE TABLE api_logs (
    id INTEGER PRIMARY KEY,
    client_ip VARCHAR(50) NOT NULL,
    request_path VARCHAR(255) NOT NULL,
    request_method VARCHAR(10) NOT NULL,
    request_params TEXT,
    request_body TEXT,
    response_status INTEGER NOT NULL,
    response_body TEXT,
    user_agent VARCHAR(255),
    created_at TIMESTAMP NOT NULL,
    duration_ms INTEGER,
    error_message TEXT
);
```

## 查看日志

### 1. 通过API接口

可以使用API接口查看日志记录：

```bash
# 获取最新的10条日志
curl http://localhost:8000/api/logs

# 使用分页参数
curl http://localhost:8000/api/logs?skip=0&limit=20

# 按路径筛选
curl http://localhost:8000/api/logs?path=/api/jira

# 按状态码筛选
curl http://localhost:8000/api/logs?status=200
```

### 2. 使用测试脚本

运行测试脚本查看日志：

```bash
uv run -m api.test_api_logs
```

### 3. 直接查询数据库

使用SQLite客户端直接查询数据库：

```bash
sqlite3 api/api.db

# 查看最新的10条日志
SELECT created_at, request_path, response_status, duration_ms
FROM api_logs
ORDER BY created_at DESC
LIMIT 10;

# 查看特定路径的请求
SELECT * FROM api_logs
WHERE request_path LIKE '%/api/jira%';

# 查看错误请求
SELECT * FROM api_logs
WHERE response_status >= 400;
```

## 日志保留策略

目前系统不会自动清理日志数据。如需清理，可以：

1. 手动删除旧数据：
```sql
DELETE FROM api_logs
WHERE created_at < datetime('now', '-30 days');
```

2. 备份并重建数据库：
```bash
# 备份当前数据库
sqlite3 api/api.db ".backup 'backup.db'"

# 重新初始化数据库
uv run -m api.init_db
```

## 开发说明

1. 日志中间件位于 `api/middleware/logging.py`
2. 数据库模型位于 `api/database/models.py`
3. 数据库工具类位于 `api/database/db.py`
4. 数据库初始化脚本位于 `api/init_db.py`

如需添加新的日志字段：
1. 修改`api/database/models.py`中的`ApiLog`类
2. 重新运行初始化脚本以更新表结构

## 监控建议

1. 定期检查日志大小：
```bash
ls -lh api/api.db
```

2. 监控错误率：
```sql
SELECT
    date(created_at) as day,
    count(*) as total,
    sum(case when response_status >= 400 then 1 else 0 end) as errors,
    round(sum(case when response_status >= 400 then 1 else 0 end) * 100.0 / count(*), 2) as error_rate
FROM api_logs
GROUP BY date(created_at)
ORDER BY day DESC;
```

3. 分析响应时间：
```sql
SELECT
    request_path,
    avg(duration_ms) as avg_duration,
    max(duration_ms) as max_duration,
    count(*) as requests
FROM api_logs
GROUP BY request_path
ORDER BY avg_duration DESC;