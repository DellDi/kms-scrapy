"""请求模型定义."""

from pydantic import BaseModel, Field


class CrawlRequest(BaseModel):
    """爬虫请求模型."""

    jql: str = Field(
        default="assignee = currentUser() AND resolution = Unresolved order by updated DESC",
        description="JQL查询语句",
    )

    description_limit: int = Field(default=400, description="问题描述截断长度")

    comments_limit: int = Field(default=10, description="问题评论个数")

    page_size: int = Field(default=500, description="每页数量")

    start_at: int = Field(default=0, description="起始位置")

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {
                "page_size": 500,
                "start_at": 0,
                "description_limit": 400,
                "comments_limit": 10,
                "jql": "assignee = currentUser() AND resolution = Unresolved order by updated DESC",
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
        default="标准检索知识库",
        description="数据集名称前缀",
    )

    max_docs: int = Field(default=12000, description="每个数据集的最大文档数量")

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {"dataset_prefix": "大品控父子检索知识库", "max_docs": 12000}
        }


class JiraITOPSRequest(BaseModel):
    """Jira ITOPS工单创建请求模型."""

    summary: str = Field(default="ITOPS工单标题", description="工单标题")
    assignee: str = Field(default="zengdi", description="经办人ID，默认-1表示未分配")
    creater: str = Field(default="zengdi", description="创建人用户名")
    password: str = Field(default="1", description="创建人密码")
    issuetype: str = Field(default="11203", description="问题类型ID")
    description: str = Field(default="工单描述", description="工单描述")

    class Config:
        """配置."""

        json_schema_extra = {
            "example": {
                "summary": "ITOPS工单标题",
                "assignee": "zengdi",
                "creater": "zengdi",
                "password": "1",
                "issuetype": "11203",
                "description": "工单详细描述",
            }
        }
