from dataclasses import dataclass, field
from typing import Dict, List

@dataclass
class AuthConfig:
    """认证配置"""
    username: str = "newsee"
    password: str = "newsee"
    basic_auth: str = "bmV3c2VlOm5ld3NlZQ=="  # base64(newsee:newsee)

@dataclass
class SpiderConfig:
    """爬虫配置"""
    base_url: str = "http://bug.new-see.com:8088"
    download_delay: float = 1.0
    concurrent_requests: int = 1
    retry_times: int = 3
    retry_http_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504, 400])

    # 默认请求头
    default_headers: Dict[str, str] = field(default_factory=lambda: {
        "Accept": "*/*",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
        "Content-Type": "application/x-www-form-urlencoded; charset=UTF-8",
        "X-Atlassian-Token": "no-check",
        "X-Requested-With": "XMLHttpRequest",
        "__amdModuleName": "jira/issue/utils/xsrf-token-header",
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
        )
    })

    # 默认Cookie
    default_cookies: Dict[str, str] = field(default_factory=lambda: {
        "JSESSIONID": "",
        "seraph.rememberme.cookie": "",
        "atlassian.xsrf.token": "",
        "ajs_user_id": "",
        "ajs_anonymous_id": ""
    })

@dataclass
class OptimizerConfig:
    """优化器配置"""
    api_key: str = ""  # 优化器API密钥
    api_url: str = ""  # 优化器API地址
    optimizer_type: str = "xunfei"  # 使用的优化器类型

@dataclass
class ExporterConfig:
    """导出器配置"""
    output_dir: str = "output-jira"  # 输出根目录
    page_dir_prefix: str = "page"    # 分页目录前缀
    encoding: str = "utf-8"          # 文件编码

@dataclass
class Config:
    """全局配置类"""
    auth: AuthConfig = field(default_factory=AuthConfig)
    spider: SpiderConfig = field(default_factory=SpiderConfig)
    optimizer: OptimizerConfig = field(default_factory=OptimizerConfig)
    exporter: ExporterConfig = field(default_factory=ExporterConfig)

    def update_from_env(self):
        """从环境变量更新配置"""
        # TODO: 实现从环境变量加载配置的逻辑
        pass

# 全局配置实例
config = Config()

# 如果有环境变量配置，更新配置
config.update_from_env()