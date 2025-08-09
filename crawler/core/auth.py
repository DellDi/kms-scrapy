from typing import Dict, Any
from scrapy.http import Request, FormRequest
import base64
from crawler.core.config import config


class AuthManager:
    """认证管理器，处理所有与认证相关的逻辑 (简化版，利用 Scrapy 自动 cookie 管理)"""

    """首先调用create_login_request 方法创建登录请求，然后调用handle_login_response 方法处理登录响应，最后调用get_auth_headers 方法获取包含Basic认证的请求头。"""

    def __init__(self, meta):
        import logging
        self.logger = logging.getLogger(__name__)
        self.meta = meta
        # 调用实例方法版本的create_login_request
        self.login_request = self.create_login_request(meta)

    @staticmethod
    def get_auth_headers() -> Dict[str, str]:
        """获取包含Basic认证的请求头 (简化版，不再手动处理 Cookie)"""
        auth_str = f'Basic {base64.b64encode(f"{config.auth.basic_auth_user}:{config.auth.basic_auth_pass}".encode()).decode()}'
        headers = {
            "Authorization": auth_str,
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Connection": "keep-alive",
            "Upgrade-Insecure-Requests": "1",
            "User-Agent": config.spider.default_headers["User-Agent"],
        }
        return headers

    def create_login_request(self, meta, original_callback=None) -> FormRequest:
        """创建登录请求 (简化版，依赖 Scrapy 自动处理 Cookie)
        Args:
            meta: 请求元数据
            original_callback: 登录成功后要调用的回调函数
        """
        target_url = meta.get("original_url", config.spider.start_urls[0])
        formdata = {
            "os_username": config.auth.username,
            "os_password": config.auth.password,
            "os_cookie": "true",
            "os_destination": target_url,
            "login": "登录",
        }
        
        login_url = target_url + "/dologin.action"
        self.logger.info(f"Creating login request to: {login_url}")
        
        # 直接构造登录请求，不再显式传递 cookies，Scrapy 会自动处理
        return FormRequest(
            url=login_url,
            method="POST",
            formdata=formdata,
            headers={
                **self.get_auth_headers(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": target_url,
            },
            callback=self.handle_login_response,
            dont_filter=True,
            meta={
                "handle_httpstatus_list": [302],
                "original_url": formdata["os_destination"],
                "original_callback": original_callback,  # 保存原始callback
            },
        )

    def handle_login_response(self, response):
        """处理登录响应，成功后继续抓取原始目标页面"""
        self.logger.info(f"处理登录响应: status={response.status}")
        
        # 检查响应状态，confluence可能返回200或302
        if response.status in [200, 302]:
            self.logger.info("登录成功")
            self.logger.info(f"Response headers: {response.headers}")
            
            # 获取原始目标URL和回调函数
            original_url = response.meta.get('original_url', config.spider.start_urls[0])
            callback = response.request.meta.get('original_callback')
            
            self.logger.info(f"继续抓取原始目标页面: {original_url}")
            
            # 创建认证请求访问目标页面
            return self.create_authenticated_request(
                url=original_url,
                callback=callback,  # 使用保存的原始回调
                meta={
                    "handle_httpstatus_list": [200, 302],
                    "dont_merge_cookies": False  # 允许合并cookies
                }
            )
        else:
            self.logger.error(f"登录失败: status={response.status}, url={response.url}")
            self.logger.error(f"Response body: {response.text[:500]}...")  # 记录响应内容前500个字符
            return None

    @staticmethod
    def create_authenticated_request(url: str, callback=None, meta: Dict[str, Any] = None, **kwargs) -> Request:
        """创建带认证信息的请求 (简化版，依赖 Scrapy 自动处理 Cookie)
        
        Args:
            url: 请求URL
            callback: 回调函数，如果为None则直接返回response
            meta: 元数据，如果为None则使用默认值
            **kwargs: 其他参数
        """
        meta = meta or {}
        headers = AuthManager.get_auth_headers()
        
        # 为文件下载请求添加特殊处理
        if any(ext in url.lower() for ext in ['.pdf', '.doc', '.docx', '.xls', '.xlsx', '.png', '.jpg', '.jpeg']):
            meta.update({
                'handle_httpstatus_list': [200],
                'dont_merge_cookies': False,  # 确保合并cookies
                'download_file': True  # 标记这是一个文件下载请求
            })
            headers.update({
                'Accept': '*/*',
                'Accept-Encoding': 'gzip, deflate'
            })

        return Request(
            url,
            callback=callback,
            headers=headers,
            dont_filter=True,
            meta=meta,
            **kwargs,
        )
