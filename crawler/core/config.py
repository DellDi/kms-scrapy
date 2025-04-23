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
    start_urls: list[str] = ["http://kms.new-see.com:8090/pages/viewpage.action?pageId=27363329"]
    optimizer_type: str = "html2md"  # 优化器类型 html2md xunfei baichuan compatible
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
    # 附件过滤配置
    attachment_filters: Dict[str, Any] = {
        "excluded_mime_types": [
            "image/jpeg",
            "image/png",
            "image/gif",
            "image/svg+xml",
        ],  # 排除的MIME类型
        "excluded_extensions": [".jpg", ".jpeg", ".png", ".gif", ".svg"],  # 排除的文件扩展名
        "max_size_mb": 50,  # 最大附件大小(MB)，超过此大小的附件将被跳过
        "enabled": True,  # 是否启用附件过滤
    }


class BaichuanConfig(BaseModel):
    """百川API配置"""

    api_key: str
    api_url: str = "https://api.baichuan-ai.com/v1/chat/completions"


class XunfeiConfig(BaseModel):
    """讯飞API配置"""

    api_key: str
    api_url: str = "https://spark-api-open.xf-yun.com/v1/chat/completions"


class OpenAIConfig(BaseModel):
    """兼容openai 配置"""

    api_key: str
    api_url: str = "https://api.openai.com/v1/chat/completions"
    model: str = "gpt-3.5-turbo"


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
        self.openai = OpenAIConfig(
            api_key=os.getenv("OPENAI_API_KEY"),
            model=os.getenv("OPENAI_API_MODEL"),
            api_url=os.getenv("OPENAI_BASE_URL"),
        )


# 全局配置实例
config = Config()
