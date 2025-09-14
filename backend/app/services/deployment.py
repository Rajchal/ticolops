"""Deployment pipeline service for automated builds and deployments."""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple
from uuid import UUID
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, or_, desc, func
from sqlalchemy.orm import selectinload

from app.models.deployment import (
    Deployment, DeploymentStatus, DeploymentTrigger, ProjectType,
    DeploymentEnvironment, BuildConfiguration, DeploymentHook
)
from app.models.repository import Repository
from app.models.project import Project
from app.core.config import settings
from app.core.exceptions import NotFoundError, ValidationError
from app.services.repository import RepositoryService

logger = logging.getLogger(__name__)


class ProjectTypeDetector:
    """Service for detecting project types from repository contents."""
    
    # Project type detection patterns
    DETECTION_PATTERNS = {
        ProjectType.REACT: {
            "files": ["package.json", "src/App.js", "src/App.jsx", "src/App.tsx"],
            "package_dependencies": ["react", "react-dom"],
            "package_scripts": ["start", "build"],
            "confidence_threshold": 0.8
        },
        ProjectType.NEXTJS: {
            "files": ["package.json", "next.config.js", "pages/index.js", "app/page.js"],
            "package_dependencies": ["next", "react"],
            "package_scripts": ["dev", "build", "start"],
            "confidence_threshold": 0.9
        },
        ProjectType.VUE: {
            "files": ["package.json", "src/App.vue", "vue.config.js"],
            "package_dependencies": ["vue"],
            "package_scripts": ["serve", "build"],
            "confidence_threshold": 0.8
        },
        ProjectType.ANGULAR: {
            "files": ["package.json", "angular.json", "src/app/app.component.ts"],
            "package_dependencies": ["@angular/core", "@angular/cli"],
            "package_scripts": ["ng", "start", "build"],
            "confidence_threshold": 0.9
        },
        ProjectType.NODE: {
            "files": ["package.json", "server.js", "app.js", "index.js"],
            "package_dependencies": ["express", "fastify", "koa"],
            "package_scripts": ["start"],
            "confidence_threshold": 0.7
        },
        ProjectType.PYTHON: {
            "files": ["requirements.txt", "setup.py", "pyproject.toml", "main.py"],
            "package_dependencies": [],
            "confidence_threshold": 0.6
        },
        ProjectType.DJANGO: {
            "files": ["requirements.txt", "manage.py", "settings.py"],
            "package_dependencies": ["django"],
            "confidence_threshold": 0.9
        },
        ProjectType.FLASK: {
            "files": ["requirements.txt", "app.py", "wsgi.py"],
            "package_dependencies": ["flask"],
            "confidence_threshold": 0.8
        },
        ProjectType.FASTAPI: {
            "files": ["requirements.txt", "main.py", "app.py"],
            "package_dependencies": ["fastapi", "uvicorn"],
            "confidence_threshold": 0.8
        },
        ProjectType.STATIC: {
            "files": ["index.html", "style.css", "script.js"],
            "package_dependencies": [],
            "confidence_threshold": 0.5
        }
    }
    
    # Default build configurations for each project type
    DEFAULT_BUILD_CONFIGS = {
        ProjectType.REACT: {
            "build_command": "npm run build",
            "output_directory": "build",
            "install_command": "npm install",
            "node_version": "18"
        },
        ProjectType.NEXTJS: {
            "build_command": "npm run build",
            "output_directory": ".next",
            "install_command": "npm install",
            "node_version": "18"
        },
        ProjectType.VUE: {
            "build_command": "npm run build",
            "output_directory": "dist",
            "install_command": "npm install",
            "node_version": "18"
        },
        ProjectType.ANGULAR: {
            "build_command": "npm run build",
            "output_directory": "dist",
            "install_command": "npm install",
            "node_version": "18"
        },
        ProjectType.NODE: {
            "build_command": "npm install",
            "output_directory": ".",
            "install_command": "npm install",
            "node_version": "18"
        },
        ProjectType.PYTHON: {
            "build_command": "pip install -r requirements.txt",
            "output_directory": ".",
            "install_command": "pip install -r requirements.txt",
            "python_version": "3.11"
        },
        ProjectType.DJANGO: {
            "build_command": "pip install -r requirements.txt && python manage.py collectstatic --noinput",
            "output_directory": "staticfiles",
            "install_command": "pip install -r requirements.txt",
            "python_version": "3.11"
        },
        ProjectType.FLASK: {
            "build_command": "pip install -r requirements.txt",
            "output_directory": ".",
            "install_command": "pip install -r requirements.txt",
            "python_version": "3.11"
        },
        ProjectType.FASTAPI: {
            "build_command": "pip install -r requirements.txt",
            "output_directory": ".",
            "install_command": "pip install -r requirements.txt",
            "python_version": "3.11"
        },
        ProjectType.STATIC: {
            "build_command": "",
            "output_directory": ".",
            "install_command": "",
            "node_version": ""
        }
    }
    
    async def detect_project_type(
        self,
        repository_files: List[str],
        package_json_content: Optional[Dict[str, Any]] = None,
        requirements_txt_content: Optional[str] = None
    ) -> Tuple[ProjectType, float, List[str]]:
        """
        Detect project type from repository files and content.
        
        Args:
            repository_files: List of file paths in the repository
            package_json_content: Parsed package.json content
            requirements_txt_content: Contents of requirements.txt
            
        Returns:
            Tuple of (project_type, confidence, detected_files)
        """
        scores = {}
        detected_files_map = {}
        
        for project_type, patterns in self.DETECTION_PATTERNS.items():
            score = 0.0
            detected_files = []
            
            # Check for required files
            file_matches = 0
            for required_file in patterns["files"]:
                if any(required_file in file_path for file_path in repository_files):
                    file_matches += 1
                    detected_files.append(required_file)
            
            if patterns["files"]:
                score += (file_matches / len(patterns["files"])) * 0.6
            
            # Check package.json dependencies for JavaScript projects
            if package_json_content and patterns.get("package_dependencies"):
                deps = package_json_content.get("dependencies", {})
                dev_deps = package_json_content.get("devDependencies", {})
                all_deps = {**deps, **dev_deps}
                
                dep_matches = 0
                for required_dep in patterns["package_dependencies"]:
                    if required_dep in all_deps:
                        dep_matches += 1
                        detected_files.append(f"package.json:{required_dep}")
                
                if patterns["package_dependencies"]:
                    score += (dep_matches / len(patterns["package_dependencies"])) * 0.3
                
                # Check package.json scripts
                scripts = package_json_content.get("scripts", {})
                script_matches = 0
                for required_script in patterns.get("package_scripts", []):
                    if required_script in scripts:
                        script_matches += 1
                
                if patterns.get("package_scripts"):
                    score += (script_matches / len(patterns["package_scripts"])) * 0.1
            
            # Check requirements.txt for Python projects
            if requirements_txt_content and patterns.get("package_dependencies"):
                req_matches = 0
                for required_dep in patterns["package_dependencies"]:
                    if required_dep in requirements_txt_content.lower():
                        req_matches += 1
                        detected_files.append(f"requirements.txt:{required_dep}")
                
                if patterns["package_dependencies"]:
                    score += (req_matches / len(patterns["package_dependencies"])) * 0.3
            
            scores[project_type] = score
            detected_files_map[project_type] = detected_files
        
        # Find the project type with the highest score
        best_type = max(scores.keys(), key=lambda k: scores[k])
        best_score = scores[best_type]
        best_files = detected_files_map[best_type]
        
        # If score is too low, default to UNKNOWN
        threshold = self.DETECTION_PATTERNS[best_type]["confidence_threshold"]
        if best_score < threshold:
            return ProjectType.UNKNOWN, best_score, best_files
        
        return best_type, best_score, best_files
    
    def get_build_config(self, project_type: ProjectType) -> Dict[str, Any]:
        """Get default build configuration for a project type."""
        return self.DEFAULT_BUILD_CONFIGS.get(project_type, self.DEFAULT_BUILD_CONFIGS[ProjectType.STATIC])


class DeploymentService:
    """Service for managing deployment pipelines and automation."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.project_detector = ProjectTypeDetector()
    
    async def create_deployment(
        self,
        repository_id: str,
        commit_sha: str,
        branch: str,
        trigger: DeploymentTrigger = DeploymentTrigger.PUSH,
        environment_id: Optional[str] = None,
        build_config: Optional[Dict[str, Any]] = None,
        environment_variables: Optional[Dict[str, str]] = None
    ) -> Deployment:
        """
        Create a new deployment.
        
        Args:
            repository_id: Repository ID
            commit_sha: Git commit SHA
            branch: Git branch name
            trigger: Deployment trigger type
            environment_id: Target environment ID (optional)
            build_config: Build configuration override
            environment_variables: Environment variables override
            
        Returns:
            Created deployment record
        """
        # Get repository with project
        query = select(Repository).options(
            selectinload(Repository.project)
        ).where(Repository.id == UUID(repository_id))
        result = await self.db.execute(query)
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise NotFoundError(f"Repository {repository_id} not found")
        
        # Detect project type if not provided in build_config
        project_type = ProjectType.UNKNOWN
        if build_config and "project_type" in build_config:
            project_type = ProjectType(build_config["project_type"])
        else:
            # TODO: Implement actual file detection from repository
            # For now, use repository deployment config or default
            repo_config = repository.deployment_config or {}
            project_type = ProjectType(repo_config.get("project_type", ProjectType.UNKNOWN.value))
        
        # Merge build configuration
        final_build_config = self.project_detector.get_build_config(project_type)
        if build_config:
            final_build_config.update(build_config)
        
        # Merge environment variables
        final_env_vars = {}
        if repository.deployment_config and "environment_variables" in repository.deployment_config:
            final_env_vars.update(repository.deployment_config["environment_variables"])
        if environment_variables:
            final_env_vars.update(environment_variables)
        
        # Create deployment record
        deployment = Deployment(
            repository_id=UUID(repository_id),
            project_id=repository.project_id,
            commit_sha=commit_sha,
            branch=branch,
            trigger=trigger.value,
            status=DeploymentStatus.PENDING.value,
            project_type=project_type.value,
            build_config=final_build_config,
            environment_variables=final_env_vars
        )
        
        self.db.add(deployment)
        await self.db.commit()
        await self.db.refresh(deployment)
        
        logger.info(f"Created deployment {deployment.id} for repository {repository_id}")
        
        # Trigger deployment execution asynchronously
        asyncio.create_task(self._execute_deployment(deployment.id))
        
        return deployment
    
    async def get_deployment(self, deployment_id: str) -> Deployment:
        """Get deployment by ID."""
        query = select(Deployment).options(
            selectinload(Deployment.repository),
            selectinload(Deployment.project)
        ).where(Deployment.id == UUID(deployment_id))
        result = await self.db.execute(query)
        deployment = result.scalar_one_or_none()
        
        if not deployment:
            raise NotFoundError(f"Deployment {deployment_id} not found")
        
        return deployment
    
    async def get_repository_deployments(
        self,
        repository_id: str,
        limit: int = 50,
        status_filter: Optional[DeploymentStatus] = None
    ) -> List[Deployment]:
        """
        Get deployments for a repository.
        
        Args:
            repository_id: Repository ID
            limit: Maximum number of deployments to return
            status_filter: Filter by deployment status
            
        Returns:
            List of deployments
        """
        query = select(Deployment).where(
            Deployment.repository_id == UUID(repository_id)
        ).order_by(desc(Deployment.created_at)).limit(limit)
        
        if status_filter:
            query = query.where(Deployment.status == status_filter.value)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def get_project_deployments(
        self,
        project_id: str,
        limit: int = 50,
        status_filter: Optional[DeploymentStatus] = None
    ) -> List[Deployment]:
        """
        Get deployments for a project.
        
        Args:
            project_id: Project ID
            limit: Maximum number of deployments to return
            status_filter: Filter by deployment status
            
        Returns:
            List of deployments
        """
        query = select(Deployment).options(
            selectinload(Deployment.repository)
        ).where(
            Deployment.project_id == UUID(project_id)
        ).order_by(desc(Deployment.created_at)).limit(limit)
        
        if status_filter:
            query = query.where(Deployment.status == status_filter.value)
        
        result = await self.db.execute(query)
        return result.scalars().all()
    
    async def update_deployment_status(
        self,
        deployment_id: str,
        status: DeploymentStatus,
        preview_url: Optional[str] = None,
        build_logs: Optional[str] = None,
        deployment_logs: Optional[str] = None,
        error_message: Optional[str] = None
    ) -> Deployment:
        """
        Update deployment status and metadata.
        
        Args:
            deployment_id: Deployment ID
            status: New deployment status
            preview_url: Preview URL (for successful deployments)
            build_logs: Build logs
            deployment_logs: Deployment logs
            error_message: Error message (for failed deployments)
            
        Returns:
            Updated deployment record
        """
        deployment = await self.get_deployment(deployment_id)
        
        # Update status
        deployment.status = status.value
        
        # Update timestamps
        if status in [DeploymentStatus.BUILDING, DeploymentStatus.DEPLOYING] and not deployment.started_at:
            deployment.started_at = datetime.utcnow()
        
        if status in [DeploymentStatus.SUCCESS, DeploymentStatus.FAILED, DeploymentStatus.CANCELLED]:
            deployment.completed_at = datetime.utcnow()
            
            # Calculate durations
            if deployment.started_at:
                total_duration = (deployment.completed_at - deployment.started_at).total_seconds()
                deployment.deployment_duration_seconds = int(total_duration)
        
        # Update metadata
        if preview_url:
            deployment.preview_url = preview_url
        if build_logs:
            deployment.build_logs = build_logs
        if deployment_logs:
            deployment.deployment_logs = deployment_logs
        if error_message:
            deployment.error_message = error_message
        
        await self.db.commit()
        await self.db.refresh(deployment)
        
        logger.info(f"Updated deployment {deployment_id} status to {status.value}")
        
        return deployment
    
    async def cancel_deployment(self, deployment_id: str) -> Deployment:
        """Cancel an active deployment."""
        deployment = await self.get_deployment(deployment_id)
        
        if not deployment.is_active:
            raise ValidationError(f"Deployment {deployment_id} is not active and cannot be cancelled")
        
        deployment.status = DeploymentStatus.CANCELLED.value
        deployment.completed_at = datetime.utcnow()
        
        await self.db.commit()
        await self.db.refresh(deployment)
        
        logger.info(f"Cancelled deployment {deployment_id}")
        
        return deployment
    
    async def trigger_deployment_from_webhook(
        self,
        repository_id: str,
        commit_sha: str,
        branch: str,
        pusher_info: Optional[Dict[str, str]] = None
    ) -> Optional[Deployment]:
        """
        Trigger deployment from webhook event.
        
        Args:
            repository_id: Repository ID
            commit_sha: Git commit SHA
            branch: Git branch name
            pusher_info: Information about who pushed the commit
            
        Returns:
            Created deployment or None if auto-deploy is disabled
        """
        # Get repository
        query = select(Repository).where(Repository.id == UUID(repository_id))
        result = await self.db.execute(query)
        repository = result.scalar_one_or_none()
        
        if not repository:
            raise NotFoundError(f"Repository {repository_id} not found")
        
        # Check if auto-deploy is enabled
        deployment_config = repository.deployment_config or {}
        if not deployment_config.get("auto_deploy", True):
            logger.info(f"Auto-deploy disabled for repository {repository_id}")
            return None
        
        # Check if branch should be deployed
        if branch != repository.branch:
            logger.info(f"Branch {branch} not configured for deployment in repository {repository_id}")
            return None
        
        # Create deployment
        deployment = await self.create_deployment(
            repository_id=repository_id,
            commit_sha=commit_sha,
            branch=branch,
            trigger=DeploymentTrigger.WEBHOOK
        )
        
        logger.info(f"Triggered deployment {deployment.id} from webhook for repository {repository_id}")
        
        return deployment
    
    async def get_deployment_stats(self, project_id: Optional[str] = None) -> Dict[str, Any]:
        """
        Get deployment statistics.
        
        Args:
            project_id: Filter by project ID (optional)
            
        Returns:
            Deployment statistics
        """
        base_query = select(Deployment)
        if project_id:
            base_query = base_query.where(Deployment.project_id == UUID(project_id))
        
        # Total deployments
        total_result = await self.db.execute(select(func.count(Deployment.id)).select_from(base_query.subquery()))
        total_deployments = total_result.scalar() or 0
        
        # Deployments by status
        status_query = select(
            Deployment.status,
            func.count(Deployment.id)
        ).group_by(Deployment.status)
        if project_id:
            status_query = status_query.where(Deployment.project_id == UUID(project_id))
        
        status_result = await self.db.execute(status_query)
        deployments_by_status = dict(status_result.fetchall())
        
        # Deployments by trigger
        trigger_query = select(
            Deployment.trigger,
            func.count(Deployment.id)
        ).group_by(Deployment.trigger)
        if project_id:
            trigger_query = trigger_query.where(Deployment.project_id == UUID(project_id))
        
        trigger_result = await self.db.execute(trigger_query)
        deployments_by_trigger = dict(trigger_result.fetchall())
        
        # Average durations
        duration_query = select(
            func.avg(Deployment.build_duration_seconds),
            func.avg(Deployment.deployment_duration_seconds)
        )
        if project_id:
            duration_query = duration_query.where(Deployment.project_id == UUID(project_id))
        
        duration_result = await self.db.execute(duration_query)
        avg_build_time, avg_deployment_time = duration_result.fetchone() or (None, None)
        
        # Recent deployments
        recent_query = base_query.order_by(desc(Deployment.created_at)).limit(10)
        recent_result = await self.db.execute(recent_query)
        recent_deployments = recent_result.scalars().all()
        
        return {
            "total_deployments": total_deployments,
            "successful_deployments": deployments_by_status.get(DeploymentStatus.SUCCESS.value, 0),
            "failed_deployments": deployments_by_status.get(DeploymentStatus.FAILED.value, 0),
            "active_deployments": (
                deployments_by_status.get(DeploymentStatus.PENDING.value, 0) +
                deployments_by_status.get(DeploymentStatus.BUILDING.value, 0) +
                deployments_by_status.get(DeploymentStatus.DEPLOYING.value, 0)
            ),
            "average_build_time_seconds": float(avg_build_time) if avg_build_time else None,
            "average_deployment_time_seconds": float(avg_deployment_time) if avg_deployment_time else None,
            "deployments_by_status": deployments_by_status,
            "deployments_by_trigger": deployments_by_trigger,
            "recent_deployments": recent_deployments
        }
    
    async def _execute_deployment(self, deployment_id: UUID) -> None:
        """
        Execute deployment pipeline (placeholder for actual implementation).
        
        This method would typically:
        1. Update status to BUILDING
        2. Clone repository
        3. Install dependencies
        4. Run build command
        5. Update status to DEPLOYING
        6. Deploy to hosting platform
        7. Update status to SUCCESS/FAILED
        
        For now, this is a mock implementation.
        """
        try:
            # Simulate deployment process
            await asyncio.sleep(1)  # Simulate build time
            
            # Update to building
            await self.update_deployment_status(
                str(deployment_id),
                DeploymentStatus.BUILDING,
                build_logs="Starting build process...\nInstalling dependencies...\n"
            )
            
            await asyncio.sleep(2)  # Simulate build time
            
            # Update to deploying
            await self.update_deployment_status(
                str(deployment_id),
                DeploymentStatus.DEPLOYING,
                build_logs="Build completed successfully!\nStarting deployment...\n",
                deployment_logs="Deploying to hosting platform...\n"
            )
            
            await asyncio.sleep(1)  # Simulate deployment time
            
            # Complete successfully
            preview_url = f"https://preview-{str(deployment_id)[:8]}.example.com"
            await self.update_deployment_status(
                str(deployment_id),
                DeploymentStatus.SUCCESS,
                preview_url=preview_url,
                deployment_logs="Deployment completed successfully!\nPreview URL: " + preview_url
            )
            
        except Exception as e:
            logger.error(f"Deployment {deployment_id} failed: {str(e)}")
            await self.update_deployment_status(
                str(deployment_id),
                DeploymentStatus.FAILED,
                error_message=str(e)
            )