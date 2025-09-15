"""API router for work-items (demo).
"""

from fastapi import APIRouter, Depends, HTTPException
from typing import List, Optional
from pydantic import BaseModel
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.services.work_item import WorkItemService

router = APIRouter(prefix="/projects/{project_id}/work-items")


class WorkItemCreate(BaseModel):
    title: str
    description: str | None = None
    assignee_id: str | None = None
    repository_url: str | None = None


class WorkItemOut(BaseModel):
    id: UUID
    project_id: UUID
    title: str
    description: Optional[str]
    status: str
    assignee_id: Optional[UUID]
    repository_url: Optional[str]
    created_at: Optional[datetime]

    class Config:
        orm_mode = True


@router.post("/", response_model=WorkItemOut)
async def create_work_item(project_id: str, payload: WorkItemCreate, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    service = WorkItemService(db)
    try:
        wi = await service.create_work_item(project_id, payload.title, payload.description, payload.assignee_id, payload.repository_url)
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))
    return wi


@router.get("/", response_model=List[WorkItemOut])
async def list_work_items(project_id: str, db: AsyncSession = Depends(get_db), user=Depends(get_current_user)):
    service = WorkItemService(db)
    items = await service.list_project_work_items(project_id)
    return items
