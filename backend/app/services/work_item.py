"""Service layer for WorkItem operations (create/list)."""

from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.models.work_item import WorkItem, WorkItemStatus
from app.models.project import Project
from app.models.user import User
from app.services.git_provider import get_repo_info
import logging

logger = logging.getLogger(__name__)


class WorkItemService:
    def __init__(self, db: AsyncSession):
        self.db = db

    async def create_work_item(self, project_id: str, title: str, description: Optional[str] = None, assignee_id: Optional[str] = None, repository_url: Optional[str] = None) -> WorkItem:
        wi = WorkItem(
            project_id=project_id,
            title=title,
            description=description,
            assignee_id=assignee_id,
            repository_url=repository_url
        )
        self.db.add(wi)
        await self.db.commit()
        # Refresh may trigger relationship loader codepaths that can fail in
        # a minimal/demo DB. Don't fail the whole request if refresh errors.
        try:
            await self.db.refresh(wi)
        except Exception:
            logger.exception("Non-fatal error while refreshing WorkItem")

        # Pre-fetch repo info (non-blocking best-effort)
        if repository_url:
            try:
                repo_info = get_repo_info(repository_url)
                logger.info('WorkItem created with repo: %s', repo_info.get('url'))
            except Exception:
                logger.exception('Failed to fetch repo info for %s', repository_url)

        return wi

    async def list_project_work_items(self, project_id: str) -> List[WorkItem]:
        q = select(WorkItem).where(WorkItem.project_id == project_id).order_by(WorkItem.created_at.desc())
        try:
            res = await self.db.execute(q)
            items = res.scalars().all()
            return items
        except Exception as exc:
            # If the work_items table doesn't exist in this demo DB, return
            # an empty list instead of raising a 500 so the frontend can
            # continue to function.
            logger.warning("Could not list work items for project %s: %s", project_id, exc)
            try:
                await self.db.rollback()
            except Exception:
                logger.exception("Failed to rollback after work_items listing error")
            return []
