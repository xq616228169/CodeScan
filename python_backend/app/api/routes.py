"""
API Routes registration for CodeScan.

Registers all API endpoints with the FastAPI application.
"""

from fastapi import FastAPI, Depends, HTTPException, status
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from typing import Optional

from app.api.handlers.auth import login_handler
from app.api.handlers.task import (
    get_tasks_handler,
    get_task_detail_handler,
    upload_handler,
    delete_task_handler,
    pause_task_handler,
    resume_task_handler,
    run_stage_handler,
    gap_check_stage_handler,
    revalidate_stage_handler,
    repair_json_handler,
)
from app.api.handlers.stats import get_stats_handler
from app.api.handlers.report import export_task_report_handler


# Security scheme
security = HTTPBearer(auto_error=False)


def create_auth_dependency(auth_key: str):
    """Create authentication dependency with the given auth key."""
    
    async def auth_dependency(
        credentials: Optional[HTTPAuthorizationCredentials] = Depends(security)
    ):
        if credentials is None:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Missing authorization header"
            )
        
        token = credentials.credentials
        if token != auth_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Auth Key"
            )
        
        return True
    
    return auth_dependency


def register_routes(app: FastAPI, auth_key: str):
    """Register all API routes with the FastAPI application."""
    
    # Create auth dependency
    require_auth = create_auth_dependency(auth_key)
    
    # Public endpoints
    app.post("/api/login")(login_handler(auth_key))
    
    # Protected endpoints
    @app.get("/api/stats", dependencies=[Depends(require_auth)])
    async def stats_endpoint():
        return await get_stats_handler()
    
    @app.get("/api/tasks", dependencies=[Depends(require_auth)])
    async def tasks_endpoint():
        return await get_tasks_handler()
    
    @app.get("/api/tasks/{task_id}", dependencies=[Depends(require_auth)])
    async def task_detail_endpoint(task_id: str):
        return await get_task_detail_handler(task_id)
    
    @app.get("/api/tasks/{task_id}/report", dependencies=[Depends(require_auth)])
    async def report_endpoint(task_id: str):
        return await export_task_report_handler(task_id)
    
    @app.post("/api/tasks", dependencies=[Depends(require_auth)])
    async def upload_endpoint(file, name: str = None, remark: str = None):
        return await upload_handler(file, name, remark)
    
    @app.delete("/api/tasks/{task_id}", dependencies=[Depends(require_auth)])
    async def delete_endpoint(task_id: str):
        return await delete_task_handler(task_id)
    
    @app.post("/api/tasks/{task_id}/pause", dependencies=[Depends(require_auth)])
    async def pause_endpoint(task_id: str):
        return await pause_task_handler(task_id)
    
    @app.post("/api/tasks/{task_id}/resume", dependencies=[Depends(require_auth)])
    async def resume_endpoint(task_id: str):
        return await resume_task_handler(task_id)
    
    @app.post("/api/tasks/{task_id}/stage/{stage_name}", dependencies=[Depends(require_auth)])
    async def run_stage_endpoint(task_id: str, stage_name: str):
        return await run_stage_handler(task_id, stage_name)
    
    @app.post("/api/tasks/{task_id}/stage/{stage_name}/gap-check", dependencies=[Depends(require_auth)])
    async def gap_check_endpoint(task_id: str, stage_name: str):
        return await gap_check_stage_handler(task_id, stage_name)
    
    @app.post("/api/tasks/{task_id}/stage/{stage_name}/revalidate", dependencies=[Depends(require_auth)])
    async def revalidate_endpoint(task_id: str, stage_name: str):
        return await revalidate_stage_handler(task_id, stage_name)
    
    @app.post("/api/tasks/{task_id}/repair", dependencies=[Depends(require_auth)])
    async def repair_endpoint(task_id: str, stage: Optional[str] = None):
        return await repair_json_handler(task_id, stage)
