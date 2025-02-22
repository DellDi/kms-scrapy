"""
爬虫数据模型定义
"""
from datetime import datetime
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl
from scrapy import Item, Field as ScrapyField

class HotSearchItem(Item):
    """热搜数据项（Scrapy Item）"""

    # 基本信息
    title = ScrapyField()          # 标题
    rank = ScrapyField()           # 排名
    heat_score = ScrapyField()     # 热度值
    url = ScrapyField()            # 原文链接

    # 内容信息
    content = ScrapyField()        # 详细内容
    summary = ScrapyField()        # 内容摘要
    tags = ScrapyField()          # 标签列表

    # 元数据
    crawl_time = ScrapyField()     # 爬取时间
    source = ScrapyField()         # 来源
    category = ScrapyField()       # 分类

    # 状态信息
    state = ScrapyField()          # 处理状态: pending, completed, failed, no_content
    error = ScrapyField()          # 错误信息

class HotSearchData(BaseModel):
    """热搜数据（Pydantic Model）"""

    # 基本信息
    title: str = Field(..., min_length=1, max_length=200, description="热搜标题")
    rank: int = Field(..., ge=1, le=100, description="热搜排名")
    heat_score: int = Field(..., ge=0, description="热度值")
    url: HttpUrl = Field(..., description="原文链接")

    # 内容信息
    content: Optional[str] = Field(None, max_length=10000, description="详细内容")
    summary: Optional[str] = Field(None, max_length=500, description="内容摘要")
    tags: List[str] = Field(default_factory=list, description="标签列表")

    # 元数据
    crawl_time: datetime = Field(default_factory=datetime.now, description="爬取时间")
    source: str = Field(default="baidu", description="来源")
    category: Optional[str] = Field(None, description="分类")

    # 状态信息
    state: str = Field(
        default="pending",
        description="处理状态",
        pattern="^(pending|completed|failed|no_content)$"
    )
    error: Optional[str] = Field(None, description="错误信息")

    class Config:
        """Pydantic 配置"""
        arbitrary_types_allowed = True
        json_encoders = {
            datetime: lambda v: v.isoformat()
        }

    def to_item(self) -> HotSearchItem:
        """转换为 Scrapy Item"""
        return HotSearchItem(**self.dict())

    @classmethod
    def from_item(cls, item: HotSearchItem) -> 'HotSearchData':
        """从 Scrapy Item 创建"""
        return cls(**dict(item))