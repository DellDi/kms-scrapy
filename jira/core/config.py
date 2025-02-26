from dataclasses import dataclass, field
from typing import Dict, List
from datetime import datetime

@dataclass
class AuthConfig:
    """认证配置"""
    username: str = "zengdi"
    password: str = "1"
    basic_auth: str = "bmV3c2VlOm5ld3NlZQ=="  # base64(newsee:newsee)

@dataclass
class SpiderConfig:
    """爬虫配置"""
    base_url: str = "http://bug.new-see.com:8088"
    download_delay: float = 1.0
    concurrent_requests: int = 1
    retry_times: int = 3
    retry_http_codes: List[int] = field(default_factory=lambda: [500, 502, 503, 504, 400])

    # 查询参数
    page_size: int = 500  # 每页数量
    start_at: int = 0  # 起始位置
    jql: str = (  # JQL查询条件
        "assignee = currentUser() AND resolution = Unresolved order by updated DESC "
    )

    # 默认请求头
    default_headers: Dict[str, str] = field(
        default_factory=lambda: {
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7",
            "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8,en-GB;q=0.7,en-US;q=0.6",
            "Cache-Control": "no-cache",
            "Host": "bug.new-see.com:8088",
            "Proxy-Connection": "keep-alive",
            "Pragma": "no-cache",
            "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/133.0.0.0 Safari/537.36 Edg/133.0.0.0"
        }
    )

    # 默认Cookie模板 (这些值将在登录时动态更新)
    default_cookies: Dict[str, str] = field(
        default_factory=lambda: {
            "ajs_user_id": "b855f69db6d93f0a1a50b21008c841d7416fc802",
            "ajs_anonymous_id": "be8fadfe-3cd8-4b1b-9c20-c467f8b20eae",
            "JSESSIONID": "96B1846618FD77935FF3F931B540D18D",
            "atlassian.xsrf.token": "AYXN-UMWG-3K4D-ZXVN_a6ee74f8634507193fe1e38c32b8a86f95b7a130_lout"
        }
    )

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
