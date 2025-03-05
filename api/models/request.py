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

class CrawlKMSRequest(BaseModel):
    """爬虫KMS请求模型."""

    start_url: str = Field(..., description="起始URL")

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {
                "start_url": "http://kms.new-see.com:8090/pages/viewpage.action?pageId=92012631"
            }
        }


class DifyUploadRequest(BaseModel):
    """Dify 知识库导入请求模型."""

    dataset_prefix: str = Field(
        default="大品控父子检索知识库",
        description="数据集名称前缀",
    )

    max_docs: int = Field(
        default=12000, 
        description="每个数据集的最大文档数量"
    )

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {
                "dataset_prefix": "大品控父子检索知识库",
                "max_docs": 12000
            }
        }
