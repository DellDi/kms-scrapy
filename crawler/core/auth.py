from typing import Dict, Any
from scrapy.http import Request, FormRequest
import base64
from .config import config


class AuthManager:
    """认证管理器，处理所有与认证相关的逻辑 (简化版，利用 Scrapy 自动 cookie 管理)"""

    """首先调用create_login_request 方法创建登录请求，然后调用handle_login_response 方法处理登录响应，最后调用get_auth_headers 方法获取包含Basic认证的请求头。"""

    def __init__(self, meta):
        self.create_login_request(meta)

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

    @staticmethod
    def create_login_request(meta) -> FormRequest:
        """创建登录请求 (简化版，依赖 Scrapy 自动处理 Cookie)"""
        target_url = meta.get("original_url", config.spider.start_urls[0])
        formdata = {
            "os_username": config.auth.username,
            "os_password": config.auth.password,
            "os_cookie": "true",
            "os_destination": target_url,
            "login": "登录",
        }
        # 直接构造登录请求，不再显式传递 cookies，Scrapy 会自动处理
        return FormRequest(
            # url=target_url.urljoin("/dologin.action"),
            url=target_url.join("/dologin.action"),
            method="POST",
            formdata=formdata,
            headers={
                **AuthManager.get_auth_headers(),
                "Content-Type": "application/x-www-form-urlencoded",
                "Referer": target_url,
            },
            dont_filter=True,
            meta={
                "handle_httpstatus_list": [302],
                "original_url": formdata["os_destination"],
            },
        )

    @staticmethod
    def create_authenticated_request(url: str, callback, meta: Dict[str, Any],**kwargs) -> Request:
        """创建带认证信息的请求 (简化版，依赖 Scrapy 自动处理 Cookie)"""
        return Request(
            url,
            callback=callback,
            headers=AuthManager.get_auth_headers(),  # 请求头中不再需要手动添加 Cookie，Scrapy 自动处理
            dont_filter=True,
            meta=meta,
            **kwargs,
        )
