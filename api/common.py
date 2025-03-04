"""系统监控"""

from typing import List
from fastapi import APIRouter, Depends, Query
from sqlmodel import Session, select

from api.database.db import get_db
from api.database.models import ApiLog

router = APIRouter(prefix="/api/common")


@router.get(
    "/logs",
    response_model=List[ApiLog],
    tags=["系统监控"],
)
async def get_logs(
    skip: int = Query(0, description="跳过记录数"),
    limit: int = Query(10, description="返回记录数"),
    path: str = Query(None, description="按路径筛选"),
    status: int = Query(None, description="按状态码筛选"),
    db: Session = Depends(get_db),
) -> List[ApiLog]:
    """获取API请求日志."""
    query = select(ApiLog)
    if path:
        query = query.where(ApiLog.request_path.contains(path))
    if status:
        query = query.where(ApiLog.response_status == status)
    query = query.offset(skip).limit(limit).order_by(ApiLog.created_at.desc())
    return db.exec(query).all()
