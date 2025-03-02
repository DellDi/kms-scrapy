"""API服务和日志记录测试脚本."""
import sqlite3
import time
import requests

def test_api_and_logs():
    """测试API调用和日志记录."""
    base_url = "http://localhost:8000"

    print("1. 测试启动爬虫任务...")
    response = requests.post(
        f"{base_url}/api/jira/crawl",
        json={"jql": "project = DEMO"}
    )
    print(f"响应状态码: {response.status_code}")
    print(f"响应内容: {response.json()}\n")

    # 等待一下让日志写入
    time.sleep(1)

    print("2. 查询API日志...")
    log_response = requests.get(f"{base_url}/api/logs")
    logs = log_response.json()
    print(f"找到 {len(logs)} 条日志记录\n")

    if logs:
        print("最新的日志记录:")
        log = logs[0]
        print(f"路径: {log['request_path']}")
        print(f"方法: {log['request_method']}")
        print(f"状态: {log['response_status']}")
        print(f"IP: {log['client_ip']}")
        print(f"处理时间: {log['duration_ms']}ms\n")

    print("3. 直接查看数据库中的日志...")
    try:
        conn = sqlite3.connect("api/api.db")
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM api_logs")
        count = cursor.fetchone()[0]
        print(f"数据库中共有 {count} 条日志记录")

        # 获取最新的5条记录
        cursor.execute("""
            SELECT created_at, request_path, response_status, duration_ms
            FROM api_logs
            ORDER BY created_at DESC
            LIMIT 5
        """)
        print("\n最新的5条日志记录:")
        print("时间 | 路径 | 状态码 | 处理时间(ms)")
        print("-" * 60)
        for row in cursor.fetchall():
            print(f"{row[0]} | {row[1]} | {row[2]} | {row[3]}")

    except Exception as e:
        print(f"数据库查询出错: {e}")
    finally:
        cursor.close()
        conn.close()

if __name__ == "__main__":
    test_api_and_logs()