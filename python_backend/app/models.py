"""
Database models for CodeScan.

Defines the Task and TaskStage ORM models.
"""

import json
import os
from datetime import datetime
from typing import List, Optional, Dict, Any

from sqlalchemy import Column, String, Integer, DateTime, ForeignKey, Text, JSON
from sqlalchemy.orm import relationship, declarative_base

from app.config import ProjectsDir


Base = declarative_base()


class Task(Base):
    """Task model representing a security audit project."""
    
    __tablename__ = "tasks"
    
    id = Column(String(64), primary_key=True)
    name = Column(String(255), nullable=False)
    remark = Column(Text, default="")
    status = Column(String(50), default="pending")  # pending, running, completed, failed, paused
    created_at = Column(DateTime, default=datetime.utcnow)
    result = Column(Text, default="")
    output_json = Column(JSON, default=dict)
    logs = Column(JSON, default=list)
    
    # Relationship to stages
    stages = relationship(
        "TaskStage",
        back_populates="task",
        cascade="all, delete-orphan",
        order_by="TaskStage.created_at"
    )
    
    # Runtime only, not persisted
    _base_path: Optional[str] = None
    
    def get_base_path(self) -> str:
        """Get the project directory path for this task."""
        if self._base_path:
            return self._base_path
        return os.path.join(ProjectsDir, self.id)
    
    def runtime_root_path(self) -> str:
        """Get the runtime root path for this task."""
        return os.path.join(self.get_base_path(), ".codescan", "runtime")
    
    def stage_runtime_path(self, stage: str) -> str:
        """Get the runtime path for a specific stage."""
        return os.path.join(self.runtime_root_path(), stage)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert task to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "remark": self.remark,
            "status": self.status,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "result": self.result,
            "output_json": self.output_json or {},
            "logs": self.logs or [],
            "stages": [stage.to_dict() for stage in self.stages]
        }


class TaskStage(Base):
    """TaskStage model representing a stage within a security audit task."""
    
    __tablename__ = "task_stages"
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    task_id = Column(String(64), ForeignKey("tasks.id"), nullable=False, index=True)
    name = Column(String(100), nullable=False)  # e.g., "rce", "injection", "auth"
    status = Column(String(50), default="pending")  # pending, running, completed, failed
    result = Column(Text, default="")
    output_json = Column(JSON, default=dict)
    logs = Column(JSON, default=list)
    meta = Column(JSON, default=dict)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    # Relationship to task
    task = relationship("Task", back_populates="stages")
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert stage to dictionary."""
        return {
            "id": self.id,
            "task_id": self.task_id,
            "name": self.name,
            "status": self.status,
            "result": self.result,
            "output_json": self.output_json or {},
            "logs": self.logs or [],
            "meta": self.meta or {},
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "updated_at": self.updated_at.isoformat() if self.updated_at else None
        }
