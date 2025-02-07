from bs4 import BeautifulSoup
from scrapy.http import Request
from urllib.parse import urlencode, parse_qs
import logging
import time


class TreeExtractor:
    """处理 Confluence 页面导航树提取的专用类"""

    def __init__(self, common_headers_callback):
        self.logger = logging.getLogger(__name__)
        self._get_common_headers = common_headers_callback

    def process_tree_container(self, response, soup):
        """处理页面中的导航树容器"""
        tree_container = soup.select_one(".plugin_pagetree")

        if not tree_container:
            self.logger.info("当前页面没有导航树")
            return None

        # 获取隐藏字段中的参数
        fieldset = tree_container.select_one("fieldset.hidden")
        if not fieldset:
            self.logger.info("无法获取导航树参数")
            return None

        try:
            # 获取基本参数
            params = {
                "decorator": "none",
                "excerpt": "false",
                "sort": "position",
                "reverse": "false",
                "disableLinks": "false",
                "expandCurrent": "true",
                "hasRoot": "true",
                "pageId": fieldset.select_one('input[name="rootPageId"]')["value"],
                "treeId": "0",
                "startDepth": fieldset.select_one('input[name="startDepth"]')["value"],
                "mobile": fieldset.select_one('input[name="mobile"]')["value"],
                "treePageId": fieldset.select_one('input[name="treePageId"]')["value"],
            }

            # 获取祖先ID列表
            ancestor_ids = [
                input_["value"]
                for input_ in fieldset.select('fieldset.hidden input[name="ancestorId"]')
            ]
            params["ancestors"] = ancestor_ids

            # 构建完整的请求URL
            tree_url = response.urljoin("/plugins/pagetree/naturalchildren.action")
            tree_url = f"{tree_url}?{urlencode(params, doseq=True)}"

            self.logger.info(f"获取到的导航树参数: {params}")

            # 构建并返回请求
            headers = self._get_common_headers()
            headers.update({"x-requested-with": "XMLHttpRequest"})

            return Request(
                url=tree_url,
                callback=self.parse_tree_ajax,
                headers=headers,
                meta={
                    "original_url": response.url,
                    "dont_merge_cookies": True,
                    "handle_httpstatus_list": [302, 200],
                },
                dont_filter=True,
            )

        except Exception as e:
            self.logger.error(f"处理导航树参数时出错: {str(e)}")
            return None

    def _expand_node(self, response, page_id, tree_params=None):
        """创建展开节点的请求"""
        params = {
            "decorator": "none",
            "excerpt": "false",
            "sort": "position",
            "reverse": "false",
            "disableLinks": "false",
            "expandCurrent": "true",
            "hasRoot": "true",
            "pageId": page_id,
            "treeId": "0",
            "startDepth": "0",
            "mobile": "false",
            "_": int(time.time() * 1000),  # 添加时间戳参数
        }

        # 如果提供了tree_params，使用其中的treePageId
        if tree_params and 'treePageId' in tree_params:
            params['treePageId'] = tree_params['treePageId']

        tree_url = response.urljoin("/plugins/pagetree/naturalchildren.action")
        tree_url = f"{tree_url}?{urlencode(params)}"

        headers = self._get_common_headers()
        headers.update({"x-requested-with": "XMLHttpRequest"})

        return Request(
            url=tree_url,
            callback=self.parse_tree_ajax,
            headers=headers,
            meta={
                "original_url": response.url,
                "dont_merge_cookies": True,
                "handle_httpstatus_list": [302, 200],
                "is_expansion": True,  # 标记这是一个节点展开请求
            },
            dont_filter=True,
        )

    def parse_tree_ajax(self, response):
        """处理导航树Ajax响应"""
        try:
            # 使用BeautifulSoup解析HTML响应
            soup = BeautifulSoup(response.text, "html.parser")

            # 获取当前活动节点
            original_url = response.meta.get("original_url")
            page_links_all = soup.select('a[href*="viewpage.action"]')

            # 如果是节点展开请求，直接处理返回的链接
            if response.meta.get("is_expansion"):
                page_links = page_links_all
            else:
                # 否则按原逻辑查找活动节点
                page_id = original_url.split("=")[-1]
                page_links = [link for link in page_links_all if page_id in link["href"]]
                active_node = page_links[0].find_parent("ul") if page_links else None
                if active_node:
                    page_links = active_node.select('a[href*="viewpage.action"]')

            self.logger.info(f"成功获取导航树数据: {len(page_links)}个页面")

            # 1. 首先在active_node中处理未展开节点
            if not response.meta.get("is_expansion") and active_node:
                # 获取必要的参数
                url_params = parse_qs(original_url.split("?")[-1])
                tree_params = {
                    'treePageId': url_params.get('pageId', [None])[0]
                }
                
                # 在active_node中查找未展开节点
                unexpanded_nodes = active_node.select("a.aui-iconfont-chevron-right")
                for node in unexpanded_nodes:
                    li_node = node.find_parent("li")
                    if li_node and li_node.select_one("span.plugin_pagetree_children_span"):
                        # 从父节点中找到对应的页面链接
                        page_link = li_node.select_one('a[href*="viewpage.action"]')
                        if page_link:
                            # 从URL中提取pageId
                            page_url = page_link["href"]
                            query_params = parse_qs(page_url.split("?")[-1])
                            if "pageId" in query_params:
                                page_id = query_params["pageId"][0]
                                # 创建展开该节点的请求，传递必要参数
                                yield self._expand_node(response, page_id, tree_params)

            # 2. 处理当前层级的所有页面链接
            for link in page_links:
                page_url = response.urljoin(link["href"])
                title = link.get_text(strip=True)
                self.logger.info(f"处理页面: {title} -> {page_url}")
                headers = self._get_common_headers()
                yield Request(
                    url=page_url,
                    callback=self.parse_content_callback,
                    headers=headers,
                    dont_filter=True,
                    meta={"dont_merge_cookies": True, "handle_httpstatus_list": [302, 200]},
                )

        except Exception as e:
            self.logger.error(f"解析导航树HTML数据失败: {str(e)}")
            if not response.meta.get("is_expansion"):  # 只对非展开请求记录原始URL
                self.logger.info(f'失败的原始URL: {response.meta.get("original_url")}')
                self.logger.error(f"解析导航树HTML数据失败: {str(e)}")
