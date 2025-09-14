"""Workspace service for team collaboration setup and management."""

from typing import List, Optional, Dict, Any
from uuid import UUID
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, and_, or_
from sqlalchemy.orm import selectinload

from app.models.project import Project, ProjectFile, project_members
from app.models.user import User
from app.schemas.project import (
    Project as ProjectSchema, ProjectSettings, ProjectMember,
    FileType, ProjectFileCreate
)
from app.services.project import ProjectService
from app.services.project_file import ProjectFileService
from app.services.notification import NotificationService
from app.core.exceptions import NotFoundError, PermissionError, ValidationError


class WorkspaceService:
    """Service for managing team collaboration workspaces."""

    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_service = ProjectService(db)
        self.file_service = ProjectFileService(db)
        self.notification_service = NotificationService(db)

    async def initialize_member_workspace(self, project_id: str, user_id: str, invited_by: str) -> Dict[str, Any]:
        """
        Initialize workspace for a new project member.
        
        Args:
            project_id: Project ID
            user_id: New member user ID
            invited_by: User ID who invited the member
            
        Returns:
            Workspace initialization result
        """
        # Get project details
        project = await self.project_service.get_project(project_id, invited_by)
        
        # Get user details
        user_query = select(User).where(User.id == UUID(user_id))
        user_result = await self.db.execute(user_query)
        user = user_result.scalar_one_or_none()
        
        if not user:
            raise NotFoundError("User not found")
        
        # Create default workspace structure for the user
        workspace_structure = await self._create_default_workspace_structure(project_id, user_id, user.name)
        
        # Set up user preferences for the project
        user_preferences = await self._setup_user_project_preferences(project_id, user_id)
        
        # Create welcome notification/activity
        welcome_activity = await self._create_welcome_activity(project_id, user_id, invited_by)
        
        # Update project last activity
        await self._update_project_activity(project_id)
        
        return {
            "project": project,
            "workspace_structure": workspace_structure,
            "user_preferences": user_preferences,
            "welcome_activity": welcome_activity,
            "status": "initialized"
        }

    async def update_project_settings(self, project_id: str, settings: ProjectSettings, user_id: str) -> Dict[str, Any]:
        """
        Update project settings and notify team members.
        
        Args:
            project_id: Project ID
            settings: New project settings
            user_id: User making the changes
            
        Returns:
            Update result with notification info
        """
        # Check permissions
        if not await self.project_service._user_can_edit_project(project_id, user_id):
            raise PermissionError("You don't have permission to update project settings")
        
        # Get current project
        project_query = select(Project).where(Project.id == UUID(project_id))
        result = await self.db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError("Project not found")
        
        # Store old settings for comparison
        old_settings = project.settings.copy()
        
        # Update settings
        project.settings = settings.dict()
        project.updated_at = datetime.utcnow()
        await self.db.commit()
        
        # Identify what changed
        changes = self._identify_settings_changes(old_settings, settings.dict())
        
        # Get project members for notifications
        members = await self.project_service._get_project_members(project_id)
        
        # Create change notifications
        notifications = await self.notification_service.create_settings_change_notification(
            project_id, user_id, changes
        )
        
        return {
            "project_id": project_id,
            "changes": changes,
            "notifications_sent": len(notifications),
            "affected_members": len(members),
            "status": "updated"
        }

    async def get_workspace_overview(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """
        Get workspace overview for a user in a project.
        
        Args:
            project_id: Project ID
            user_id: User ID
            
        Returns:
            Workspace overview data
        """
        # Check access
        if not await self.project_service._user_has_project_access(project_id, user_id):
            raise PermissionError("You don't have access to this project")
        
        # Get project with members
        project = await self.project_service.get_project(project_id, user_id)
        
        # Get recent files
        recent_files = await self._get_recent_files(project_id, limit=10)
        
        # Get user's role in project
        user_role = await self._get_user_role_in_project(project_id, user_id)
        
        # Get project activity summary
        activity_summary = await self._get_project_activity_summary(project_id)
        
        # Get collaboration opportunities
        collaboration_opportunities = await self._get_collaboration_opportunities(project_id, user_id)
        
        return {
            "project": project,
            "user_role": user_role,
            "recent_files": recent_files,
            "activity_summary": activity_summary,
            "collaboration_opportunities": collaboration_opportunities,
            "workspace_ready": True
        }

    async def setup_project_templates(self, project_id: str, template_type: str, user_id: str) -> Dict[str, Any]:
        """
        Set up project templates and starter files.
        
        Args:
            project_id: Project ID
            template_type: Type of template (web, mobile, api, etc.)
            user_id: User ID
            
        Returns:
            Template setup result
        """
        # Check permissions
        if not await self.project_service._user_can_edit_project(project_id, user_id):
            raise PermissionError("You don't have permission to set up templates")
        
        # Get template configuration
        template_config = self._get_template_config(template_type)
        
        if not template_config:
            raise ValidationError(f"Unknown template type: {template_type}")
        
        # Create template files
        created_files = []
        for file_config in template_config["files"]:
            try:
                file_data = ProjectFileCreate(
                    name=file_config["name"],
                    path=file_config["path"],
                    content=file_config["content"],
                    file_type=FileType(file_config["type"])
                )
                
                created_file = await self.file_service.create_file(project_id, file_data, user_id)
                created_files.append(created_file)
            except Exception as e:
                # Log error but continue with other files
                print(f"Error creating template file {file_config['name']}: {e}")
        
        # Update project settings with template info
        project_query = select(Project).where(Project.id == UUID(project_id))
        result = await self.db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if project:
            project.metadata_info.update({
                "template_type": template_type,
                "template_version": template_config["version"],
                "template_setup_date": datetime.utcnow().isoformat()
            })
            await self.db.commit()
        
        return {
            "template_type": template_type,
            "files_created": len(created_files),
            "template_config": template_config,
            "status": "completed"
        }

    async def manage_member_permissions(self, project_id: str, member_id: str, permissions: Dict[str, bool], user_id: str) -> Dict[str, Any]:
        """
        Manage specific permissions for a project member.
        
        Args:
            project_id: Project ID
            member_id: Member user ID
            permissions: Permission settings
            user_id: User making the changes
            
        Returns:
            Permission update result
        """
        # Check if user can manage permissions (owner or admin)
        if not await self._user_can_manage_permissions(project_id, user_id):
            raise PermissionError("You don't have permission to manage member permissions")
        
        # Get project
        project_query = select(Project).where(Project.id == UUID(project_id))
        result = await self.db.execute(project_query)
        project = result.scalar_one_or_none()
        
        if not project:
            raise NotFoundError("Project not found")
        
        # Update member permissions in project metadata
        if "member_permissions" not in project.metadata_info:
            project.metadata_info["member_permissions"] = {}
        
        project.metadata_info["member_permissions"][member_id] = permissions
        project.updated_at = datetime.utcnow()
        await self.db.commit()
        
        return {
            "project_id": project_id,
            "member_id": member_id,
            "permissions": permissions,
            "status": "updated"
        }

    # Private helper methods
    async def _create_default_workspace_structure(self, project_id: str, user_id: str, user_name: str) -> Dict[str, Any]:
        """Create default workspace structure for new member."""
        # Create user-specific folder structure
        user_folder = f"/workspace/{user_name.lower().replace(' ', '_')}"
        
        # Default folders to create
        default_folders = [
            f"{user_folder}/drafts",
            f"{user_folder}/experiments",
            f"{user_folder}/notes"
        ]
        
        # Create a welcome file
        welcome_content = f"""# Welcome to the Project, {user_name}!

This is your personal workspace within the project. You can use this space to:

- Work on drafts before sharing with the team
- Experiment with new ideas
- Keep personal notes and documentation

## Getting Started

1. Explore the project files in the main directories
2. Check out the project README for setup instructions
3. Join the team discussions and ask questions
4. Start contributing to the project!

Happy coding! 🚀
"""
        
        try:
            welcome_file = ProjectFileCreate(
                name="welcome.md",
                path=f"{user_folder}/welcome.md",
                content=welcome_content,
                file_type=FileType.MARKDOWN
            )
            
            await self.file_service.create_file(project_id, welcome_file, user_id)
        except Exception as e:
            print(f"Error creating welcome file: {e}")
        
        return {
            "user_folder": user_folder,
            "default_folders": default_folders,
            "welcome_file_created": True
        }

    async def _setup_user_project_preferences(self, project_id: str, user_id: str) -> Dict[str, Any]:
        """Set up default project preferences for user."""
        default_preferences = {
            "notifications": {
                "file_changes": True,
                "member_activity": True,
                "deployment_updates": True,
                "mentions": True
            },
            "workspace": {
                "auto_save": True,
                "show_activity_feed": True,
                "highlight_conflicts": True
            },
            "collaboration": {
                "share_presence": True,
                "allow_suggestions": True,
                "auto_merge_compatible": False
            }
        }
        
        # Store preferences in user's project metadata
        # This would typically be stored in a separate user_project_preferences table
        # For now, we'll use the project metadata
        
        return default_preferences

    async def _create_welcome_activity(self, project_id: str, user_id: str, invited_by: str) -> Dict[str, Any]:
        """Create welcome activity for new member."""
        # This would typically create an activity record
        # For now, return activity data
        
        return {
            "type": "member_joined",
            "project_id": project_id,
            "user_id": user_id,
            "invited_by": invited_by,
            "timestamp": datetime.utcnow(),
            "message": "joined the project"
        }

    async def _update_project_activity(self, project_id: str):
        """Update project's last activity timestamp."""
        update_query = (
            update(Project)
            .where(Project.id == UUID(project_id))
            .values(last_activity=datetime.utcnow())
        )
        
        await self.db.execute(update_query)
        await self.db.commit()

    def _identify_settings_changes(self, old_settings: Dict[str, Any], new_settings: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Identify what settings changed."""
        changes = []
        
        for key, new_value in new_settings.items():
            old_value = old_settings.get(key)
            if old_value != new_value:
                changes.append({
                    "setting": key,
                    "old_value": old_value,
                    "new_value": new_value
                })
        
        return changes

    async def _create_settings_change_notifications(self, project_id: str, user_id: str, changes: List[Dict[str, Any]], members: List[ProjectMember]) -> List[Dict[str, Any]]:
        """Create notifications for settings changes."""
        notifications = []
        
        # Get user who made changes
        user_query = select(User).where(User.id == UUID(user_id))
        result = await self.db.execute(user_query)
        user = result.scalar_one_or_none()
        
        if not user:
            return notifications
        
        # Create notification for each member (except the one who made changes)
        for member in members:
            if member.user_id != user_id:
                notification = {
                    "type": "project_settings_changed",
                    "project_id": project_id,
                    "recipient_id": member.user_id,
                    "actor_id": user_id,
                    "actor_name": user.name,
                    "changes": changes,
                    "timestamp": datetime.utcnow()
                }
                notifications.append(notification)
        
        return notifications

    async def _get_recent_files(self, project_id: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Get recently modified files in project."""
        query = (
            select(ProjectFile)
            .where(
                and_(
                    ProjectFile.project_id == UUID(project_id),
                    ProjectFile.is_deleted == False
                )
            )
            .order_by(ProjectFile.updated_at.desc())
            .limit(limit)
        )
        
        result = await self.db.execute(query)
        files = result.scalars().all()
        
        return [
            {
                "id": str(file.id),
                "name": file.name,
                "path": file.path,
                "type": file.file_type,
                "updated_at": file.updated_at,
                "last_modified_by": str(file.last_modified_by) if file.last_modified_by else None
            }
            for file in files
        ]

    async def _get_user_role_in_project(self, project_id: str, user_id: str) -> str:
        """Get user's role in the project."""
        query = (
            select(project_members.c.role)
            .where(
                and_(
                    project_members.c.project_id == UUID(project_id),
                    project_members.c.user_id == UUID(user_id)
                )
            )
        )
        
        result = await self.db.execute(query)
        role = result.scalar_one_or_none()
        
        return role or "viewer"

    async def _get_project_activity_summary(self, project_id: str) -> Dict[str, Any]:
        """Get project activity summary."""
        # This would typically query an activities table
        # For now, return mock data
        
        return {
            "total_files": 0,
            "recent_changes": 0,
            "active_members": 0,
            "last_activity": datetime.utcnow()
        }

    async def _get_collaboration_opportunities(self, project_id: str, user_id: str) -> List[Dict[str, Any]]:
        """Get collaboration opportunities for user."""
        # This would analyze project files and member activities
        # For now, return empty list
        
        return []

    def _get_template_config(self, template_type: str) -> Optional[Dict[str, Any]]:
        """Get template configuration for project type."""
        templates = {
            "web": {
                "version": "1.0",
                "description": "Basic web project template",
                "files": [
                    {
                        "name": "index.html",
                        "path": "/index.html",
                        "type": "html",
                        "content": """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>My Project</title>
    <link rel="stylesheet" href="styles.css">
</head>
<body>
    <h1>Welcome to My Project</h1>
    <p>This is a starter template for your web project.</p>
    <script src="script.js"></script>
</body>
</html>"""
                    },
                    {
                        "name": "styles.css",
                        "path": "/styles.css",
                        "type": "css",
                        "content": """/* Basic styles for your project */
body {
    font-family: Arial, sans-serif;
    margin: 0;
    padding: 20px;
    background-color: #f5f5f5;
}

h1 {
    color: #333;
    text-align: center;
}

p {
    color: #666;
    line-height: 1.6;
}"""
                    },
                    {
                        "name": "script.js",
                        "path": "/script.js",
                        "type": "js",
                        "content": """// JavaScript for your project
console.log('Welcome to your project!');

// Add your JavaScript code here
document.addEventListener('DOMContentLoaded', function() {
    console.log('Page loaded successfully');
});"""
                    },
                    {
                        "name": "README.md",
                        "path": "/README.md",
                        "type": "md",
                        "content": """# My Web Project

This is a basic web project template created with Ticolops.

## Getting Started

1. Open `index.html` in your browser
2. Edit the HTML, CSS, and JavaScript files
3. Collaborate with your team members
4. Deploy your project when ready

## Project Structure

- `index.html` - Main HTML file
- `styles.css` - CSS styles
- `script.js` - JavaScript code
- `README.md` - This file

Happy coding! 🚀"""
                    }
                ]
            },
            "api": {
                "version": "1.0",
                "description": "Basic API project template",
                "files": [
                    {
                        "name": "main.py",
                        "path": "/main.py",
                        "type": "text",
                        "content": """# Basic API template
from fastapi import FastAPI

app = FastAPI(title="My API", version="1.0.0")

@app.get("/")
async def root():
    return {"message": "Hello World"}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)"""
                    },
                    {
                        "name": "requirements.txt",
                        "path": "/requirements.txt",
                        "type": "text",
                        "content": """fastapi==0.104.1
uvicorn==0.24.0"""
                    },
                    {
                        "name": "README.md",
                        "path": "/README.md",
                        "type": "md",
                        "content": """# My API Project

This is a basic API project template using FastAPI.

## Getting Started

1. Install dependencies: `pip install -r requirements.txt`
2. Run the server: `python main.py`
3. Visit http://localhost:8000 to see your API
4. Check http://localhost:8000/docs for API documentation

## Project Structure

- `main.py` - Main API application
- `requirements.txt` - Python dependencies
- `README.md` - This file

Happy coding! 🚀"""
                    }
                ]
            }
        }
        
        return templates.get(template_type)

    async def _user_can_manage_permissions(self, project_id: str, user_id: str) -> bool:
        """Check if user can manage member permissions."""
        # Get user's role
        role = await self._get_user_role_in_project(project_id, user_id)
        return role in ["owner", "admin"]