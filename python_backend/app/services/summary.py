"""
Summary service for CodeScan.

Provides statistics aggregation and task list building.
"""

from datetime import datetime
from typing import List, Dict, Any, Optional, Tuple
import json
import re

from app.models import Task, TaskStage


# Stage definitions
KNOWN_STAGES = [
    {"key": "rce", "label": "RCE Audit"},
    {"key": "injection", "label": "Injection Audit"},
    {"key": "auth", "label": "Auth & Session Audit"},
    {"key": "access", "label": "Access Control Audit"},
    {"key": "xss", "label": "XSS Audit"},
    {"key": "config", "label": "Config & Component Audit"},
    {"key": "fileop", "label": "File Operation Audit"},
    {"key": "logic", "label": "Business Logic Audit"},
]

STAGE_LABEL_BY_KEY = {s["key"]: s["label"] for s in KNOWN_STAGES}

SEVERITY_RANK = {
    "CRITICAL": 5,
    "HIGH": 4,
    "MEDIUM": 3,
    "LOW": 2,
    "INFO": 1,
    "NONE": 0,
    "UNKNOWN": 0,
}


def is_supported_stage_name(stage_name: str) -> bool:
    """Check if stage name is supported."""
    return stage_name == "init" or stage_name in STAGE_LABEL_BY_KEY


def parse_route_count(output_json: dict, result: str) -> int:
    """Parse route count from task output."""
    if output_json and isinstance(output_json, list):
        return len(output_json)
    
    # Try to extract from result string
    try:
        data = json.loads(result)
        if isinstance(data, list):
            return len(data)
    except (json.JSONDecodeError, TypeError):
        pass
    
    return 0


def parse_json_array(json_data: dict, result: str) -> Optional[List]:
    """Parse JSON array from output."""
    if json_data and isinstance(json_data, list):
        return json_data
    
    try:
        data = json.loads(result)
        if isinstance(data, list):
            return data
    except (json.JSONDecodeError, TypeError):
        pass
    
    return None


def build_stats(tasks: List[Task]) -> Dict[str, Any]:
    """Build dashboard statistics from tasks."""
    stats = {
        "projects": len(tasks),
        "interfaces": 0,
        "vulns": 0,
        "completed_audits": 0,
        "status_breakdown": {
            "pending": 0,
            "running": 0,
            "paused": 0,
            "completed": 0,
            "failed": 0,
        },
        "severity_breakdown": [],
        "stage_breakdown": [],
    }
    
    severity_counts = {}
    stage_counts = {s["key"]: 0 for s in KNOWN_STAGES}
    
    for task in tasks:
        # Count interfaces
        stats["interfaces"] += parse_route_count(task.output_json, task.result)
        
        # Status breakdown
        status = task.status.lower() if task.status else "pending"
        if status in stats["status_breakdown"]:
            stats["status_breakdown"][status] += 1
        
        # Process stages
        for stage in task.stages:
            if stage.status == "completed":
                stats["completed_audits"] += 1
                if stage.name in stage_counts:
                    stage_counts[stage.name] += 1
            
            # Parse findings for severity
            findings = parse_json_array(stage.output_json, stage.result)
            if findings:
                for finding in findings:
                    if isinstance(finding, dict):
                        severity = finding.get("severity", "UNKNOWN").upper()
                        severity_counts[severity] = severity_counts.get(severity, 0) + 1
                        stats["vulns"] += 1
    
    # Build severity breakdown
    severity_order = ["CRITICAL", "HIGH", "MEDIUM", "LOW", "INFO"]
    stats["severity_breakdown"] = [
        {"label": sev, "count": severity_counts.get(sev, 0)}
        for sev in severity_order
        if severity_counts.get(sev, 0) > 0
    ]
    
    # Build stage breakdown
    stats["stage_breakdown"] = [
        {"key": s["key"], "label": s["label"], "count": stage_counts[s["key"]]}
        for s in KNOWN_STAGES
        if stage_counts[s["key"]] > 0
    ]
    
    return stats


def build_task_list(tasks: List[Task]) -> List[Dict[str, Any]]:
    """Build task list with summaries."""
    result = []
    
    for task in tasks:
        route_count = parse_route_count(task.output_json, task.result)
        
        # Count findings and determine highest severity
        finding_count = 0
        highest_severity = "NONE"
        completed_stages = 0
        
        for stage in task.stages:
            if stage.status == "completed":
                completed_stages += 1
            
            findings = parse_json_array(stage.output_json, stage.result)
            if findings:
                finding_count += len(findings)
                for finding in findings:
                    if isinstance(finding, dict):
                        severity = finding.get("severity", "UNKNOWN").upper()
                        if SEVERITY_RANK.get(severity, 0) > SEVERITY_RANK.get(highest_severity, 0):
                            highest_severity = severity
        
        result.append({
            "id": task.id,
            "name": task.name,
            "remark": task.remark or "",
            "status": task.status,
            "created_at": task.created_at.isoformat() if task.created_at else None,
            "route_count": route_count,
            "finding_count": finding_count,
            "completed_stage_count": completed_stages,
            "total_stage_count": len(KNOWN_STAGES),
            "highest_severity": highest_severity,
        })
    
    return result
