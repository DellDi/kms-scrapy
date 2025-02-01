import scrapy
from scrapy.http import Request, FormRequest
from bs4 import BeautifulSoup
from datetime import datetime
import requests
import base64
from .auth import AuthManager
from .content import ContentParser, KMSItem
from .config import config

class ConfluenceSpider(scrapy.Spider):
    name = 'confluence'
    custom_settings = {
        'DOWNLOAD_DELAY': config.spider.download_delay,
        'COOKIES_ENABLED': True,
        'CONCURRENT_REQUESTS': config.spider.concurrent_requests,
        'RETRY_TIMES': config.spider.retry_times,
        'RETRY_HTTP_CODES': config.spider.retry_http_codes,
        'DEFAULT_REQUEST_HEADERS': config.spider.default_headers,
        'Cookie': ''
    }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.start_urls = [kwargs.get('start_url', 'http://kms.new-see.com:8090')]
        self.auth_manager = AuthManager()
        self.content_parser = ContentParser()
        self.basic_auth = (config.auth.basic_auth_user, config.auth.basic_auth_pass)
        self.auth = {
            'os_username': config.auth.username,
            'os_password': config.auth.password
        }
        self.default_cookies = config.spider.default_cookies
        self.baichuan_config = {
            'api_key': config.baichuan.api_key,
            'api_url': config.baichuan.api_url
        }

    def _get_common_headers(self, cookies=None):
        """获取通用的请求头"""
        headers = config.spider.default_headers.copy()
        headers.update({
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'Authorization': 'Basic bmV3c2VlOm5ld3NlZQ==',
            'Cookie':'confluence.list.pages.cookie=list-content-tree; seraph.confluence=149782566%3Adcc80dc3aa14b0a5f57223027a87f61e56afa47d; JSESSIONID=6FB059AC7D7B504817E9B894051AF62B'
        })
        if cookies:
            headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in cookies.items())
        return headers

    def start_requests(self):
        for url in self.start_urls:
            yield Request(
                url,
                callback=self.parse,
                headers=self._get_common_headers(),
                dont_filter=True,
                meta={
                    'dont_merge_cookies': True,
                    'handle_httpstatus_list': [302]
                }
            )

    def _handle_redirect(self, response, callback=None, meta=None):
        """处理重定向和登录页面的通用方法"""
        # 如果是302重定向，获取重定向URL
        if response.status == 302:
            redirect_url = response.urljoin(response.headers.get('Location', b'').decode())
        else:
            redirect_url = response.url

        # 处理登录页面
        if '/login.action' in redirect_url:
            # 获取原始URL，如果meta中没有，则使用当前URL
            original_url = response.meta.get('original_url', response.url)
            meta = meta or {}
            meta.update({
                'dont_merge_cookies': True,
                'handle_httpstatus_list': [302],
                'original_url': original_url
            })
            headers = self._get_common_headers()
            return Request(
                redirect_url,
                callback=self.login,
                headers=headers,
                dont_filter=True,
                meta=meta
            )
        else:
            meta = meta or {}
            meta.update({
                'dont_merge_cookies': True,
                'handle_httpstatus_list': [302]
            })
            return Request(
                redirect_url,
                callback=callback or self.parse,
                dont_filter=True,
                meta=meta
            )

    def parse(self, response):
        # 如果是重定向到登录页面
        if response.status == 302 or '/login.action' in response.url:
            yield self._handle_redirect(response)
        # 处理内容页面
        else:
            self.logger.info(f'开始处理页面: {response}')
            # 检查页面是否已完全加载
            soup = BeautifulSoup(response.text, 'html.parser')
            title_element = soup.select_one('#title-text')
            main_content = soup.select_one('#main-content')
            retry_count = response.meta.get('retry_count', 0)
            max_retries = 3  # 最大重试次数

            # 检查页面关键元素是否加载
            if not title_element or not main_content:
                if retry_count < max_retries:
                    self.logger.info(f'页面未完全加载，第{retry_count + 1}次重试')
                    meta = response.meta.copy()
                    meta['retry_count'] = retry_count + 1
                    # 增加延迟，避免过于频繁的请求
                    meta['download_delay'] = (retry_count + 1) * 2
                    yield self.auth_manager.create_authenticated_request(
                        response.url,
                        callback=self.parse,
                        meta=meta
                    )
                else:
                    self.logger.warning(f'页面 {response.url} 在{max_retries}次重试后仍未完全加载，跳过处理')
                return
            # 检查页面是否已完全加载
            soup = BeautifulSoup(response.text, 'html.parser')
            title_element = soup.select_one('#title-text')
            main_content = soup.select_one('#main-content')
            retry_count = response.meta.get('retry_count', 0)
            max_retries = 3  # 最大重试次数

            # 检查页面关键元素是否加载
            if not title_element or not main_content:
                if retry_count < max_retries:
                    self.logger.info(f'页面未完全加载，第{retry_count + 1}次重试')
                    meta = response.meta.copy()
                    meta['retry_count'] = retry_count + 1
                    # 增加延迟，避免过于频繁的请求
                    meta['download_delay'] = (retry_count + 1) * 2
                    yield self.auth_manager.create_authenticated_request(
                        response.url,
                        callback=self.parse,
                        meta=meta
                    )
                else:
                    self.logger.warning(f'页面 {response.url} 在{max_retries}次重试后仍未完全加载，跳过处理')
                return

            # 解析导航树（作为可选项）
            tree_container = soup.select_one('span.plugin_pagetree_children_span')
            retry_count = response.meta.get('tree_retry_count', 0)
            max_tree_retries = 3  # 导航树最大重试次数

            # 检查导航树是否完全加载
            if tree_container and not tree_container.find_all('a'):
                if retry_count < max_tree_retries:
                    self.logger.info(f'导航树未完全加载，第{retry_count + 1}次重试')
                    meta = response.meta.copy()
                    meta['tree_retry_count'] = retry_count + 1
                    # 使用递增的延迟时间
                    delay = (retry_count + 1) * 3  # 每次重试增加3秒延迟
                    meta['download_delay'] = delay
                    yield self.auth_manager.create_authenticated_request(
                        response.url,
                        callback=self.parse,
                        meta=meta
                    )
                    return
                else:
                    self.logger.warning(f'导航树在{max_tree_retries}次重试后仍未完全加载')

            if tree_container:
                # 解析导航树
                tree_links = tree_container.find_all('a')
                self.logger.info(f'找到{len(tree_links)}个导航树链接')
                # 遍历导航树链接
                for link in tree_links:
                    href = link.get('href')
                    text = link.get_text(strip=True)
                    if href:
                        full_url = response.urljoin(href)
                        self.logger.info(f'处理导航树链接: {text} -> {full_url}')
                        headers = self._get_common_headers()
                        yield response.follow(
                            url=full_url,
                            callback=self.parse_content,
                            headers=headers,
                            dont_filter=True,
                            meta={
                                'dont_merge_cookies': True,
                                'handle_httpstatus_list': [302,200],
                            }
                        )
            else:
                self.logger.info('当前页面没有导航树，继续处理页面内容')
                # 没有导航树时，直接处理当前页面内容
                yield response.follow(
                    url=response.url,
                    callback=self.parse_content,
                    headers=self._get_common_headers(),
                    dont_filter=True,
                    meta={
                        'dont_merge_cookies': True,
                        'handle_httpstatus_list': [302,200],
                    }
                )

    def login(self, response):
        # 检查是否是登录页面
        if '/login.action' in response.url:
            # 构建登录表单数据
            # 获取原始目标URL，如果没有则使用起始URL
            target_url = response.meta.get('original_url', self.start_urls[0])
            formdata = {
                'os_username': self.auth['os_username'],
                'os_password': self.auth['os_password'],
                'os_cookie': 'true',
                'os_destination': target_url,  # 使用实际的目标URL
                'login': '登录'
            }

            # 使用正确的选择器和登录按钮
            headers = self._get_common_headers()
            headers['Cache-Control'] = 'max-age=0'
            headers['Proxy-Connection'] = 'keep-alive'
            yield FormRequest.from_response(
                response,
                formdata=formdata,
                formid='loginform',  # 指定登录表单的ID
                clickdata={'name': 'login'},  # 指定登录按钮
                headers=headers,
                callback=self.after_login,
                dont_filter=True,
                meta={
                    'dont_merge_cookies': True,  # 使用新的cookie
                    'handle_httpstatus_list': [302],  # 处理302重定向
                    'original_url': formdata['os_destination']  # 保存原始目标URL
                }
            )

    def after_login(self, response):
        # 记录响应状态码和响应头信息
        self.logger.info(f'登录响应状态码: {response.status}')
        self.logger.info(f'响应头信息: {dict(response.headers)}')

        # 检查登录是否成功 - 需要同时满足以下条件：
        # 1. 302状态码
        # 2. 存在JSESSIONID和seraph.confluence两个cookie
        if response.status == 302:
            cookies = self.default_cookies.copy()  # 使用默认cookie作为基础
            jsessionid_found = False
            seraph_found = False

            # 记录Set-Cookie头信息并解析
            self.logger.info('开始处理cookie信息')
            for cookie in response.headers.getlist('Set-Cookie'):
                cookie_str = cookie.decode()
                self.logger.info(f'处理cookie: {cookie_str}')

                if '=' in cookie_str:
                    name, value = cookie_str.split('=', 1)
                    value = value.split(';')[0]
                    name = name.strip()
                    value = value.strip()
                    cookies[name] = value

                    if name == 'JSESSIONID':
                        jsessionid_found = True
                    elif name == 'seraph.confluence':
                        seraph_found = True

            # 检查是否获取到所需的cookie
            if jsessionid_found and seraph_found:
                self.logger.info('成功获取所需的cookie')
                # 直接使用保存的原始目标URL
                target_url = response.meta.get('original_url', self.start_urls[0])
                self.logger.info(f'使用原始目标URL: {target_url}')

                # 更新默认cookie
                self.default_cookies.update(cookies)
                self.logger.info(f'更新默认cookie: {self.default_cookies}')

                # 构建认证头
                headers = self._get_common_headers(cookies)

                self.logger.info(f'构建的请求头: {headers}')
                self.logger.info(f'构建的请求目标地址: {target_url}')
                # 登录成功后直接访问目标URL
                return Request(
                    url=target_url,
                    callback=self.parse_content,  # 直接使用parse_content方法处理页面内容
                    headers=headers,
                    dont_filter=True,
                    meta={
                        'dont_merge_cookies': False,  # 登录成功后允许合并cookie
                        'handle_httpstatus_list': [302],  # 继续处理可能的重定向
                        # 'cookies': cookies  # 保存cookie信息供后续使用
                    }
                )
            else:
                missing_cookies = []
                if not jsessionid_found:
                    missing_cookies.append('JSESSIONID')
                if not seraph_found:
                    missing_cookies.append('seraph.confluence')
                self.logger.error(f'登录失败：缺少必要的cookie: {", ".join(missing_cookies)}')
                return None
        else:
            self.logger.error(f'登录失败：响应状态码不正确 {response.status}')
            return None

    def optimize_content(self, content: str) -> str:
        if not self.baichuan_config.get('api_key'):
            self.logger.warning('未配置百川API密钥，跳过内容优化')
            return content
        self.logger.info(f'百川API密钥: {self.baichuan_config["api_key"]}')
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.baichuan_config["api_key"]}'
        }
        data = {
            'model':'Baichuan4-Air',
            'messages': [
                {
                    'role': 'system',
                    'content': '你是一个专业的文档优化助手，需要对输入的文档内容进行结构化和优化处理，使其更加清晰易读，同时保持原有的核心信息和专业性。'
                },
                {
                    'role': 'user',
                    'content': content
                }
            ],
            'temperature': 0.2,
            'stream': False
        }

        try:
            response = requests.post(self.baichuan_config['api_url'], headers=headers, json=data)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except Exception as e:
            self.logger.error(f'百川API调用失败: {str(e)}')
            return content

    def parse_content(self, response):
        # 检查是否是重定向
        if response.status == 302:
            redirect_url = response.headers.get(b'Location', b'').decode()
            if redirect_url:
                redirect_url = response.urljoin(redirect_url)
                cookies = config.spider.default_cookies.copy()
                if 'cookies' in response.meta:
                    cookies.update(response.meta['cookies'])
                meta = {
                    'dont_merge_cookies': False,
                    'handle_httpstatus_list': [302],
                    'cookies': cookies,
                    'original_url': response.meta.get('original_url', response.url)
                }
                # 如果是权限验证失败或需要重新登录
                if 'permissionViolation=true' in redirect_url or '/login.action' in redirect_url:
                    yield self._handle_redirect(response, self.login, meta)
                    return
                else:
                    yield self._handle_redirect(response, self.parse_content, meta)
                    return

        # 检查是否是登录页面
        if '/login.action' in response.url:
            yield self.auth_manager.create_authenticated_request(
                response.url,
                callback=self.login,
                meta={
                    'dont_merge_cookies': True,
                    'handle_httpstatus_list': [302],
                    'original_url': response.meta.get('original_url')
                }
            )
            return

        # 获取当前的cookie
        cookies = config.spider.default_cookies.copy()
        if 'cookies' in response.meta:
            cookies.update(response.meta['cookies'])

        # 解析页面内容
        soup = BeautifulSoup(response.text, 'html.parser')
        title_element = soup.select_one('#title-text')
        main_content = soup.select_one('#main-content')

        # 检查页面是否已完全加载
        retry_count = response.meta.get('retry_count', 0)
        max_retries = 3  # 最大重试次数

        if not title_element or not main_content or not main_content.find_all():
            if retry_count < max_retries:
                self.logger.info(f'页面内容未完全加载，第{retry_count + 1}次重试')
                meta = response.meta.copy()
                meta['retry_count'] = retry_count + 1
                delay = (retry_count + 1) * 3  # 每次重试增加3秒延迟
                meta['download_delay'] = delay
                yield self.auth_manager.create_authenticated_request(
                    response.url,
                    callback=self.parse_content,
                    meta=meta,
                    cookies=cookies
                )
            else:
                self.logger.warning(f'页面 {response.url} 在{max_retries}次重试后仍未完全加载，跳过处理')
            return

        # 处理页面内容
        title = title_element.get_text(strip=True)
        content = soup.select_one('#main-content')

        # 处理附件
        attachments = []
        # 选择具有data-linked-resource-type='attachment'属性的元素
        for attachment in soup.select('#main-content [data-linked-resource-type="attachment"]'):
            # 根据元素类型获取附件链接
            if attachment.name == 'img':
                file_url = response.urljoin(attachment.get('src', ''))
            else:  # a标签
                file_url = response.urljoin(attachment.get('href', ''))

            if file_url:  # 只处理有效的URL
                attachment_info = self.content_parser.process_attachment(
                    file_url,
                    self._get_common_headers()
                )
                if attachment_info:
                    attachments.append(attachment_info)

        # 使用百川API优化内容
        optimized_content = self.optimize_content(content.get_text())

        # 创建KMSItem对象
        from .exporter import DocumentExporter
        kms_item = KMSItem(
            title=title,
            content=optimized_content,
            attachments=attachments
        )

        # 使用DocumentExporter导出文档
        exporter = DocumentExporter()
        markdown_path, attachments_dir = exporter.export(kms_item)

        self.logger.info(f'已保存文档：{markdown_path}')
        self.logger.info(f'附件保存在：{attachments_dir}' if attachments else '无附件')

        # 将关键信息yield给Scrapy数据管道
        yield {
            'title': title,
            'url': response.url,
            'markdown_path': markdown_path,
            'attachments_dir': attachments_dir if attachments else None,
            'attachments_count': len(attachments),
            'timestamp': datetime.now().isoformat(),
            'status': 'success'
        }