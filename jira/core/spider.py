import logging
from typing import Dict, Optional, Generator, Any, Union
import json
import requests
from bs4 import BeautifulSoup
from dataclasses import dataclass
from datetime import datetime
from urllib.parse import urljoin, urlencode

from .auth import AuthManager, AuthError
from .config import config
from crawler.core.optimizer import OptimizerFactory

# 配置日志
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

@dataclass
class JiraIssue:
    """Jira问题数据模型"""
    id: str
    key: str
    summary: str
    description: str
    created_date: str
    resolved_date: str
    reporter: str
    assignee: str
    status: str
    priority: str
    optimized_content: Optional[str] = None

class ParseError(Exception):
    """解析异常"""
    pass

class JiraSpider:
    """Jira爬虫主类"""

    def __init__(self):
        """初始化爬虫"""
        self.auth_manager = AuthManager()
        self.optimizer = OptimizerFactory.create_optimizer()
        self.session = requests.Session()

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        retry_count: int = 0,
        **kwargs
    ) -> requests.Response:
        """
        发送HTTP请求

        Args:
            url: 请求URL
            method: 请求方法
            data: 请求数据
            retry_count: 当前重试次数
            **kwargs: 其他请求参数

        Returns:
            requests.Response: 响应对象

        Raises:
            AuthError: 认证失败
            requests.RequestException: 请求失败
        """
        try:
            # 创建请求
            data_str = urlencode(data) if data else None
            request = self.auth_manager.create_authenticated_request(
                url=url,
                method=method,
                data=data_str,
                **kwargs
            )

            # 准备请求
            prepped = self.session.prepare_request(request)

            # 添加日志
            logger.debug(f"Making request to {url}")
            logger.debug(f"Method: {method}")
            logger.debug(f"Headers: {json.dumps(dict(prepped.headers), indent=2)}")
            if data:
                logger.debug(f"Data: {json.dumps(data, indent=2)}")

            # 发送请求
            response = self.session.send(prepped)

            # 记录响应信息
            logger.debug(f"Response Status: {response.status_code}")
            logger.debug(f"Response Headers: {json.dumps(dict(response.headers), indent=2)}")
            if response.status_code != 200:
                logger.error(f"Response Content: {response.text}")

            # 检查是否需要认证
            if response.status_code == 401 and retry_count < config.spider.retry_times:
                logger.info("认证失败，尝试刷新认证信息")
                if self.auth_manager.refresh_authentication():
                    return self._make_request(
                        url=url,
                        method=method,
                        data=data,
                        retry_count=retry_count + 1,
                        **kwargs
                    )

            # 检查其他需要重试的状态码
            if (
                response.status_code in config.spider.retry_http_codes
                and retry_count < config.spider.retry_times
            ):
                logger.info(f"请求失败(状态码:{response.status_code})，正在重试({retry_count + 1})")
                return self._make_request(
                    url=url,
                    method=method,
                    data=data,
                    retry_count=retry_count + 1,
                    **kwargs
                )

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            if retry_count < config.spider.retry_times:
                logger.warning(f"请求异常，正在重试({retry_count + 1}): {str(e)}")
                return self._make_request(
                    url=url,
                    method=method,
                    data=data,
                    retry_count=retry_count + 1,
                    **kwargs
                )
            raise

    def get_issue_table(self, start_index: int = 0) -> tuple[str, Dict[str, Any]]:
        """
        获取问题列表表格

        Args:
            start_index: 起始索引

        Returns:
            tuple[str, dict]: (表格HTML内容, 分页信息)
        """
        url = f"{config.spider.base_url}/rest/issueNav/1/issueTable"
        data = {
            "startIndex": start_index,
            "filterId": 37131,
            "jql": (
                "project in (PMS, V10) AND "
                "created >= 2024-01-01 AND "
                "resolved <= 2025-01-01 "
                "ORDER BY created ASC"
            ),
            "layoutKey": "list-view"
        }

        # 发送请求
        response = self._make_request(
            url=url,
            method="POST",
            data=data,
            headers={
                "Origin": config.spider.base_url,
                "Referer": f"{config.spider.base_url}/issues/?filter=37131"
            }
        )

        # 解析响应
        try:
            result = response.json()
            if not isinstance(result, dict):
                logger.error("Unexpected response format")
                logger.debug(f"Response content: {response.text}")
                raise ParseError("Response is not a JSON object")

            issue_table = result.get("issueTable", "")
            pagination = result.get("pagination", {})

            if not issue_table:
                logger.warning("Empty issue table in response")
                logger.debug(f"Full response: {json.dumps(result, indent=2)}")

            return issue_table, pagination

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            logger.debug(f"Response content: {response.text[:1000]}...")
            raise ParseError("解析问题列表响应失败") from e
        except Exception as e:
            logger.error(f"解析响应失败: {str(e)}")
            logger.debug(f"Response content: {response.text[:1000]}...")
            raise ParseError("解析问题列表响应失败") from e

    def parse_issue_table(self, html: str) -> Generator[str, None, None]:
        """
        解析问题列表表格

        Args:
            html: 表格HTML内容

        Yields:
            str: 问题详情页URL
        """
        if not html:
            logger.warning("空的HTML内容")
            return

        try:
            soup = BeautifulSoup(html, "html.parser")
            logger.debug(f"解析HTML内容: {len(html)} 字符")

            rows = soup.select("tr")
            if not rows:
                logger.warning("未找到表格行")
                logger.debug(f"HTML内容: {html[:500]}...")
                return

            for row in rows:
                issue_key_cell = row.select_one("td.issuekey")
                if issue_key_cell:
                    issue_link = issue_key_cell.select_one("a")
                    if issue_link and issue_link.get("href"):
                        url = urljoin(config.spider.base_url, issue_link["href"])
                        logger.debug(f"找到问题链接: {url}")
                        yield url

        except Exception as e:
            logger.error(f"解析问题表格失败: {str(e)}")
            logger.debug(f"HTML内容: {html[:500]}...")
            raise ParseError("解析问题表格失败") from e

    def get_issue_detail(self, url: str) -> JiraIssue:
        """
        获取问题详情

        Args:
            url: 问题详情页URL

        Returns:
            JiraIssue: 问题数据对象
        """
        # 发送请求
        response = self._make_request(
            url=url,
            headers={"Referer": f"{config.spider.base_url}/issues/?filter=37131"}
        )

        try:
            soup = BeautifulSoup(response.text, "html.parser")

            # 提取问题信息
            key = soup.select_one("#key-val").text.strip()
            id_elem = soup.select_one("#issue_id_a")
            id = id_elem["rel"] if id_elem else ""
            summary = soup.select_one("#summary-val").text.strip()
            description = soup.select_one("#description-val").text.strip()

            # 提取字段值
            created_date = soup.select_one("#created-val time")["datetime"]
            resolved_date = soup.select_one("#resolutiondate-val time")["datetime"]
            reporter = soup.select_one("#reporter-val").text.strip()
            assignee = soup.select_one("#assignee-val").text.strip()
            status = soup.select_one("#status-val span").text.strip()
            priority = soup.select_one("#priority-val").text.strip()

            # 优化内容
            optimized_content = self.optimizer.optimize(description)

            return JiraIssue(
                id=id,
                key=key,
                summary=summary,
                description=description,
                created_date=created_date,
                resolved_date=resolved_date,
                reporter=reporter,
                assignee=assignee,
                status=status,
                priority=priority,
                optimized_content=optimized_content
            )

        except (AttributeError, KeyError) as e:
            logger.error(f"解析问题详情失败: {str(e)}")
            logger.debug(f"Response content: {response.text[:1000]}...")
            raise ParseError(f"解析问题详情失败: {str(e)}") from e

    def crawl(self) -> Generator[JiraIssue, None, None]:
        """
        爬取Jira问题

        Yields:
            JiraIssue: 问题数据对象
        """
        start_index = 0

        while True:
            try:
                # 获取问题列表
                logger.info(f"获取问题列表，起始索引: {start_index}")
                issue_table, pagination = self.get_issue_table(start_index)

                # 解析问题链接
                for issue_url in self.parse_issue_table(issue_table):
                    try:
                        logger.info(f"处理问题: {issue_url}")
                        # 获取问题详情
                        issue = self.get_issue_detail(issue_url)
                        yield issue
                    except Exception as e:
                        logger.error(f"处理问题详情失败({issue_url}): {str(e)}")
                        continue

                # 检查是否还有下一页
                if not pagination.get("next"):
                    logger.info("已到达最后一页")
                    break

                # 更新起始索引
                start_index = pagination.get("start", 0) + pagination.get("max", 50)
                logger.info(f"处理下一页，新的起始索引: {start_index}")

            except Exception as e:
                logger.error(f"处理问题列表失败: {str(e)}")
                break
