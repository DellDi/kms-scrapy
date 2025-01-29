from typing import Dict, Any
from scrapy.http import Request, FormRequest
import base64
from .config import config

class AuthManager:
    """认证管理器，处理所有与认证相关的逻辑"""

    @staticmethod
    def get_auth_headers() -> Dict[str, str]:
        """获取包含Basic认证的请求头"""
        auth_str = f'Basic {base64.b64encode(f"{config.auth.basic_auth_user}:{config.auth.basic_auth_pass}".encode()).decode()}'
        return {
            'Authorization': auth_str,
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6',
            'Connection': 'keep-alive',
            'Upgrade-Insecure-Requests': '1',
            'User-Agent': config.spider.default_headers['User-Agent']
        }

    @staticmethod
    def create_login_request(response, callback, meta: Dict[str, Any]) -> FormRequest:
        """创建登录请求"""
        target_url = meta.get('original_url', config.spider.start_urls[0])
        formdata = {
            'os_username': config.auth.username,
            'os_password': config.auth.password,
            'os_cookie': 'true',
            'os_destination': target_url,
            'login': '登录'
        }

        return FormRequest.from_response(
            response,
            formdata=formdata,
            formid='loginform',
            clickdata={'name': 'login'},
            headers=AuthManager.get_auth_headers(),
            callback=callback,
            dont_filter=True,
            meta={
                'dont_merge_cookies': True,
                'handle_httpstatus_list': [302],
                'original_url': formdata['os_destination']
            }
        )

    @staticmethod
    def create_authenticated_request(url: str, callback, meta: Dict[str, Any], cookies: Dict[str, str] = None) -> Request:
        """创建带认证信息的请求"""
        headers = AuthManager.get_auth_headers()
        if cookies:
            headers['Cookie'] = '; '.join(f'{k}={v}' for k, v in cookies.items())

        return Request(
            url,
            callback=callback,
            headers=headers,
            dont_filter=True,
            meta=meta
        )