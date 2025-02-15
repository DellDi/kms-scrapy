from typing import Dict, Optional, Union
import logging
import requests
from urllib.parse import urljoin, quote

from .config import config

# 配置日志
logger = logging.getLogger(__name__)

class AuthError(Exception):
    """认证相关异常"""
    pass

class AuthManager:
    """认证管理类"""

    def __init__(self):
        """初始化认证管理器"""
        # 初始化headers和cookies
        self._headers: Dict[str, str] = config.spider.default_headers.copy()
        self._cookies: Dict[str, str] = {}  # 初始化为空，等待登录后更新

        # 设置Basic认证
        self._headers["Authorization"] = f"Basic {config.auth.basic_auth}"
        logger.debug("AuthManager initialized with default headers")

    @property
    def cookies(self) -> Dict[str, str]:
        """
        获取当前Cookie

        Returns:
            Dict[str, str]: 当前的Cookie字典
        """
        # 如果没有cookies，使用默认cookies
        if not self._cookies:
            logger.debug("Using default cookies")
            return config.spider.default_cookies.copy()
        return self._cookies.copy()

    @property
    def headers(self) -> Dict[str, str]:
        """
        获取当前请求头

        Returns:
            Dict[str, str]: 当前的请求头字典
        """
        headers = self._headers.copy()

        # 获取当前cookies
        cookies = self.cookies
        if cookies:
            # 使用quote对cookie值进行编码，处理特殊字符
            cookie_str = "; ".join(
                f"{k}={quote(v)}" for k, v in cookies.items()
                if v is not None and v != ""
            )
            if cookie_str:
                headers["Cookie"] = cookie_str
                logger.debug(f"Cookie header set: {cookie_str}")

        return headers

    def update_cookies(self, new_cookies: Dict[str, str]):
        """
        更新Cookie

        Args:
            new_cookies: 新的Cookie字典
        """
        old_cookies = self._cookies.copy()
        self._cookies.update(
            {k: v for k, v in new_cookies.items() if v is not None and v != ""}
        )
        logger.debug(f"Updated cookies: {set(self._cookies) - set(old_cookies)}")

    def parse_set_cookie(self, response: requests.Response) -> Dict[str, str]:
        """
        从响应中解析Set-Cookie头

        Args:
            response: 响应对象

        Returns:
            Dict[str, str]: 解析出的Cookie字典
        """
        cookies = {}
        all_cookies = []

        # 获取所有Set-Cookie头
        if "Set-Cookie" in response.headers:
            if isinstance(response.headers["Set-Cookie"], (list, tuple)):
                all_cookies = response.headers.getlist("Set-Cookie")
            else:
                all_cookies = [response.headers["Set-Cookie"]]
            logger.debug(f"Found {len(all_cookies)} Set-Cookie headers")

        # 解析每个Cookie
        for cookie in all_cookies:
            cookie_str = cookie.decode() if isinstance(cookie, bytes) else cookie
            if "=" in cookie_str:
                try:
                    # 分割Cookie字符串
                    parts = cookie_str.split(";")[0].split("=", 1)
                    if len(parts) == 2:
                        name, value = parts
                        name = name.strip()
                        value = value.strip()
                        if name and value:
                            cookies[name] = value
                            logger.debug(f"Parsed cookie: {name}={value}")
                except Exception as e:
                    logger.warning(f"Failed to parse cookie: {cookie_str}, error: {str(e)}")

        return cookies

    def create_authenticated_request(
        self,
        url: str,
        method: str = "GET",
        data: Optional[Union[Dict, str]] = None,
        **kwargs
    ) -> requests.Request:
        """
        创建带认证信息的请求

        Args:
            url: 请求URL
            method: 请求方法
            data: 请求数据（可以是字典或字符串）
            **kwargs: 其他请求参数

        Returns:
            requests.Request: 请求对象
        """
        # 确保URL是完整的
        if not url.startswith(("http://", "https://")):
            url = urljoin(config.spider.base_url, url)

        # 获取完整的headers
        headers = self.headers
        if kwargs.get("headers"):
            headers.update(kwargs.pop("headers"))

        # 设置Referer
        if "Referer" not in headers:
            headers["Referer"] = f"{config.spider.base_url}/issues/?filter=37131"

        # 记录请求信息
        logger.debug(f"Creating {method} request to {url}")
        logger.debug(f"Headers: {headers}")
        if data:
            logger.debug(f"Data: {data}")

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

            logger.debug(f"Auth check response status: {response.status_code}")
            if response.status_code == 401:
                logger.debug(f"Auth check response content: {response.text}")

            # 检查响应状态并更新cookies
            if response.status_code == 200:
                new_cookies = self.parse_set_cookie(response)
                if new_cookies:
                    self.update_cookies(new_cookies)
                logger.info("Authentication check successful")
                return True

            logger.warning(f"Authentication check failed with status {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Authentication check error: {str(e)}")
            raise AuthError(f"认证检查失败: {str(e)}")

    def refresh_authentication(self) -> bool:
        """
        刷新认证信息

        Returns:
            bool: 是否刷新成功
        """
        try:
            logger.info("Attempting to refresh authentication")
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

            logger.debug(f"Auth refresh response status: {response.status_code}")
            logger.debug(f"Auth refresh response headers: {dict(response.headers)}")

            # 如果是重定向响应，认为登录成功
            if response.status_code in (302, 303):
                # 解析并更新Cookie
                new_cookies = self.parse_set_cookie(response)
                if new_cookies:
                    self.update_cookies(new_cookies)
                    logger.info("Authentication refresh successful")
                    return True

            logger.warning(f"Authentication refresh failed with status {response.status_code}")
            return False

        except Exception as e:
            logger.error(f"Authentication refresh error: {str(e)}")
            raise AuthError(f"认证刷新失败: {str(e)}")