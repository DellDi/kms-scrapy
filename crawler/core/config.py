from typing import Dict, Any
from pydantic import BaseModel
from dotenv import load_dotenv
import os

load_dotenv()


class AuthConfig(BaseModel):
    """认证配置"""

    username: str
    password: str
    basic_auth_user: str
    basic_auth_pass: str


class SpiderConfig(BaseModel):
    """爬虫配置"""
    output_dir: str = "output-kms"
    start_urls: list[str] = ["http://kms.new-see.com:8090"]
    download_delay: int = 4
    concurrent_requests: int = 2
    retry_times: int = 5
    retry_http_codes: list[int] = [500, 502, 503, 504, 408, 429]
    default_headers: Dict[str, str] = {
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36",
    }
    default_cookies: Dict[str, str] = {
        "confluence.list.pages.cookie": "list-content-tree",
        "ajs_user_id": "b855f69db6d93f0a1a50b21008c841d7416fc802",
        "ajs_anonymous_id": "be8fadfe-3cd8-4b1b-9c20-c467f8b20eae",
    }


class BaichuanConfig(BaseModel):
    """百川API配置"""

    api_key: str
    api_url: str = "https://api.baichuan-ai.com/v1/chat/completions"


class XunfeiConfig(BaseModel):
    """讯飞API配置"""

    api_key: str
    api_url: str = "https://spark-api-open.xf-yun.com/v1/chat/completions"


class Config:
    """全局配置类"""

    def __init__(self):

        self.auth = AuthConfig(
            username=os.getenv("CONFLUENCE_USERNAME", "zengdi"),
            password=os.getenv("CONFLUENCE_PASSWORD", "808611"),
            basic_auth_user=os.getenv("BASIC_AUTH_USER", "newsee"),
            basic_auth_pass=os.getenv("BASIC_AUTH_PASS", "newsee"),
        )
        self.spider = SpiderConfig()
        self.baichuan = BaichuanConfig(api_key=os.getenv("BAI_CH_API_KEK"))
        self.xunfei = XunfeiConfig(api_key=os.getenv("XUNFEI_API_KEY"))


# 全局配置实例
config = Config()
