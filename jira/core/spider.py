import logging
import html2text
from typing import Dict, Optional, Generator, Any, Union, List
import json
import os
import requests
from pydantic import BaseModel, Field
from bs4 import BeautifulSoup
from bs4.element import Tag

from jira.core.auth import AuthManager, AuthError
from jira.core.config import config
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
    "attachments": "#attachmentmodule .attachment-content .attachment-title",
    "comments": ".issue-data-block .twixi-wrap.verbose",
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
    annex_str: str = Field("", description="附件列表Markdown格式")
    comments_str: str = Field("", description="评论列表Markdown格式")
    annex_urls: List[Dict[str, str]] = Field(default_factory=list, description="附件URL列表")
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


def format_attachment(element: Tag, key: str) -> tuple[str, Dict[str, str]]:
    """
    格式化附件链接，返回Markdown格式的链接和元数据

    Args:
        element: 附件元素

    Returns:
        tuple[str, Dict[str, str]]: (Markdown格式链接, 附件元数据)
    """
    title = element.text.strip()
    url = element["href"]
    # /secure/attachment/355909/screenshot-1.png => f"{key}-attachment/355909/screenshot-1.png
    # md_link = f"{key}-attachments{url.replace('/secure/attachment', '')}"
    md_link = f"{config.spider.base_url}{url}"
    logger.info(f"Attachment URL: {url}")
    return f"[{title}]({md_link})", {"name": title, "url": url}


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
        params: Optional[Dict] = None,
        data: Optional[Union[Dict, str]] = None,
        retry_count: int = 0,
        **kwargs,
    ) -> requests.Response:
        """
        发送HTTP请求

        Args:
            url: 请求URL
            method: 请求方法
            params: URL参数
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
            request = self.auth_manager.create_authenticated_request(
                url=url, method=method, params=params, data=data, **kwargs
            )

            # 准备请求
            prepped = self.session.prepare_request(request)

            # 添加日志
            logger.debug(f"Making request to {url}")
            logger.debug(f"Method: {method}")
            logger.debug(f"Headers: {json.dumps(dict(prepped.headers), indent=2)}")
            if data:
                logger.debug(f"Data: {data}")
            if params:
                logger.debug(f"Params: {params}")

            # 发送请求
            response = self.session.send(prepped, stream=True)

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
                        params=params,
                        data=data,
                        retry_count=retry_count + 1,
                        **kwargs,
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
                    params=params,
                    data=data,
                    retry_count=retry_count + 1,
                    **kwargs,
                )

            response.raise_for_status()
            return response

        except requests.RequestException as e:
            if retry_count < config.spider.retry_times:
                logger.warning(f"请求异常，正在重试({retry_count + 1}): {str(e)}")
                return self._make_request(
                    url=url,
                    method=method,
                    params=params,
                    data=data,
                    retry_count=retry_count + 1,
                    **kwargs,
                )
            raise

    def get_issue_table(self, start_index: int = 0) -> tuple[List[str], Dict[str, Any]]:
        """
        获取问题列表数据

        Args:
            start_index: 起始索引

        Returns:
            tuple[list[str], dict]: (问题key列表, 分页信息)
        """
        url = f"{config.spider.base_url}/rest/api/2/search"

        # 发送请求
        response = self._make_request(
            url=url,
            method="GET",
            params={
                "startAt": start_index,
                "jql": config.spider.jql,
                "maxResults": config.spider.page_size,
                "fields": "key",
            },
            headers={
                **config.spider.default_headers,
                "Accept": "application/json",
            },
        )

        # 解析响应
        try:
            result = response.json()
            if not isinstance(result, dict):
                logger.error("Unexpected response format")
                logger.debug(f"Response content: {response.text}")
                raise ParseError("Response is not a JSON object")

            # 获取issues列表和分页信息
            issues = result.get("issues", [])  # issues直接在根级别
            start_at = result.get("startAt", 0)
            max_results = result.get("maxResults", config.spider.page_size)
            total = result.get("total", 0)
            pagination = {
                "total": total,
                "startAt": start_at,
                "maxResults": max_results,
                "next": (start_at + max_results) < total,
            }
            if not issues:
                logger.warning("Empty issues list in response")
                logger.debug(f"Full response: {json.dumps(result, indent=2)}")
                return [], pagination

            # 提取issue keys
            issue_keys = []
            for issue in issues:
                if issue_key := issue.get("key"):
                    issue_keys.append(issue_key)
                    logger.debug(f"Found issue key: {issue_key}")

            return issue_keys, pagination

        except json.JSONDecodeError as e:
            logger.error(f"JSON解析失败: {str(e)}")
            logger.debug(f"Response content: {response.text[:1000]}...")
            raise ParseError("解析问题列表响应失败") from e
        except Exception as e:
            logger.error(f"解析响应失败: {str(e)}")
            logger.debug(f"Response content: {response.text[:1000]}...")
            raise ParseError("解析问题列表响应失败") from e

    def download_attachment(self, url: str, page_dir: str, issue_key: str, filename: str) -> bool:
        """
        下载附件

        Args:
            url: 附件URL
            page_dir: 分页目录路径
            issue_key: 问题Key
            filename: 文件名

        Returns:
            bool: 下载是否成功
        """
        try:
            # 创建问题专属的附件目录
            attachment_dir = os.path.join(page_dir, f"{issue_key}-attachments")
            os.makedirs(attachment_dir, exist_ok=True)
            # 构造完整的文件路径
            file_path = os.path.join(attachment_dir, filename)

            # 下载文件
            response = self._make_request(
                url=url, headers={**config.spider.default_headers, "Accept": "*/*"}
            )

            # 判断文件大小限制
            content_length = int(response.headers.get("Content-Length", "0"))
            if content_length > config.attachment_filters.size_limit:
                logger.warning(f"附件大小超过限制: {filename} ({content_length} B)")
                return False

            # 写入文件
            with open(file_path, "wb") as f:
                for chunk in response.iter_content(chunk_size=8192):
                    if chunk:
                        f.write(chunk)

            logger.info(f"下载附件成功: {filename}")
            return True

        except Exception as e:
            logger.error(f"下载附件失败({filename}): {str(e)}")
            return False

    def get_issue_detail(self, url: str, page_dir: str) -> JiraIssue:
        """
        获取问题详情

        Args:
            url: 问题详情页URL
            page_dir: 分页目录路径

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

        # 获取评论接口响应，和原始明细接口保持一致，但请求头不一样
        response_comment = self._make_request(
            url=url,
            headers={
                **config.spider.default_headers,  # 使用公共headers
                # 评论接口特定headers
                "Accept": "*/*",
                "X-PJAX": "true",
                "X-Requested-With": "XMLHttpRequest",
            },
        )

        try:
            soup = BeautifulSoup(response.text, "html.parser")
            keyDom = soup.select_one("#key-val")
            soup_comment = BeautifulSoup(response_comment.text, "html.parser")

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
                "resolved_date": extract_value(soup, SELECTORS["resolved_date"], "datetime", ""),
                "reporter": extract_value(soup, SELECTORS["reporter"]),
                "assignee": extract_value(soup, SELECTORS["assignee"]),
                "status": extract_value(soup, SELECTORS["status"]),
                "priority": extract_value(soup, SELECTORS["priority"]),
                "type_jira": extract_value(soup, SELECTORS["type"]),
                "labels": extract_list(soup, SELECTORS["labels"]),
            }
            # 限制描述长度
            description_limit = config.exporter.description_limit
            if description_limit > 0:
                issue_data["description"] = issue_data["description"][:description_limit]

            # 处理附件
            attachments = []
            annex_urls = []
            for a in soup.select(SELECTORS["attachments"]):
                if "href" in a.attrs:
                    md_link, meta = format_attachment(a, issue_data["key"])
                    attachments.append(md_link)
                    annex_urls.append(meta)
                    # 下载附件,检查附件类型,非排除列表中的类型才下载
                    if meta["name"].lower().endswith(config.attachment_filters.included_extensions):
                        self.download_attachment(
                            url=meta["url"],
                            page_dir=page_dir,
                            issue_key=issue_data["key"],
                            filename=meta["name"],
                        )
                    else:
                        logger.warning(f"附件类型不在限制内: {meta['name']} : ({meta['url']})")
            issue_data["annex_str"] = "\n".join(attachments)
            issue_data["annex_urls"] = annex_urls

            # 限制评论长度
            comments_limit = config.exporter.comments_limit

            # 评论内容md格式
            commentsDomList = soup_comment.select(SELECTORS["comments"])
            # 只取文本的节点，不包含a标签
            for dom in commentsDomList:
                for a in dom.select("a"):
                    a.decompose()

            commentsDomList = [str(dom) for dom in commentsDomList]
            if comments_limit > 0:
                commentsDomList = commentsDomList[:comments_limit]

            commentsDom = "\n".join(commentsDomList)
            if commentsDom:
                # html2text 处理全部dom为md
                comments_str = html2text.html2text(str(commentsDom))
                issue_data["comments_str"] = comments_str

            else:
                issue_data["comments_str"] = "暂无评论内容"
            # 优化内容
            if issue_data["description"]:
                issue_data["optimized_content"] = self.optimizer.optimize(issue_data["description"])

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

    def crawl(
        self, start_at: int = 0, page_size: int = 500, output_dir: str = "output-jira"
    ) -> Generator[JiraIssue, None, None]:
        """
        爬取Jira问题

        Yields:
            JiraIssue: 问题数据对象
        """
        start_index = start_at

        while True:
            try:
                # 获取问题列表
                logger.info(f"获取问题列表，起始索引: {start_index}")
                issue_keys, pagination = self.get_issue_table(start_index)

                # 计算当前分页目录
                current_page = (start_index // page_size) + 1
                page_dir = os.path.join(
                    output_dir, f"{config.exporter.page_dir_prefix}{current_page}"
                )

                # 获取每个问题的详情
                for key in issue_keys:
                    try:
                        url = f"{config.spider.base_url}/browse/{key}"
                        logger.info(f"处理问题: {url}")
                        issue = self.get_issue_detail(url, page_dir)
                        yield issue
                    except Exception as e:
                        logger.error(f"处理问题详情失败({key}): {str(e)}")
                        continue

                # 检查是否还有下一页
                if not pagination.get("next"):
                    logger.info("已到达最后一页")
                    break

                # 更新起始索引
                start_index += pagination.get("maxResults", page_size)
                logger.info(f"处理下一页，新的起始索引: {start_index}")

            except Exception as e:
                logger.error(f"处理问题列表失败: {str(e)}")
                break
