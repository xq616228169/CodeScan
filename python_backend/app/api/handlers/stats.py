"""
Stats handler for CodeScan.

Provides dashboard statistics and aggregated task data.
"""

from sqlalchemy.orm import Session, joinedload
from app.database import SessionLocal
from app.models import Task, TaskStage
from app.services.summary import build_stats, build_task_list


async def get_stats_handler():
    """Get dashboard statistics."""
    db = SessionLocal()
    try:
        tasks = db.query(Task).options(
            joinedload(Task.stages)
        ).order_by(Task.created_at.desc()).all()
        
        return build_stats(tasks)
    finally:
        db.close()


async def get_tasks_handler():
    """Get list of tasks with summaries."""
    db = SessionLocal()
    try:
        tasks = db.query(Task).options(
            joinedload(Task.stages)
        ).order_by(Task.created_at.desc()).all()
        
        return build_task_list(tasks)
    finally:
        db.close()


async def get_task_detail_handler(task_id: str):
    """Get detailed information about a specific task."""
    db = SessionLocal()
    try:
        task = db.query(Task).options(
            joinedload(Task.stages)
        ).filter(Task.id == task_id).first()
        
        if not task:
            from fastapi import HTTPException
            raise HTTPException(status_code=404, detail="Task not found")
        
        return task.to_dict()
    finally:
        db.close()
