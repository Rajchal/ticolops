"""Deployment error handling and recovery service."""

import logging
import re
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional, Tuple
from enum import Enum
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, and_, desc
from sqlalchemy.orm import selectinload

from app.models.deployment import Deployment, DeploymentStatus, ProjectType
from app.models.repository import Repository
from app.services.deployment import DeploymentService
from app.core.exceptions import DeploymentError, NotFoundError

logger = logging.getLogger(__name__)


class ErrorCategory(str, Enum):
    """Categories of deployment errors."""
    BUILD_FAILURE = "build_failure"
    DEPENDENCY_ERROR = "dependency_error"
    CONFIGURATION_ERROR = "configuration_error"
    RESOURCE_LIMIT = "resource_limit"
    NETWORK_ERROR = "network_error"
    PLATFORM_ERROR = "platform_error"
    TIMEOUT_ERROR = "timeout_error"
    PERMISSION_ERROR = "permission_error"
    UNKNOWN_ERROR = "unknown_error"


class ErrorSeverity(str, Enum):
    """Severity levels for deployment errors."""
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"


class DeploymentErrorAnalyzer:
    """Analyzes deployment errors and provides troubleshooting suggestions."""
    
    # Error patterns and their categories
    ERROR_PATTERNS = {
        ErrorCategory.BUILD_FAILURE: [
            r"npm ERR!.*build.*failed",
            r"Error: Build failed",
            r"webpack.*failed to compile",
            r"TypeScript error",
            r"Compilation error",
            r"SyntaxError.*Unexpected token",
            r"ModuleNotFoundError",
            r"ImportError.*No module named"
        ],
        ErrorCategory.DEPENDENCY_ERROR: [
            r"npm ERR!.*Cannot resolve dependency",
            r"pip.*No matching distribution found",
            r"Package.*not found",
            r"npm ERR!.*ERESOLVE",
            r"requirements.*not satisfied",
            r"ModuleNotFoundError.*No module named",
            r"npm ERR!.*peer dep missing"
        ],
        ErrorCategory.CONFIGURATION_ERROR: [
            r"Invalid configuration",
            r"Missing environment variable",
            r"Configuration file.*not found",
            r"Invalid.*config",
            r"Missing required field",
            r"Unsupported.*version",
            r"Invalid build command"
        ],
        ErrorCategory.RESOURCE_LIMIT: [
            r"Out of memory",
            r"Disk space.*full",
            r"Resource limit exceeded",
            r"Memory limit exceeded",
            r"Build timeout",
            r"Process killed.*memory",
            r"ENOMEM.*not enough memory"
        ],
        ErrorCategory.NETWORK_ERROR: [
            r"Network.*timeout",
            r"Connection.*refused",
            r"DNS.*resolution failed",
            r"Unable to connect",
            r"Request timeout",
            r"Network is unreachable",
            r"SSL.*certificate.*error"
        ],
        ErrorCategory.PLATFORM_ERROR: [
            r"Platform.*error",
            r"Deployment platform.*unavailable",
            r"API.*rate limit",
            r"Service temporarily unavailable",
            r"Internal server error.*platform",
            r"Hosting platform.*error"
        ],
        ErrorCategory.TIMEOUT_ERROR: [
            r"Timeout.*exceeded",
            r"Build.*timed out",
            r"Deployment.*timeout",
            r"Process.*timeout",
            r"Operation.*timed out"
        ],
        ErrorCategory.PERMISSION_ERROR: [
            r"Permission denied",
            r"Access.*forbidden",
            r"Unauthorized",
            r"Authentication.*failed",
            r"Invalid.*credentials",
            r"Insufficient permissions"
        ]
    }
    
    # Troubleshooting suggestions for each error category
    TROUBLESHOOTING_SUGGESTIONS = {
        ErrorCategory.BUILD_FAILURE: [
            "Check your build command and ensure it's correct for your project type",
            "Verify all source files are valid and free of syntax errors",
            "Ensure all imports and dependencies are correctly specified",
            "Check for TypeScript errors if using TypeScript",
            "Review build logs for specific error messages",
            "Try building locally to reproduce the issue"
        ],
        ErrorCategory.DEPENDENCY_ERROR: [
            "Check your package.json or requirements.txt for correct dependency versions",
            "Ensure all dependencies are available in the package registry",
            "Try updating dependency versions to compatible ones",
            "Check for peer dependency conflicts",
            "Clear dependency cache and reinstall",
            "Verify package names are spelled correctly"
        ],
        ErrorCategory.CONFIGURATION_ERROR: [
            "Review your build configuration settings",
            "Ensure all required environment variables are set",
            "Check configuration file syntax and format",
            "Verify build command is appropriate for your project type",
            "Ensure output directory is correctly specified",
            "Check for missing configuration files"
        ],
        ErrorCategory.RESOURCE_LIMIT: [
            "Optimize your build process to use less memory",
            "Reduce the size of your project or dependencies",
            "Consider splitting large builds into smaller chunks",
            "Check for memory leaks in your build process",
            "Increase resource limits if possible",
            "Remove unnecessary files from your build"
        ],
        ErrorCategory.NETWORK_ERROR: [
            "Check your internet connection",
            "Verify external service URLs are correct and accessible",
            "Check for firewall or proxy issues",
            "Try again later if services are temporarily unavailable",
            "Verify SSL certificates are valid",
            "Check DNS resolution for external services"
        ],
        ErrorCategory.PLATFORM_ERROR: [
            "Check the hosting platform status page",
            "Verify your API tokens and credentials are valid",
            "Try deploying again after a few minutes",
            "Check platform-specific limits and quotas",
            "Contact platform support if the issue persists",
            "Consider using an alternative deployment platform"
        ],
        ErrorCategory.TIMEOUT_ERROR: [
            "Optimize your build process to complete faster",
            "Reduce the complexity of your build",
            "Check for infinite loops or hanging processes",
            "Increase timeout limits if configurable",
            "Split large operations into smaller steps",
            "Remove unnecessary build steps"
        ],
        ErrorCategory.PERMISSION_ERROR: [
            "Check your API tokens and credentials",
            "Verify you have necessary permissions for the operation",
            "Ensure repository access permissions are correct",
            "Check hosting platform account permissions",
            "Regenerate API tokens if they may be expired",
            "Contact administrator for permission issues"
        ],
        ErrorCategory.UNKNOWN_ERROR: [
            "Review the complete error logs for more details",
            "Try deploying again to see if it's a temporary issue",
            "Check the platform status and documentation",
            "Contact support with the full error details",
            "Try a different deployment approach if available",
            "Check for recent changes that might have caused the issue"
        ]
    }
    
    def analyze_error(self, error_logs: str, deployment: Deployment) -> Dict[str, Any]:
        """
        Analyze deployment error and provide troubleshooting suggestions.
        
        Args:
            error_logs: Combined error logs from build and deployment
            deployment: Deployment instance
            
        Returns:
            Error analysis with category, severity, and suggestions
        """
        if not error_logs:
            return {
                "category": ErrorCategory.UNKNOWN_ERROR,
                "severity": ErrorSeverity.MEDIUM,
                "patterns_matched": [],
                "suggestions": self.TROUBLESHOOTING_SUGGESTIONS[ErrorCategory.UNKNOWN_ERROR],
                "quick_fixes": [],
                "related_docs": []
            }
        
        # Analyze error patterns
        category_scores = {}
        matched_patterns = []
        
        for category, patterns in self.ERROR_PATTERNS.items():
            score = 0
            category_matches = []
            
            for pattern in patterns:
                matches = re.findall(pattern, error_logs, re.IGNORECASE | re.MULTILINE)
                if matches:
                    score += len(matches)
                    category_matches.extend(matches)
            
            if score > 0:
                category_scores[category] = score
                matched_patterns.extend(category_matches)
        
        # Determine primary error category
        if category_scores:
            primary_category = max(category_scores.keys(), key=lambda k: category_scores[k])
        else:
            primary_category = ErrorCategory.UNKNOWN_ERROR
        
        # Determine severity based on category and deployment context
        severity = self._determine_severity(primary_category, deployment, error_logs)
        
        # Get suggestions and quick fixes
        suggestions = self.TROUBLESHOOTING_SUGGESTIONS.get(
            primary_category, 
            self.TROUBLESHOOTING_SUGGESTIONS[ErrorCategory.UNKNOWN_ERROR]
        )
        
        quick_fixes = self._get_quick_fixes(primary_category, deployment)
        related_docs = self._get_related_documentation(primary_category, deployment)
        
        return {
            "category": primary_category,
            "severity": severity,
            "patterns_matched": matched_patterns[:5],  # Limit to first 5 matches
            "suggestions": suggestions,
            "quick_fixes": quick_fixes,
            "related_docs": related_docs,
            "analysis_confidence": min(category_scores.get(primary_category, 0) / 10, 1.0)
        }
    
    def _determine_severity(self, category: ErrorCategory, deployment: Deployment, error_logs: str) -> ErrorSeverity:
        """Determine error severity based on category and context."""
        # Critical errors that prevent any deployment
        if category in [ErrorCategory.PLATFORM_ERROR, ErrorCategory.PERMISSION_ERROR]:
            return ErrorSeverity.CRITICAL
        
        # High severity for resource and timeout issues
        if category in [ErrorCategory.RESOURCE_LIMIT, ErrorCategory.TIMEOUT_ERROR]:
            return ErrorSeverity.HIGH
        
        # Medium severity for build and dependency issues
        if category in [ErrorCategory.BUILD_FAILURE, ErrorCategory.DEPENDENCY_ERROR]:
            return ErrorSeverity.MEDIUM
        
        # Check for specific high-severity patterns
        high_severity_patterns = [
            r"fatal error",
            r"critical.*error",
            r"system.*failure",
            r"cannot recover"
        ]
        
        for pattern in high_severity_patterns:
            if re.search(pattern, error_logs, re.IGNORECASE):
                return ErrorSeverity.HIGH
        
        return ErrorSeverity.MEDIUM
    
    def _get_quick_fixes(self, category: ErrorCategory, deployment: Deployment) -> List[Dict[str, str]]:
        """Get quick fix suggestions for the error category."""
        project_type = ProjectType(deployment.project_type)
        
        quick_fixes = []
        
        if category == ErrorCategory.BUILD_FAILURE:
            if project_type in [ProjectType.REACT, ProjectType.NEXTJS, ProjectType.VUE]:
                quick_fixes.extend([
                    {
                        "title": "Clear npm cache",
                        "command": "npm cache clean --force",
                        "description": "Clear npm cache and try rebuilding"
                    },
                    {
                        "title": "Update build command",
                        "command": "npm run build",
                        "description": "Ensure build command is correct"
                    }
                ])
            elif project_type in [ProjectType.PYTHON, ProjectType.DJANGO, ProjectType.FLASK]:
                quick_fixes.extend([
                    {
                        "title": "Update requirements",
                        "command": "pip install -r requirements.txt --upgrade",
                        "description": "Update Python dependencies"
                    }
                ])
        
        elif category == ErrorCategory.DEPENDENCY_ERROR:
            if project_type in [ProjectType.REACT, ProjectType.NEXTJS, ProjectType.VUE]:
                quick_fixes.append({
                    "title": "Install missing dependencies",
                    "command": "npm install",
                    "description": "Install all required dependencies"
                })
        
        elif category == ErrorCategory.CONFIGURATION_ERROR:
            quick_fixes.append({
                "title": "Check environment variables",
                "command": "Review deployment configuration",
                "description": "Ensure all required environment variables are set"
            })
        
        return quick_fixes
    
    def _get_related_documentation(self, category: ErrorCategory, deployment: Deployment) -> List[Dict[str, str]]:
        """Get related documentation links for the error category."""
        project_type = ProjectType(deployment.project_type)
        
        docs = []
        
        # Project-specific documentation
        if project_type == ProjectType.REACT:
            docs.append({
                "title": "React Build Troubleshooting",
                "url": "https://create-react-app.dev/docs/troubleshooting/",
                "description": "Official React build troubleshooting guide"
            })
        elif project_type == ProjectType.NEXTJS:
            docs.append({
                "title": "Next.js Deployment Guide",
                "url": "https://nextjs.org/docs/deployment",
                "description": "Next.js deployment best practices"
            })
        
        # Category-specific documentation
        if category == ErrorCategory.BUILD_FAILURE:
            docs.append({
                "title": "Build Troubleshooting Guide",
                "url": "/docs/troubleshooting/build-errors",
                "description": "Common build errors and solutions"
            })
        elif category == ErrorCategory.DEPENDENCY_ERROR:
            docs.append({
                "title": "Dependency Management",
                "url": "/docs/troubleshooting/dependencies",
                "description": "Managing project dependencies"
            })
        
        return docs


class DeploymentRecoveryService:
    """Service for handling deployment recovery and rollback operations."""
    
    def __init__(self, db: AsyncSession):
        self.db = db
        self.deployment_service = DeploymentService(db)
        self.error_analyzer = DeploymentErrorAnalyzer()
    
    async def handle_deployment_failure(self, deployment_id: str) -> Dict[str, Any]:
        """
        Handle deployment failure with error analysis and recovery suggestions.
        
        Args:
            deployment_id: Failed deployment ID
            
        Returns:
            Recovery analysis and suggestions
        """
        # Get failed deployment
        deployment = await self.deployment_service.get_deployment(deployment_id)
        
        if deployment.status != DeploymentStatus.FAILED.value:
            raise DeploymentError(f"Deployment {deployment_id} is not in failed state")
        
        # Combine error logs
        error_logs = ""
        if deployment.build_logs:
            error_logs += deployment.build_logs + "\n"
        if deployment.deployment_logs:
            error_logs += deployment.deployment_logs + "\n"
        if deployment.error_message:
            error_logs += deployment.error_message + "\n"
        
        # Analyze error
        error_analysis = self.error_analyzer.analyze_error(error_logs, deployment)
        
        # Get recovery options
        recovery_options = await self._get_recovery_options(deployment)
        
        # Check for similar past failures
        similar_failures = await self._find_similar_failures(deployment)
        
        # Generate recovery plan
        recovery_plan = self._generate_recovery_plan(error_analysis, deployment)
        
        return {
            "deployment_id": deployment_id,
            "error_analysis": error_analysis,
            "recovery_options": recovery_options,
            "recovery_plan": recovery_plan,
            "similar_failures": similar_failures,
            "auto_retry_recommended": self._should_auto_retry(error_analysis),
            "rollback_available": len(recovery_options.get("rollback_targets", [])) > 0
        }
    
    async def auto_retry_deployment(self, deployment_id: str) -> Optional[Deployment]:
        """
        Automatically retry a failed deployment if conditions are met.
        
        Args:
            deployment_id: Failed deployment ID
            
        Returns:
            New deployment if retry was initiated, None otherwise
        """
        deployment = await self.deployment_service.get_deployment(deployment_id)
        
        # Check if auto-retry is appropriate
        error_logs = (deployment.build_logs or "") + (deployment.deployment_logs or "") + (deployment.error_message or "")
        error_analysis = self.error_analyzer.analyze_error(error_logs, deployment)
        
        if not self._should_auto_retry(error_analysis):
            return None
        
        # Check retry count to prevent infinite loops
        retry_count = await self._get_retry_count(deployment)
        if retry_count >= 3:  # Maximum 3 retries
            logger.warning(f"Maximum retry count reached for deployment {deployment_id}")
            return None
        
        # Create new deployment with same parameters
        new_deployment = await self.deployment_service.create_deployment(
            repository_id=str(deployment.repository_id),
            commit_sha=deployment.commit_sha,
            branch=deployment.branch,
            trigger=deployment.trigger,
            build_config=deployment.build_config,
            environment_variables=deployment.environment_variables
        )
        
        logger.info(f"Auto-retry initiated: new deployment {new_deployment.id} for failed deployment {deployment_id}")
        return new_deployment
    
    async def rollback_deployment(self, deployment_id: str, target_deployment_id: Optional[str] = None) -> Deployment:
        """
        Rollback to a previous successful deployment.
        
        Args:
            deployment_id: Current failed deployment ID
            target_deployment_id: Specific deployment to rollback to (optional)
            
        Returns:
            New deployment created for rollback
        """
        current_deployment = await self.deployment_service.get_deployment(deployment_id)
        
        # Find target deployment for rollback
        if target_deployment_id:
            target_deployment = await self.deployment_service.get_deployment(target_deployment_id)
        else:
            # Find last successful deployment for the same repository
            target_deployment = await self._find_last_successful_deployment(current_deployment.repository_id)
        
        if not target_deployment:
            raise DeploymentError("No suitable deployment found for rollback")
        
        # Create rollback deployment
        rollback_deployment = await self.deployment_service.create_deployment(
            repository_id=str(current_deployment.repository_id),
            commit_sha=target_deployment.commit_sha,
            branch=target_deployment.branch,
            trigger="rollback",
            build_config=target_deployment.build_config,
            environment_variables=target_deployment.environment_variables
        )
        
        logger.info(f"Rollback initiated: deployment {rollback_deployment.id} rolling back to {target_deployment.id}")
        return rollback_deployment
    
    async def get_deployment_health_score(self, repository_id: str) -> Dict[str, Any]:
        """
        Calculate deployment health score for a repository.
        
        Args:
            repository_id: Repository ID
            
        Returns:
            Health score and metrics
        """
        # Get recent deployments (last 30 days)
        from datetime import timedelta
        cutoff_date = datetime.utcnow() - timedelta(days=30)
        
        query = select(Deployment).where(
            and_(
                Deployment.repository_id == repository_id,
                Deployment.created_at >= cutoff_date
            )
        ).order_by(desc(Deployment.created_at))
        
        result = await self.db.execute(query)
        recent_deployments = result.scalars().all()
        
        if not recent_deployments:
            return {
                "health_score": 100,
                "total_deployments": 0,
                "success_rate": 0,
                "avg_duration": 0,
                "failure_trends": [],
                "recommendations": []
            }
        
        # Calculate metrics
        total_deployments = len(recent_deployments)
        successful_deployments = sum(1 for d in recent_deployments if d.status == DeploymentStatus.SUCCESS.value)
        success_rate = (successful_deployments / total_deployments) * 100
        
        # Calculate average duration for successful deployments
        successful_durations = [
            d.deployment_duration_seconds for d in recent_deployments 
            if d.status == DeploymentStatus.SUCCESS.value and d.deployment_duration_seconds
        ]
        avg_duration = sum(successful_durations) / len(successful_durations) if successful_durations else 0
        
        # Analyze failure trends
        failed_deployments = [d for d in recent_deployments if d.status == DeploymentStatus.FAILED.value]
        failure_trends = self._analyze_failure_trends(failed_deployments)
        
        # Calculate health score (0-100)
        health_score = self._calculate_health_score(success_rate, avg_duration, failure_trends)
        
        # Generate recommendations
        recommendations = self._generate_health_recommendations(success_rate, failure_trends)
        
        return {
            "health_score": health_score,
            "total_deployments": total_deployments,
            "success_rate": round(success_rate, 2),
            "avg_duration": round(avg_duration, 2),
            "failure_trends": failure_trends,
            "recommendations": recommendations
        }
    
    async def _get_recovery_options(self, deployment: Deployment) -> Dict[str, Any]:
        """Get available recovery options for a failed deployment."""
        options = {
            "retry": True,
            "rollback_targets": [],
            "configuration_fixes": [],
            "alternative_approaches": []
        }
        
        # Find rollback targets (last 5 successful deployments)
        query = select(Deployment).where(
            and_(
                Deployment.repository_id == deployment.repository_id,
                Deployment.status == DeploymentStatus.SUCCESS.value,
                Deployment.created_at < deployment.created_at
            )
        ).order_by(desc(Deployment.created_at)).limit(5)
        
        result = await self.db.execute(query)
        successful_deployments = result.scalars().all()
        
        for dep in successful_deployments:
            options["rollback_targets"].append({
                "deployment_id": str(dep.id),
                "commit_sha": dep.commit_sha[:8],
                "created_at": dep.created_at.isoformat(),
                "branch": dep.branch
            })
        
        return options
    
    async def _find_similar_failures(self, deployment: Deployment) -> List[Dict[str, Any]]:
        """Find similar past failures for learning purposes."""
        # Get recent failed deployments for the same repository
        query = select(Deployment).where(
            and_(
                Deployment.repository_id == deployment.repository_id,
                Deployment.status == DeploymentStatus.FAILED.value,
                Deployment.id != deployment.id
            )
        ).order_by(desc(Deployment.created_at)).limit(5)
        
        result = await self.db.execute(query)
        similar_failures = result.scalars().all()
        
        failures_info = []
        for failure in similar_failures:
            failures_info.append({
                "deployment_id": str(failure.id),
                "commit_sha": failure.commit_sha[:8],
                "created_at": failure.created_at.isoformat(),
                "error_message": failure.error_message[:100] if failure.error_message else None
            })
        
        return failures_info
    
    def _generate_recovery_plan(self, error_analysis: Dict[str, Any], deployment: Deployment) -> List[Dict[str, str]]:
        """Generate step-by-step recovery plan."""
        plan = []
        category = error_analysis["category"]
        severity = error_analysis["severity"]
        
        # Immediate actions based on severity
        if severity == ErrorSeverity.CRITICAL:
            plan.append({
                "step": 1,
                "action": "Immediate Investigation",
                "description": "Critical error requires immediate attention. Check platform status and credentials."
            })
        
        # Category-specific recovery steps
        if category == ErrorCategory.BUILD_FAILURE:
            plan.extend([
                {
                    "step": len(plan) + 1,
                    "action": "Review Build Logs",
                    "description": "Examine build logs for specific error messages and failed commands."
                },
                {
                    "step": len(plan) + 1,
                    "action": "Test Locally",
                    "description": "Try building the project locally to reproduce and fix the issue."
                },
                {
                    "step": len(plan) + 1,
                    "action": "Fix and Retry",
                    "description": "Apply fixes and trigger a new deployment."
                }
            ])
        
        elif category == ErrorCategory.DEPENDENCY_ERROR:
            plan.extend([
                {
                    "step": len(plan) + 1,
                    "action": "Check Dependencies",
                    "description": "Review package.json or requirements.txt for version conflicts."
                },
                {
                    "step": len(plan) + 1,
                    "action": "Update Dependencies",
                    "description": "Update to compatible versions and test locally."
                }
            ])
        
        # Always add rollback option if available
        plan.append({
            "step": len(plan) + 1,
            "action": "Consider Rollback",
            "description": "If fixes are complex, consider rolling back to the last successful deployment."
        })
        
        return plan
    
    def _should_auto_retry(self, error_analysis: Dict[str, Any]) -> bool:
        """Determine if deployment should be automatically retried."""
        category = error_analysis["category"]
        severity = error_analysis["severity"]
        
        # Don't auto-retry critical errors or configuration issues
        if severity == ErrorSeverity.CRITICAL:
            return False
        
        if category in [ErrorCategory.CONFIGURATION_ERROR, ErrorCategory.PERMISSION_ERROR]:
            return False
        
        # Auto-retry for transient issues
        if category in [ErrorCategory.NETWORK_ERROR, ErrorCategory.PLATFORM_ERROR, ErrorCategory.TIMEOUT_ERROR]:
            return True
        
        return False
    
    async def _get_retry_count(self, deployment: Deployment) -> int:
        """Get the number of retries for this deployment's commit."""
        query = select(Deployment).where(
            and_(
                Deployment.repository_id == deployment.repository_id,
                Deployment.commit_sha == deployment.commit_sha,
                Deployment.created_at <= deployment.created_at
            )
        )
        
        result = await self.db.execute(query)
        deployments = result.scalars().all()
        return len(deployments) - 1  # Subtract 1 for the original deployment
    
    async def _find_last_successful_deployment(self, repository_id: str) -> Optional[Deployment]:
        """Find the last successful deployment for a repository."""
        query = select(Deployment).where(
            and_(
                Deployment.repository_id == repository_id,
                Deployment.status == DeploymentStatus.SUCCESS.value
            )
        ).order_by(desc(Deployment.created_at)).limit(1)
        
        result = await self.db.execute(query)
        return result.scalar_one_or_none()
    
    def _analyze_failure_trends(self, failed_deployments: List[Deployment]) -> List[Dict[str, Any]]:
        """Analyze trends in deployment failures."""
        trends = []
        
        if not failed_deployments:
            return trends
        
        # Group failures by error category
        category_counts = {}
        for deployment in failed_deployments:
            if deployment.error_message:
                error_analysis = self.error_analyzer.analyze_error(deployment.error_message, deployment)
                category = error_analysis["category"]
                category_counts[category] = category_counts.get(category, 0) + 1
        
        # Convert to trend data
        for category, count in category_counts.items():
            trends.append({
                "category": category,
                "count": count,
                "percentage": round((count / len(failed_deployments)) * 100, 2)
            })
        
        return sorted(trends, key=lambda x: x["count"], reverse=True)
    
    def _calculate_health_score(self, success_rate: float, avg_duration: float, failure_trends: List[Dict[str, Any]]) -> int:
        """Calculate overall deployment health score (0-100)."""
        # Base score from success rate
        score = success_rate
        
        # Penalty for slow deployments (over 5 minutes)
        if avg_duration > 300:  # 5 minutes
            score -= min(20, (avg_duration - 300) / 60)  # Up to 20 point penalty
        
        # Penalty for recurring failure patterns
        if failure_trends:
            top_failure_rate = failure_trends[0]["percentage"]
            if top_failure_rate > 50:  # More than 50% of failures are the same type
                score -= 10
        
        return max(0, min(100, int(score)))
    
    def _generate_health_recommendations(self, success_rate: float, failure_trends: List[Dict[str, Any]]) -> List[str]:
        """Generate recommendations to improve deployment health."""
        recommendations = []
        
        if success_rate < 80:
            recommendations.append("Success rate is below 80%. Review common failure patterns and fix underlying issues.")
        
        if failure_trends:
            top_failure = failure_trends[0]
            if top_failure["percentage"] > 30:
                recommendations.append(f"Most common failure is {top_failure['category']}. Focus on resolving this issue type.")
        
        if success_rate < 50:
            recommendations.append("Consider implementing pre-deployment validation to catch issues early.")
        
        if not recommendations:
            recommendations.append("Deployment health is good. Continue monitoring for any emerging patterns.")
        
        return recommendations