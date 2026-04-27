"""
Task handlers for CodeScan.

Handles task creation, upload, deletion, and stage execution.
"""

import os
import uuid
import json
import shutil
from datetime import datetime
from typing import Optional

from fastapi import HTTPException, UploadFile, Form
from sqlalchemy.orm import Session, joinedload

from app.database import SessionLocal
from app.models import Task, TaskStage
from app.config import ProjectsDir
from app.utils.zip_utils import unzip_file, MAX_FILE_SIZE
from app.services.scanner import run_ai_scan, resume_ai_scan, run_gap_check, run_revalidate, repair_json
from app.services.summary import parse_route_count, parse_json_array, is_supported_stage_name


async def upload_handler(file: UploadFile, name: Optional[str] = None, remark: Optional[str] = None):
    """Handle project file upload and create a new task."""
    
    # Validate file size
    file.file.seek(0, 2)  # Seek to end
    file_size = file.tell()
    file.file.seek(0)  # Reset to beginning
    
    if file_size > MAX_FILE_SIZE:
        raise HTTPException(status_code=400, detail="File exceeds 30MB limit")
    
    # Generate task ID
    task_id = uuid.uuid4().hex
    project_path = os.path.join(ProjectsDir, task_id)
    zip_path = os.path.join(ProjectsDir, f"{task_id}.zip")
    
    try:
        # Save uploaded zip file
        with open(zip_path, "wb") as buffer:
            shutil.copyfileobj(file.file, buffer)
        
        # Unzip the file
        unzip_file(zip_path, project_path)
        
        # Remove zip file after extraction
        os.remove(zip_path)
        
        # Create task record
        db = SessionLocal()
        try:
            task = Task(
                id=task_id,
                name=name or "",
                remark=remark or "",
                status="pending",
                result="",
                output_json={},
                logs=[],
                _base_path=project_path
            )
            
            db.add(task)
            db.commit()
            db.refresh(task)
            
            # Start initial scan in background
            import asyncio
            asyncio.create_task(run_ai_scan_wrapper(task_id, "init"))
            
            return task.to_dict()
        finally:
            db.close()
            
    except Exception as e:
        # Cleanup on failure
        if os.path.exists(zip_path):
            os.remove(zip_path)
        if os.path.exists(project_path):
            shutil.rmtree(project_path)
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def run_ai_scan_wrapper(task_id: str, stage_name: str):
    """Wrapper to run AI scan in background."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task._base_path = task.get_base_path()
            await run_ai_scan(task, stage_name)
    finally:
        db.close()


async def delete_task_handler(task_id: str):
    """Delete a task and its associated files."""
    db = SessionLocal()
    try:
        task = db.query(Task).options(joinedload(Task.stages)).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status == "running":
            raise HTTPException(
                status_code=409, 
                detail="Task is running. Pause it before deleting."
            )
        
        # Delete stages first
        db.query(TaskStage).filter(TaskStage.task_id == task_id).delete()
        db.delete(task)
        db.commit()
        
        # Remove task files
        task_path = task.get_base_path()
        if os.path.exists(task_path):
            try:
                shutil.rmtree(task_path)
            except Exception as e:
                print(f"Warning: Failed to remove task data for {task_id}: {e}")
        
        return {"status": "deleted"}
    finally:
        db.close()


async def pause_task_handler(task_id: str):
    """Pause a running task."""
    db = SessionLocal()
    try:
        task = db.query(Task).options(joinedload(Task.stages)).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task.status = "paused"
        
        # Pause all running stages
        for stage in task.stages:
            if stage.status == "running":
                stage.status = "paused"
        
        db.commit()
        db.refresh(task)
        
        return task.to_dict()
    finally:
        db.close()


async def resume_task_handler(task_id: str):
    """Resume a paused task."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        task._base_path = task.get_base_path()
        
        try:
            stage = await resume_ai_scan(task)
        except Exception as e:
            raise HTTPException(status_code=409, detail=str(e))
        
        task.status = "running"
        db.commit()
        db.refresh(task)
        
        return {"status": "resumed", "stage": stage, "task": task.to_dict()}
    finally:
        db.close()


async def run_stage_handler(task_id: str, stage_name: str):
    """Run a specific audit stage."""
    
    if not is_supported_stage_name(stage_name):
        raise HTTPException(status_code=400, detail="Unsupported stage")
    
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status == "running":
            raise HTTPException(status_code=409, detail="Task is already running")
        
        task._base_path = task.get_base_path()
        task.status = "running"
        db.commit()
        
        # Start scan in background
        import asyncio
        asyncio.create_task(run_ai_scan_wrapper(task_id, stage_name))
        
        return {"status": "stage started", "stage": stage_name}
    finally:
        db.close()


async def gap_check_stage_handler(task_id: str, stage_name: str):
    """Run gap check for a completed stage."""
    
    if not is_supported_stage_name(stage_name):
        raise HTTPException(status_code=400, detail="Unsupported stage")
    
    db = SessionLocal()
    try:
        task = db.query(Task).options(joinedload(Task.stages)).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status == "running":
            raise HTTPException(status_code=409, detail="Task is already running")
        
        # Validate stage readiness
        if stage_name == "init":
            findings = parse_json_array(task.output_json, task.result)
            if not findings:
                raise HTTPException(
                    status_code=409,
                    detail="Route inventory is not available as structured JSON yet. Run the scan or repair JSON first."
                )
        else:
            stage = db.query(TaskStage).filter(
                TaskStage.task_id == task_id,
                TaskStage.name == stage_name
            ).first()
            
            if not stage:
                raise HTTPException(status_code=404, detail="Stage not found")
            
            if stage.status != "completed":
                raise HTTPException(
                    status_code=409,
                    detail="Stage must complete once before gap check can run"
                )
            
            findings = parse_json_array(stage.output_json, stage.result)
            if not findings:
                raise HTTPException(
                    status_code=409,
                    detail="Stage output is not structured JSON yet. Repair JSON first."
                )
        
        task._base_path = task.get_base_path()
        task.status = "running"
        db.commit()
        
        # Start gap check in background
        import asyncio
        asyncio.create_task(run_gap_check_wrapper(task_id, stage_name))
        
        return {"status": "gap check started", "stage": stage_name}
    finally:
        db.close()


async def run_gap_check_wrapper(task_id: str, stage_name: str):
    """Wrapper to run gap check in background."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task._base_path = task.get_base_path()
            await run_gap_check(task, stage_name)
    finally:
        db.close()


async def revalidate_stage_handler(task_id: str, stage_name: str):
    """Revalidate findings for a completed stage."""
    
    if stage_name == "init":
        raise HTTPException(status_code=400, detail="Route inventory does not support revalidation")
    
    if not is_supported_stage_name(stage_name):
        raise HTTPException(status_code=400, detail="Unsupported stage")
    
    db = SessionLocal()
    try:
        task = db.query(Task).options(joinedload(Task.stages)).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        if task.status == "running":
            raise HTTPException(status_code=409, detail="Task is already running")
        
        stage = db.query(TaskStage).filter(
            TaskStage.task_id == task_id,
            TaskStage.name == stage_name
        ).first()
        
        if not stage:
            raise HTTPException(status_code=404, detail="Stage not found")
        
        if stage.status != "completed":
            raise HTTPException(
                status_code=409,
                detail="Stage must complete once before revalidation can run"
            )
        
        findings = parse_json_array(stage.output_json, stage.result)
        if not findings:
            raise HTTPException(
                status_code=409,
                detail="Stage output is not structured JSON yet. Repair JSON first."
            )
        
        if len(findings) == 0:
            raise HTTPException(status_code=409, detail="No findings are available to revalidate")
        
        task._base_path = task.get_base_path()
        task.status = "running"
        db.commit()
        
        # Start revalidation in background
        import asyncio
        asyncio.create_task(run_revalidate_wrapper(task_id, stage_name))
        
        return {"status": "revalidation started", "stage": stage_name}
    finally:
        db.close()


async def run_revalidate_wrapper(task_id: str, stage_name: str):
    """Wrapper to run revalidation in background."""
    db = SessionLocal()
    try:
        task = db.query(Task).filter(Task.id == task_id).first()
        if task:
            task._base_path = task.get_base_path()
            await run_revalidate(task, stage_name)
    finally:
        db.close()


async def repair_json_handler(task_id: str, stage: Optional[str] = None):
    """Repair JSON output for a task or stage."""
    
    db = SessionLocal()
    try:
        task = db.query(Task).options(joinedload(Task.stages)).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        raw_result = ""
        target = None
        
        if not stage or stage == "init":
            raw_result = task.result or ""
            target = task
        else:
            stage_obj = db.query(TaskStage).filter(
                TaskStage.task_id == task_id,
                TaskStage.name == stage
            ).first()
            
            if not stage_obj:
                raise HTTPException(status_code=404, detail="Stage not found")
            
            raw_result = stage_obj.result or ""
            target = stage_obj
        
        # Try to extract from logs if no result
        if not raw_result:
            logs = target.logs or []
            for log_entry in reversed(logs):
                idx = log_entry.find("] AI: ")
                if idx != -1:
                    raw_result = log_entry[idx + 6:]
                    break
        
        if not raw_result:
            raise HTTPException(status_code=400, detail="No result to repair. Please re-run the scan.")
        
        # Repair JSON
        repaired = await repair_json(raw_result, stage or "init")
        
        if target == task:
            task.output_json = json.loads(repaired)
        else:
            target.output_json = json.loads(repaired)
        
        db.commit()
        
        return {"status": "repaired", "output_json": json.loads(repaired)}
    finally:
        db.close()
