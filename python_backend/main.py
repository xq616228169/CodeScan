"""
CodeScan Python Backend - Main Entry Point

A source code security audit platform supporting project upload, 
route analysis, multi-stage vulnerability auditing, result review, 
and HTML report export.
"""

import os
import json
import argparse
from typing import Optional

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings, Config, load_config, apply_env_overrides
from app.database import init_database, ensure_schema
from app.api.routes import register_routes


def create_app(config_path: str = "data/config.json") -> FastAPI:
    """Create and configure the FastAPI application."""
    
    # Load configuration
    cfg = load_config(config_path)
    cfg = apply_env_overrides(cfg)
    
    # Validate auth key
    if not cfg.auth_key:
        print("Error: Auth Key not found. Please run 'python -m cmd.init' first.")
        return None
    
    # Initialize global config for scanner access
    settings.ai_config = cfg.ai_config
    settings.scanner_config = cfg.scanner_config
    
    # Initialize database
    try:
        db_session = init_database(cfg.db_config)
        repairs = ensure_schema(db_session)
        print("Connected to Database")
        if repairs:
            print(f"Schema repairs applied: {repairs}")
    except Exception as e:
        print(f"Error connecting to database: {e}")
        return None
    
    print("=" * 50)
    print(f"Loaded AUTH KEY: {cfg.auth_key}")
    print("=" * 50)
    
    # Create FastAPI app
    app = FastAPI(
        title="CodeScan API",
        description="Source Code Security Audit Platform",
        version="1.0.0"
    )
    
    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["POST", "GET", "OPTIONS", "PUT", "DELETE"],
        allow_headers=["Content-Type", "Authorization"],
    )
    
    # Register routes
    register_routes(app, cfg.auth_key)
    
    return app


def main():
    parser = argparse.ArgumentParser(description="CodeScan Server")
    parser.add_argument(
        "--config", 
        type=str, 
        default="data/config.json",
        help="Path to configuration file"
    )
    parser.add_argument(
        "--host",
        type=str,
        default="0.0.0.0",
        help="Host to bind the server"
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8089,
        help="Port to bind the server"
    )
    
    args = parser.parse_args()
    
    app = create_app(args.config)
    if app is None:
        return
    
    # Import uvicorn here to avoid dependency if config fails
    import uvicorn
    uvicorn.run(app, host=args.host, port=args.port)


if __name__ == "__main__":
    main()
