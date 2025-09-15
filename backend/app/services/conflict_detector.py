"""Minimal conflict detector stub used for demo and to satisfy imports.

This provides lightweight async functions and a simple `conflict_detector`
object with the methods the API expects. The implementations return safe
defaults so the app can import and run during a demo/hackathon.
"""
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import asyncio


@dataclass
class _ConflictDetector:
    conflict_detection_window_minutes: int = 60
    collaboration_window_minutes: int = 240
    file_proximity_threshold: int = 3

    async def analyze_conflict_severity(self, conflict: Any) -> Dict[str, Any]:
        # simple heuristic: severity based on number of users involved
        users = getattr(conflict, "users", []) or conflict.get("users", [])
        severity_map = {0: "low", 1: "low", 2: "medium"}
        sev = severity_map.get(len(users), "high")
        return {"severity": sev, "confidence": 0.6}

    async def suggest_conflict_resolution(self, conflict: Any) -> List[Dict[str, Any]]:
        # return a couple of generic suggestions
        await asyncio.sleep(0)  # keep it async-friendly
        return [
            {"suggestion": "Coordinate via a short call", "priority": "high"},
            {"suggestion": "Assign clear ownership of the resource", "priority": "medium"}
        ]

    async def get_conflict_history(self, project_id: str, days: int = 7) -> List[Dict[str, Any]]:
        await asyncio.sleep(0)
        return []

    def get_stats(self) -> Dict[str, Any]:
        return {"is_running": True, "tracked_projects": 0}


# module-level instance used by API
conflict_detector = _ConflictDetector()


async def detect_project_conflicts(project_id: str) -> List[Dict[str, Any]]:
    # Lightweight placeholder: no real analysis, return empty list
    await asyncio.sleep(0)
    return []


async def find_collaboration_opportunities(project_id: str, user_id: Optional[str] = None) -> List[Dict[str, Any]]:
    await asyncio.sleep(0)
    return []
