from bs4 import BeautifulSoup
from scrapy.http import Request
from urllib.parse import urlencode
import logging

class TreeExtractor:
    """处理 Confluence 页面导航树提取的专用类"""
    
    def __init__(self, common_headers_callback):
        self.logger = logging.getLogger(__name__)
        self._get_common_headers = common_headers_callback

    def process_tree_container(self, response, soup):
        """处理页面中的导航树容器"""
        tree_container = soup.select_one('.plugin_pagetree')
        
        if not tree_container:
            self.logger.info('当前页面没有导航树')
            return None
            
        # 获取隐藏字段中的参数
        fieldset = tree_container.select_one('fieldset.hidden')
        if not fieldset:
            self.logger.info('无法获取导航树参数')
            return None
            
        try:
            # 获取基本参数
            params = {
                'decorator': 'none',
                'excerpt': 'false',
                'sort': 'position',
                'reverse': 'false',
                'disableLinks': 'false',
                'expandCurrent': 'true',
                'hasRoot': 'true',
                'pageId': fieldset.select_one('input[name="rootPageId"]')['value'],
                'treeId': '0',
                'startDepth': fieldset.select_one('input[name="startDepth"]')['value'],
                'mobile': fieldset.select_one('input[name="mobile"]')['value'],
                'treePageId': fieldset.select_one('input[name="treePageId"]')['value']
            }
            
            # 获取祖先ID列表
            ancestor_ids = [input_['value'] for input_ in fieldset.select('fieldset.hidden input[name="ancestorId"]')]
            params['ancestors'] = ancestor_ids
            
            # 构建完整的请求URL
            tree_url = response.urljoin('/plugins/pagetree/naturalchildren.action')
            tree_url = f"{tree_url}?{urlencode(params, doseq=True)}"
            
            self.logger.info(f'获取到的导航树参数: {params}')
            
            # 构建并返回请求
            headers = self._get_common_headers()
            headers.update({
                'x-requested-with': 'XMLHttpRequest'
            })
            
            return Request(
                url=tree_url,
                callback=self.parse_tree_ajax,
                headers=headers,
                meta={
                    'original_url': response.url,
                    'dont_merge_cookies': True,
                    'handle_httpstatus_list': [302,200]
                },
                dont_filter=True
            )
            
        except Exception as e:
            self.logger.error(f'处理导航树参数时出错: {str(e)}')
            return None

    def parse_tree_ajax(self, response):
        """处理导航树Ajax响应"""
        try:
            # 使用BeautifulSoup解析HTML响应
            soup = BeautifulSoup(response.text, 'html.parser')
            # 查找所有页面链接
            page_links = soup.select('a[href*="viewpage.action"]')
            self.logger.info(f'成功获取导航树数据: {len(page_links)}个子页面')

            # 处理每个子页面
            for link in page_links:
                page_url = response.urljoin(link['href'])
                title = link.get_text(strip=True)
                self.logger.info(f'处理子页面: {title} -> {page_url}')
                headers = self._get_common_headers()
                yield Request(
                    url=page_url,
                    callback=self.parse_content_callback,
                    headers=headers,
                    dont_filter=True,
                    meta={
                        'dont_merge_cookies': True,
                        'handle_httpstatus_list': [302,200]
                    }
                )

        except Exception as e:
            self.logger.error(f'解析导航树HTML数据失败: {str(e)}')