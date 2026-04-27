"""
Report handler for CodeScan.

Handles HTML report generation and export.
"""

from fastapi import HTTPException, Response
from app.database import SessionLocal
from app.models import Task
from app.services.report import generate_html


async def export_task_report_handler(task_id: str):
    """Generate and export HTML report for a task."""
    
    db = SessionLocal()
    try:
        task = db.query(Task).options(
            db.query(Task.stages)
        ).filter(Task.id == task_id).first()
        
        if not task:
            raise HTTPException(status_code=404, detail="Task not found")
        
        from datetime import datetime
        html, file_name = await generate_html(task, datetime.utcnow())
        
        if not html:
            raise HTTPException(
                status_code=400, 
                detail="No completed audit stages available for export"
            )
        
        fallback_name = file_name.strip() if file_name else f"codescan-report-{task_id}.html"
        
        return Response(
            content=html,
            media_type="text/html; charset=utf-8",
            headers={
                "Content-Disposition": f'attachment; filename="{fallback_name}"'
            }
        )
    finally:
        db.close()
