from typing import Dict, Optional
import requests
from urllib.parse import urljoin

from .config import config

class AuthError(Exception):
    """认证相关异常"""
    pass

class AuthManager:
    """认证管理类"""

    def __init__(self):
        """初始化认证管理器"""
        self._cookies: Dict[str, str] = config.spider.default_cookies.copy()
        self._headers: Dict[str, str] = config.spider.default_headers.copy()
        # 添加Basic认证头
        self._headers["Authorization"] = f"Basic {config.auth.basic_auth}"

    @property
    def cookies(self) -> Dict[str, str]:
        """获取当前Cookie"""
        return self._cookies.copy()

    @property
    def headers(self) -> Dict[str, str]:
        """获取当前请求头"""
        headers = self._headers.copy()
        if self._cookies:
            cookie_str = "; ".join(f"{k}={v}" for k, v in self._cookies.items())
            headers["Cookie"] = cookie_str
        return headers

    def update_cookies(self, new_cookies: Dict[str, str]):
        """
        更新Cookie

        Args:
            new_cookies: 新的Cookie字典
        """
        self._cookies.update(new_cookies)

    def parse_set_cookie(self, response: requests.Response) -> Dict[str, str]:
        """
        从响应中解析Set-Cookie头

        Args:
            response: 响应对象

        Returns:
            Dict[str, str]: 解析出的Cookie字典
        """
        cookies = {}
        for cookie in response.headers.getlist("Set-Cookie"):
            cookie_str = cookie.decode() if isinstance(cookie, bytes) else cookie
            if "=" in cookie_str:
                name, value = cookie_str.split("=", 1)
                value = value.split(";")[0]
                cookies[name.strip()] = value.strip()
        return cookies

    def create_authenticated_request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Dict] = None,
        **kwargs
    ) -> requests.Request:
        """
        创建带认证信息的请求

        Args:
            url: 请求URL
            method: 请求方法
            data: 请求数据
            **kwargs: 其他请求参数

        Returns:
            requests.Request: 请求对象
        """
        # 确保URL是完整的
        if not url.startswith(("http://", "https://")):
            url = urljoin(config.spider.base_url, url)

        # 创建请求
        headers = self.headers
        if kwargs.get("headers"):
            headers.update(kwargs.pop("headers"))

        return requests.Request(
            method=method,
            url=url,
            headers=headers,
            data=data,
            **kwargs
        )

    def check_authentication(self) -> bool:
        """
        检查认证状态

        Returns:
            bool: 认证是否有效
        """
        try:
            # 尝试访问一个需要认证的API
            session = requests.Session()
            request = self.create_authenticated_request(
                "/rest/api/2/myself",  # Jira提供的当前用户信息API
                method="GET"
            )
            prepped = request.prepare()
            response = session.send(prepped)

            # 检查响应状态
            return response.status_code == 200

        except Exception as e:
            raise AuthError(f"认证检查失败: {str(e)}")

    def refresh_authentication(self) -> bool:
        """
        刷新认证信息

        Returns:
            bool: 是否刷新成功
        """
        try:
            # 登录获取新的认证信息
            session = requests.Session()
            login_data = {
                "os_username": config.auth.username,
                "os_password": config.auth.password,
                "os_cookie": "true"
            }

            request = self.create_authenticated_request(
                "/login.jsp",
                method="POST",
                data=login_data
            )

            prepped = request.prepare()
            response = session.send(prepped, allow_redirects=False)

            # 如果是重定向响应，认为登录成功
            if response.status_code in (302, 303):
                # 解析并更新Cookie
                new_cookies = self.parse_set_cookie(response)
                if new_cookies:
                    self.update_cookies(new_cookies)
                    return True

            return False

        except Exception as e:
            raise AuthError(f"认证刷新失败: {str(e)}")