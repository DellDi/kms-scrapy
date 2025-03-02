"""API服务测试脚本."""
import requests

def test_crawler_api():
    """测试爬虫API的基本功能."""
    # 启动爬虫任务
    response = requests.post(
        "http://localhost:8000/api/jira/crawl",
        json={"jql": "project = DEMO"}
    )
    print("\n1. 启动爬虫任务:")
    print(response.json())

    if response.status_code == 200:
        task_id = response.json()["task_id"]

        # 查询任务状态
        status_response = requests.get(
            f"http://localhost:8000/api/jira/task/{task_id}"
        )
        print("\n2. 查询任务状态:")
        print(status_response.json())

if __name__ == "__main__":
    test_crawler_api()