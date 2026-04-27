"""
AI Scanner service for CodeScan.

Core AI-driven security scanning engine supporting multiple audit stages.
This is a simplified stub - full implementation would mirror the Go version.
"""

import json
import asyncio
from typing import Optional, List, Dict, Any

from app.models import Task, TaskStage
from app.database import SessionLocal


# Audit stage definitions
AUDIT_STAGES = [
    {"key": "rce", "label": "RCE Audit", "prompt": "Analyze for Remote Code Execution vulnerabilities"},
    {"key": "injection", "label": "Injection Audit", "prompt": "Analyze for SQL/NoSQL injection vulnerabilities"},
    {"key": "auth", "label": "Auth & Session Audit", "prompt": "Analyze authentication and session management"},
    {"key": "access", "label": "Access Control Audit", "prompt": "Analyze access control mechanisms"},
    {"key": "xss", "label": "XSS Audit", "prompt": "Analyze for Cross-Site Scripting vulnerabilities"},
    {"key": "config", "label": "Config & Component Audit", "prompt": "Analyze configuration and component security"},
    {"key": "fileop", "label": "File Operation Audit", "prompt": "Analyze file operation security"},
    {"key": "logic", "label": "Business Logic Audit", "prompt": "Analyze business logic vulnerabilities"},
]


async def run_ai_scan(task: Task, stage_name: str) -> None:
    """
    Run AI-powered security scan for a specific stage.
    
    This is a placeholder - full implementation would:
    1. Set up conversation with AI
    2. Execute tool calls (read_file, list_files, etc.)
    3. Process AI responses
    4. Handle context compression
    5. Persist results
    """
    db = SessionLocal()
    try:
        # Update task status
        task.status = "running"
        db.commit()
        
        if stage_name == "init":
            # Route analysis stage
            await _run_init_stage(task, db)
        else:
            # Security audit stage
            await _run_audit_stage(task, stage_name, db)
            
    except Exception as e:
        task.status = "failed"
        task.logs.append(f"Error: {str(e)}")
        db.commit()
        raise
    finally:
        db.close()


async def _run_init_stage(task: Task, db) -> None:
    """Run initial route analysis stage."""
    
    # Create or get init stage
    stage = db.query(TaskStage).filter(
        TaskStage.task_id == task.id,
        TaskStage.name == "init"
    ).first()
    
    if not stage:
        stage = TaskStage(
            task_id=task.id,
            name="init",
            status="running",
            logs=[]
        )
        db.add(stage)
        db.commit()
    
    # Placeholder: In real implementation, this would analyze routes
    # using AI to build an inventory of API endpoints
    
    stage.status = "completed"
    stage.result = "[]"  # Empty JSON array placeholder
    stage.output_json = []
    stage.logs.append("Route analysis completed")
    
    task.status = "completed"
    task.logs.append("Initial scan completed")
    
    db.commit()


async def _run_audit_stage(task: Task, stage_name: str, db) -> None:
    """Run a security audit stage."""
    
    # Create or get stage
    stage = db.query(TaskStage).filter(
        TaskStage.task_id == task.id,
        TaskStage.name == stage_name
    ).first()
    
    if not stage:
        stage = TaskStage(
            task_id=task.id,
            name=stage_name,
            status="running",
            logs=[]
        )
        db.add(stage)
        db.commit()
    
    # Placeholder: In real implementation, this would use AI
    # to analyze code for specific vulnerability types
    
    stage.status = "completed"
    stage.result = "[]"  # Empty JSON array placeholder
    stage.output_json = []
    stage.logs.append(f"{stage_name} audit completed")
    
    task.status = "completed"
    task.logs.append(f"{stage_name} audit completed")
    
    db.commit()


async def resume_ai_scan(task: Task) -> str:
    """Resume a paused AI scan. Returns the stage name to resume."""
    
    db = SessionLocal()
    try:
        # Find the last running/paused stage
        stage = db.query(TaskStage).filter(
            TaskStage.task_id == task.id,
            TaskStage.status.in_(["running", "paused"])
        ).order_by(TaskStage.created_at.desc()).first()
        
        if not stage:
            # No stage in progress, start from beginning
            return "init"
        
        stage.status = "running"
        db.commit()
        
        return stage.name
    finally:
        db.close()


async def run_gap_check(task: Task, stage_name: str) -> None:
    """Run gap check to find missed vulnerabilities."""
    
    db = SessionLocal()
    try:
        task.status = "running"
        db.commit()
        
        # Placeholder for gap check logic
        # In real implementation, this would re-analyze with focus
        # on finding missed issues
        
        task.status = "completed"
        task.logs.append(f"Gap check completed for {stage_name}")
        db.commit()
    finally:
        db.close()


async def run_revalidate(task: Task, stage_name: str) -> None:
    """Revalidate findings to confirm/reject them."""
    
    db = SessionLocal()
    try:
        task.status = "running"
        db.commit()
        
        # Placeholder for revalidation logic
        # In real implementation, this would verify each finding
        
        task.status = "completed"
        task.logs.append(f"Revalidation completed for {stage_name}")
        db.commit()
    finally:
        db.close()


async def repair_json(raw_result: str, stage_name: str) -> str:
    """
    Attempt to repair malformed JSON output from AI.
    
    Returns repaired JSON string.
    """
    
    raw_result = raw_result.strip()
    
    # Check if already valid JSON
    try:
        json.loads(raw_result)
        return raw_result
    except json.JSONDecodeError:
        pass
    
    # Try to extract JSON from markdown code blocks
    import re
    pattern = r"```(?:json)?\s*(\[.*?\]|\{.*?\})\s*```"
    matches = re.findall(pattern, raw_result, re.DOTALL)
    
    if matches:
        # Try last match first
        for match in reversed(matches):
            try:
                json.loads(match.strip())
                return match.strip()
            except json.JSONDecodeError:
                continue
    
    # Try adaptive search for JSON arrays
    for i, char in enumerate(raw_result):
        if char == '[':
            candidate = raw_result[i:]
            last_bracket = candidate.rfind(']')
            if last_bracket > 0:
                candidate = candidate[:last_bracket + 1]
                try:
                    json.loads(candidate)
                    return candidate
                except json.JSONDecodeError:
                    continue
    
    # Return original if all attempts fail
    return raw_result
