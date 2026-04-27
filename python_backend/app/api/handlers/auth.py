"""
Authentication handler for CodeScan.

Handles login and token validation.
"""

from fastapi import HTTPException, status
from pydantic import BaseModel


class LoginRequest(BaseModel):
    key: str


def login_handler(auth_key: str):
    """Create login handler with the given auth key."""
    
    async def handler(request: LoginRequest):
        if request.key != auth_key:
            raise HTTPException(
                status_code=status.HTTP_401_UNAUTHORIZED,
                detail="Invalid Key"
            )
        
        return {"token": auth_key}
    
    return handler
