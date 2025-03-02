"""请求模型定义."""
from pydantic import BaseModel, Field

class CrawlRequest(BaseModel):
    """爬虫请求模型."""

    jql: str = Field(
        default="assignee = currentUser() AND resolution = Unresolved order by updated DESC",
        description="JQL查询语句",
    )

    page_size: int = Field(default=500, description="每页数量")

    start_at: int = Field(default=0, description="起始位置")

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {
                "page_size": 500,
                "start_at": 0,
                "jql": "assignee = currentUser() AND resolution = Unresolved order by updated DESC"
            }
        }
