import scrapy
from scrapy.http import Request, FormRequest
from bs4 import BeautifulSoup
import requests
import base64
from .auth import AuthManager
from .content import ContentParser, KMSItem
from .config import config

class ConfluenceSpider(scrapy.Spider):
    name = 'confluence'
    custom_settings = {
        'DOWNLOAD_DELAY': 2,
        'COOKIES_ENABLED': True,
        'CONCURRENT_REQUESTS': 1,
        'RETRY_TIMES': 5,
        'RETRY_HTTP_CODES': [500, 502, 503, 504, 408, 429],
        'DEFAULT_REQUEST_HEADERS': {
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8',
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.114 Safari/537.36'
        },
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

    def start_requests(self):
        for url in self.start_urls:
            yield self.auth_manager.create_authenticated_request(
                url,
                callback=self.parse,
                meta={
                    'dont_merge_cookies': True,
                    'handle_httpstatus_list': [302]
                }
            )

    def parse(self, response):
        # 如果是重定向到登录页面
        if response.status == 302 or '/login.action' in response.url:
            # 如果是302重定向，获取重定向URL
            if response.status == 302:
                login_url = response.urljoin(response.headers.get('Location', b'').decode())
            else:
                login_url = response.url

            # 处理登录页面
            if '/login.action' in login_url:
                # 获取原始URL，如果meta中没有，则使用当前URL
                original_url = response.meta.get('original_url', response.url)
                # 获取登录页面内容
                # auth_str = f'Basic {base64.b64encode(f"{self.basic_auth[0]}:{self.basic_auth[1]}".encode()).decode()}'
                auth_str = 'Basic bmV3c2VlOm5ld3NlZQ=='
                headers = {
                    'Authorization': auth_str,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
                }
                yield Request(
                    login_url,
                    callback=self.login,
                    headers=headers,
                    dont_filter=True,
                    meta={
                        'dont_merge_cookies': True,
                        'handle_httpstatus_list': [302],
                        'original_url': original_url  # 保存原始URL
                    }
                )
            else:
                yield Request(
                    login_url,
                    callback=self.parse,
                    dont_filter=True,
                    meta={
                        'dont_merge_cookies': True,
                        'handle_httpstatus_list': [302]
                    }
                )
        # 处理内容页面
        else:
            # 解析导航树
            tree_links = response.css('.plugin-tabmeta-details a::attr(href)').getall()
            for link in tree_links:
                if 'pageId' in link:
                    # 添加认证和cookie信息
                    auth_str ='Basic bmV3c2VlOm5ld3NlZQ=='
                    headers = {
                        'Authorization': auth_str,
                        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                        'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                        'Connection': 'keep-alive',
                        'Upgrade-Insecure-Requests': '1',
                        'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
                    }
                    # 获取当前的cookie
                    cookies = self.default_cookies.copy()
                    if 'cookies' in response.meta:
                        cookies.update(response.meta['cookies'])
                    headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in cookies.items())

                    yield response.follow(
                        link,
                        callback=self.parse_content,
                        headers=headers,
                        meta={
                            'dont_merge_cookies': False,
                            'handle_httpstatus_list': [302],
                            'cookies': cookies
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
            auth_str ='Basic bmV3c2VlOm5ld3NlZQ=='
            headers = {
                'Authorization': auth_str,
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                'Cache-Control': 'max-age=0',
                'Proxy-Connection': 'keep-alive',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0'
            }
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
                auth_str = 'Basic bmV3c2VlOm5ld3NlZQ=='
                headers = {
                    'Authorization': auth_str,
                    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7',
                    'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
                    'Cache-Control': 'max-age=0',
                    'Proxy-Connection': 'keep-alive',
                    'Connection': 'keep-alive',
                    'Upgrade-Insecure-Requests': '1',
                    'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/132.0.0.0 Safari/537.36 Edg/132.0.0.0',
                    'Host': 'kms.new-see.com:8090',
                    'Cookie': '; '.join(f'{k}={v}' for k, v in cookies.items())
                }

                self.logger.info(f'构建的请求头: {headers}')

                # 登录成功后直接访问目标URL
                return Request(
                    target_url,
                    callback=self.parse_content,  # 直接使用parse_content方法处理页面内容
                    headers=headers,
                    dont_filter=True,
                    meta={
                        'dont_merge_cookies': False,  # 登录成功后允许合并cookie
                        'handle_httpstatus_list': [302],  # 继续处理可能的重定向
                        'cookies': cookies  # 保存cookie信息供后续使用
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
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {self.baichuan_config["api_key"]}'
        }

        data = {
            'model': 'Baichuan4',
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
            'temperature': 0.3,
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
                # 如果是权限验证失败或需要重新登录
                if 'permissionViolation=true' in redirect_url or '/login.action' in redirect_url:
                    original_url = response.meta.get('original_url', response.url)
                    yield self.auth_manager.create_authenticated_request(
                        redirect_url,
                        callback=self.login,
                        meta={
                            'dont_merge_cookies': True,
                            'handle_httpstatus_list': [302],
                            'original_url': original_url
                        }
                    )
                    return
                else:
                    cookies = config.spider.default_cookies.copy()
                    if 'cookies' in response.meta:
                        cookies.update(response.meta['cookies'])
                    target_url = response.meta.get('original_url', response.url)
                    yield self.auth_manager.create_authenticated_request(
                        target_url,
                        callback=self.parse_content,
                        meta={
                            'dont_merge_cookies': False,
                            'handle_httpstatus_list': [302],
                            'cookies': cookies,
                            'original_url': target_url
                        },
                        cookies=cookies
                    )
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

        # 检查页面是否已完全加载
        if not title_element:
            self.logger.info('页面未完全加载，重新请求')
            yield self.auth_manager.create_authenticated_request(
                response.url,
                callback=self.parse_content,
                meta=response.meta,
                cookies=cookies
            )
            return

        # 处理页面内容
        title = title_element.get_text(strip=True)
        content = soup.select_one('#main-content')

        # 处理附件
        attachments = []
        for attachment in soup.select('.attachment-content'):
            file_url = response.urljoin(attachment.select_one('a')['href'])
            attachment_info = self.content_parser.process_attachment(
                file_url,
                self.auth_manager.get_auth_headers()
            )
            if attachment_info:
                attachments.append(attachment_info)

        # 使用百川API优化内容
        optimized_content = self.optimize_content(content.get_text())

        yield KMSItem(
            title=title,
            content=optimized_content,
            attachments=attachments
        )