#!/usr/bin/env python3
"""
Initialization script for CodeScan.

Creates directories, generates configuration, and initializes database.
"""

import os
import sys
import json
import uuid

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from app.config import Config, DBConfig, AIConfig, ScannerConfig, save_config, normalize_scanner_config
from app.database import init_database, ensure_schema, build_connection_string
from sqlalchemy import create_engine, text


DATA_DIR = "data"
PROJECTS_DIR = "projects"
CONFIG_FILE = "data/config.json"


def main():
    print("Initializing CodeScan System...")
    
    # 1. Create directories
    dirs = [DATA_DIR, PROJECTS_DIR]
    for dir_name in dirs:
        os.makedirs(dir_name, exist_ok=True)
        print(f"Verified directory: {dir_name}")
    
    # 2. Load or create config
    cfg = Config()
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, 'r') as f:
                data = json.load(f)
            
            if 'auth_key' in data:
                cfg.auth_key = data['auth_key']
            if 'db_config' in data:
                cfg.db_config = DBConfig(**data['db_config'])
            if 'ai_config' in data:
                cfg.ai_config = AIConfig(**data['ai_config'])
                
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Failed to parse existing config: {e}")
    
    # 3. Setup Auth Key
    if not cfg.auth_key:
        print("Generating new Auth Key...")
        cfg.auth_key = uuid.uuid4().hex
    else:
        print("Existing Auth Key found.")
    
    # 4. Setup Database Config
    if not cfg.db_config.host:
        cfg.db_config.host = "127.0.0.1"
    if cfg.db_config.port == 0:
        cfg.db_config.port = 3306
    if not cfg.db_config.user:
        cfg.db_config.user = "root"
    if not cfg.db_config.password:
        cfg.db_config.password = os.getenv("CODESCAN_DB_PASSWORD", "")
    if not cfg.db_config.dbname:
        cfg.db_config.dbname = "codescan"
    
    # Normalize scanner config
    cfg.scanner_config, warnings = normalize_scanner_config(cfg.scanner_config)
    for warning in warnings:
        print(f"Warning: {warning}")
    
    # Save config
    if save_config(cfg, CONFIG_FILE):
        print("Configuration saved.")
    else:
        print("Failed to save configuration.")
        return
    
    # 5. Initialize Database
    print("Initializing Database...")
    
    try:
        # Connect without database first
        root_conn_str = build_connection_string(cfg.db_config, with_database=False)
        root_engine = create_engine(root_conn_str)
        
        with root_engine.connect() as conn:
            # Check if database exists
            result = conn.execute(
                text("SELECT COUNT(*) FROM information_schema.SCHEMATA WHERE SCHEMA_NAME = :dbname"),
                {"dbname": cfg.db_config.dbname}
            )
            existed = result.scalar() > 0
            
            # Create database
            conn.execute(
                text(f"CREATE DATABASE IF NOT EXISTS `{cfg.db_config.dbname}` CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci")
            )
            conn.commit()
            
            if existed:
                print(f"Database '{cfg.db_config.dbname}' already existed.")
            else:
                print(f"Database '{cfg.db_config.dbname}' created.")
        
        root_engine.dispose()
        
        # Connect to database and migrate schema
        db_session = init_database(cfg.db_config)
        repairs = ensure_schema(db_session)
        print("Database schema migrated successfully.")
        
        if not repairs:
            print("Schema check: no repairs were needed.")
        else:
            print("Schema check: repaired columns:")
            for repair in repairs:
                print(f" - {repair}")
        
        db_session.close()
        
    except Exception as e:
        print(f"Error connecting to MySQL: {e}")
        print("Please check if MySQL is running and credentials are correct.")
        return
    
    print("=" * 50)
    print(f"AUTH KEY: {cfg.auth_key}")
    print(f"DB Host: {cfg.db_config.host}:{cfg.db_config.port}")
    print(f"DB Name: {cfg.db_config.dbname}")
    print("=" * 50)
    print("Initialization Complete.")


if __name__ == "__main__":
    main()
