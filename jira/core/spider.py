import logging
from typing import Dict, Optional, Generator, Any, Union
import json
import requests
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from bs4.element import Tag
from urllib.parse import urljoin, urlencode

from .auth import AuthManager, AuthError
from .config import config
from crawler.core.optimizer import OptimizerFactory

# 获取当前模块的日志记录器
logger = logging.getLogger(__name__)

# 选择器配置
SELECTORS = {
    "key": "#key-val",
    "summary": "#summary-val", 
    "description": "#description-val",
    "labels": "#wrap-labels .lozenge span",
    "customer_name": "#customfield_10000-val",
    "created_date": "#created-val time",
    "resolved_date": "#resolutiondate-val time",
    "reporter": "#reporter-val",
    "assignee": "#assignee-val",
    "status": "#resolution-val",
    "priority": "#priority-val",
    "type": "#type-val",
    "attachments": "#attachmentmodule .attachment-title"
}

class JiraIssue(BaseModel):
    """Jira问题数据模型"""

    id: str = Field(..., description="问题ID")
    key: str = Field(..., description="问题Key")
    link: str = Field(..., description="问题链接")
    summary: str = Field(..., description="问题摘要")
    description: str = Field(None, description="问题描述")
    created_date: str = Field(None, description="创建日期")
    resolved_date: str = Field(None, description="解决日期")
    customer_name: str = Field(None, description="客户名称")
    reporter: str = Field(None, description="报告人")
    assignee: str = Field(None, description="指派人")
    type_jira: str = Field(None, description="问题类型")
    status: str = Field(None, description="状态")
    priority: str = Field(None, description="优先级")
    labels: list = Field(default_factory=list, description="标签列表")
    annex_str: str = Field("", description="附件列表")
    optimized_content: Optional[str] = Field(None, description="优化后的内容")

    class Config:
        allow_none = True

def extract_value(soup: BeautifulSoup, selector: str, attr: str = None, default: Any = None) -> Any:
    """从BeautifulSoup中提取值的通用函数"""
    element = soup.select_one(selector)
    if not element:
        return default

    if attr:
        return element.get(attr, default)

    return element.text.strip()

def extract_list(soup: BeautifulSoup, selector: str) -> list:
    """从BeautifulSoup中提取列表的通用函数"""
    elements = soup.select(selector)
    return [element.text.strip() for element in elements]

def format_attachment(element: Tag) -> str:
    """格式化附件链接"""
    return f"[{element.text.strip()}]({element['href']})"

class ParseError(Exception):
    """解析异常"""
    pass

class JiraSpider:
    """Jira爬虫主类"""

    def __init__(self, auth_manager: AuthManager):
        """
        初始化爬虫
        
        Args:
            auth_manager: 认证管理器实例
        """
        self.auth_manager = auth_manager
        self.optimizer = OptimizerFactory.create_optimizer()
        self.session = requests.Session()

    def _make_request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        retry_count: int = 0,
        **kwargs,
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
                url=url, method=method, data=data_str, **kwargs
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
                logger.info("认证失败，尝试刷新认证")
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
            "layoutKey": "list-view",
        }

        # 发送请求
        response = self._make_request(
            url=url,
            method="POST",
            data=data,
            headers={
                **config.spider.default_headers,  # 使用公共headers
                # 列表接口特定headers
                "Accept": "*/*",
                "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
                "Origin": config.spider.base_url,
                "Referer": f"{config.spider.base_url}/issues/?filter=37131",
                "X-Atlassian-Token": "no-check",
                "X-Requested-With": "XMLHttpRequest",
                "__amdModuleName": "jira/issue/utils/xsrf-token-header",
            },
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
            headers={
                **config.spider.default_headers,  # 使用公共headers
                # 详情页特定headers
                "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
                "Accept-Encoding": "gzip, deflate",
                "Cache-Control": "no-cache",
                "Pragma": "no-cache",
                "Upgrade-Insecure-Requests": "1",
            },
        )

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            keyDom = soup.select_one("#key-val")

            # 获取关键信息
            key = extract_value(soup, SELECTORS["key"])
            if not key:
                raise ParseError("未找到问题关键字")

            # 修复 id 提取逻辑
            id = None
            if keyDom and "rel" in keyDom.attrs:
                rel_value = keyDom["rel"]
                # 确保获取字符串类型的 id
                id = str(rel_value[0]) if isinstance(rel_value, list) else str(rel_value)

            # 需求单地址
            link = f"{config.spider.base_url}/browse/{key}"

            # 提取基本字段
            issue_data = {
                "id": id,
                "key": key,
                "link": link,
                "summary": extract_value(soup, SELECTORS["summary"]),
                "description": extract_value(soup, SELECTORS["description"]),
                "customer_name": extract_value(soup, SELECTORS["customer_name"]),
                "created_date": extract_value(soup, SELECTORS["created_date"], "datetime"),
                "resolved_date": extract_value(soup, SELECTORS["resolved_date"], "datetime"),
                "reporter": extract_value(soup, SELECTORS["reporter"]),
                "assignee": extract_value(soup, SELECTORS["assignee"]),
                "status": extract_value(soup, SELECTORS["status"]),
                "priority": extract_value(soup, SELECTORS["priority"]),
                "type_jira": extract_value(soup, SELECTORS["type"]),
                "labels": extract_list(soup, SELECTORS["labels"]),
            }

            # 附件列表
            attachments = [format_attachment(a) for a in soup.select(SELECTORS["attachments"])]
            issue_data["annex_str"] = "\n".join(attachments)

            # 优化内容
            if issue_data["description"]:
                issue_data["optimized_content"] = self.optimizer.optimize(issue_data["description"], strip=True)

            # 记录日志
            for key, value in issue_data.items():
                if isinstance(value, str) and len(value) > 100:
                    logger.debug(f"{key}: {value[:100]}...")
                else:
                    logger.debug(f"{key}: {value}")

            return JiraIssue(**issue_data)

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
                table_html = issue_table["table"]
                # 解析问题链接
                for issue_url in self.parse_issue_table(table_html):
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
