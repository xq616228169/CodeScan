"""
Configuration module for CodeScan.

Handles loading, parsing, and managing application configuration
including database, AI, and scanner settings.
"""

import os
import json
from dataclasses import dataclass, field, asdict
from typing import Optional


# Default directories
ProjectsDir = "projects"
DataDir = "data"


@dataclass
class DBConfig:
    """Database configuration."""
    host: str = "127.0.0.1"
    port: int = 3306
    user: str = "root"
    password: str = ""
    dbname: str = "codescan"


@dataclass
class AIConfig:
    """AI/LLM configuration."""
    api_key: str = ""
    base_url: str = ""
    model: str = "gemini-3-pro-high"


@dataclass
class ContextCompressionConfig:
    """Context compression configuration."""
    enabled: bool = True
    soft_limit_bytes: int = 90000
    hard_limit_bytes: int = 140000
    summary_window_messages: int = 12
    microcompact_keep_recent: int = 2
    artifact_max_bytes: int = 65536  # 64KB
    compact_min_tail_messages: int = 4
    session_memory_enabled: bool = True


@dataclass
class SessionMemoryConfig:
    """Session memory configuration."""
    enabled: bool = True
    min_growth_bytes: int = 24576  # 24KB
    min_tool_calls: int = 4
    max_update_bytes: int = 32768  # 32KB
    request_timeout_seconds: int = 180
    max_retries: int = 3
    retry_backoff_seconds: int = 2
    failure_cooldown_seconds: int = 300


@dataclass
class ScannerConfig:
    """Scanner configuration."""
    context_soft_limit_bytes: int = 90000
    context_hard_limit_bytes: int = 140000
    context_summary_window_messages: int = 12
    context_compression: ContextCompressionConfig = field(default_factory=ContextCompressionConfig)
    session_memory: SessionMemoryConfig = field(default_factory=SessionMemoryConfig)


@dataclass
class Config:
    """Main application configuration."""
    auth_key: str = ""
    db_config: DBConfig = field(default_factory=DBConfig)
    ai_config: AIConfig = field(default_factory=AIConfig)
    scanner_config: ScannerConfig = field(default_factory=ScannerConfig)


class Settings:
    """Global settings accessible throughout the application."""
    
    def __init__(self):
        self.ai_config: Optional[AIConfig] = None
        self.scanner_config: Optional[ScannerConfig] = None


# Global settings instance
settings = Settings()


def default_scanner_config() -> ScannerConfig:
    """Return default scanner configuration."""
    return ScannerConfig(
        context_soft_limit_bytes=90000,
        context_hard_limit_bytes=140000,
        context_summary_window_messages=12,
        context_compression=ContextCompressionConfig(
            enabled=True,
            soft_limit_bytes=90000,
            hard_limit_bytes=140000,
            summary_window_messages=12,
            microcompact_keep_recent=2,
            artifact_max_bytes=65536,
            compact_min_tail_messages=4,
            session_memory_enabled=True,
        ),
        session_memory=SessionMemoryConfig(
            enabled=True,
            min_growth_bytes=24576,
            min_tool_calls=4,
            max_update_bytes=32768,
            request_timeout_seconds=180,
            max_retries=3,
            retry_backoff_seconds=2,
            failure_cooldown_seconds=300,
        )
    )


def normalize_scanner_config(cfg: ScannerConfig) -> tuple[ScannerConfig, list[str]]:
    """Normalize scanner configuration with defaults and warnings."""
    defaults = default_scanner_config()
    warnings = []
    
    if cfg.context_soft_limit_bytes <= 0:
        cfg.context_soft_limit_bytes = defaults.context_soft_limit_bytes
    if cfg.context_hard_limit_bytes <= 0:
        cfg.context_hard_limit_bytes = defaults.context_hard_limit_bytes
    if cfg.context_summary_window_messages <= 0:
        cfg.context_summary_window_messages = defaults.context_summary_window_messages
    
    if cfg.context_hard_limit_bytes <= cfg.context_soft_limit_bytes:
        cfg.context_hard_limit_bytes = defaults.context_hard_limit_bytes
        if cfg.context_hard_limit_bytes <= cfg.context_soft_limit_bytes:
            cfg.context_hard_limit_bytes = cfg.context_soft_limit_bytes + 1
        warnings.append(
            "scanner_config.context_hard_limit_bytes must be greater than "
            "context_soft_limit_bytes; falling back to a safe hard limit"
        )
    
    # Normalize context compression
    cc = cfg.context_compression
    if cc.soft_limit_bytes <= 0:
        cc.soft_limit_bytes = cfg.context_soft_limit_bytes or defaults.context_compression.soft_limit_bytes
    if cc.hard_limit_bytes <= 0:
        cc.hard_limit_bytes = cfg.context_hard_limit_bytes or defaults.context_compression.hard_limit_bytes
    if cc.summary_window_messages <= 0:
        cc.summary_window_messages = cfg.context_summary_window_messages or defaults.context_compression.summary_window_messages
    
    if cc.hard_limit_bytes <= cc.soft_limit_bytes:
        cc.hard_limit_bytes = defaults.context_compression.hard_limit_bytes
        if cc.hard_limit_bytes <= cc.soft_limit_bytes:
            cc.hard_limit_bytes = cc.soft_limit_bytes + 1
        warnings.append(
            "scanner_config.context_compression.hard_limit_bytes must be greater than "
            "soft_limit_bytes; falling back to a safe hard limit"
        )
    
    if cc.microcompact_keep_recent <= 0:
        cc.microcompact_keep_recent = defaults.context_compression.microcompact_keep_recent
    if cc.artifact_max_bytes <= 0:
        cc.artifact_max_bytes = defaults.context_compression.artifact_max_bytes
    if cc.compact_min_tail_messages <= 0:
        cc.compact_min_tail_messages = defaults.context_compression.compact_min_tail_messages
    
    # Normalize session memory
    sm = cfg.session_memory
    if sm.min_growth_bytes <= 0:
        sm.min_growth_bytes = defaults.session_memory.min_growth_bytes
    if sm.min_tool_calls <= 0:
        sm.min_tool_calls = defaults.session_memory.min_tool_calls
    if sm.max_update_bytes <= 0:
        sm.max_update_bytes = defaults.session_memory.max_update_bytes
    if sm.request_timeout_seconds <= 0:
        sm.request_timeout_seconds = defaults.session_memory.request_timeout_seconds
    if sm.max_retries <= 0:
        sm.max_retries = defaults.session_memory.max_retries
    if sm.retry_backoff_seconds <= 0:
        sm.retry_backoff_seconds = defaults.session_memory.retry_backoff_seconds
    if sm.failure_cooldown_seconds <= 0:
        sm.failure_cooldown_seconds = defaults.session_memory.failure_cooldown_seconds
    
    # Keep deprecated flat fields in sync
    cfg.context_soft_limit_bytes = cfg.context_compression.soft_limit_bytes
    cfg.context_hard_limit_bytes = cfg.context_compression.hard_limit_bytes
    cfg.context_summary_window_messages = cfg.context_compression.summary_window_messages
    
    return cfg, warnings


def load_config(config_path: str) -> Config:
    """Load configuration from JSON file."""
    cfg = Config()
    
    if os.path.exists(config_path):
        try:
            with open(config_path, 'r') as f:
                data = json.load(f)
            
            # Parse nested configs
            if 'db_config' in data:
                cfg.db_config = DBConfig(**data['db_config'])
            if 'ai_config' in data:
                cfg.ai_config = AIConfig(**data['ai_config'])
            if 'scanner_config' in data:
                sc_data = data['scanner_config']
                if 'context_compression' in sc_data:
                    sc_data['context_compression'] = ContextCompressionConfig(**sc_data['context_compression'])
                if 'session_memory' in sc_data:
                    sc_data['session_memory'] = SessionMemoryConfig(**sc_data['session_memory'])
                cfg.scanner_config = ScannerConfig(**sc_data)
            if 'auth_key' in data:
                cfg.auth_key = data['auth_key']
                
        except (json.JSONDecodeError, TypeError) as e:
            print(f"Warning: Failed to parse config file: {e}")
    
    # Apply defaults and normalization
    cfg.scanner_config, warnings = normalize_scanner_config(cfg.scanner_config)
    for warning in warnings:
        print(f"Warning: {warning}")
    
    return cfg


def apply_env_overrides(cfg: Config) -> Config:
    """Override configuration with environment variables."""
    if os.getenv("CODESCAN_AUTH_KEY"):
        cfg.auth_key = os.getenv("CODESCAN_AUTH_KEY")
    if os.getenv("CODESCAN_DB_HOST"):
        cfg.db_config.host = os.getenv("CODESCAN_DB_HOST")
    if os.getenv("CODESCAN_DB_PORT"):
        cfg.db_config.port = int(os.getenv("CODESCAN_DB_PORT"))
    if os.getenv("CODESCAN_DB_USER"):
        cfg.db_config.user = os.getenv("CODESCAN_DB_USER")
    if os.getenv("CODESCAN_DB_PASSWORD"):
        cfg.db_config.password = os.getenv("CODESCAN_DB_PASSWORD")
    if os.getenv("CODESCAN_DB_NAME"):
        cfg.db_config.dbname = os.getenv("CODESCAN_DB_NAME")
    if os.getenv("CODESCAN_AI_API_KEY"):
        cfg.ai_config.api_key = os.getenv("CODESCAN_AI_API_KEY")
    if os.getenv("CODESCAN_AI_BASE_URL"):
        cfg.ai_config.base_url = os.getenv("CODESCAN_AI_BASE_URL")
    if os.getenv("CODESCAN_AI_MODEL"):
        cfg.ai_config.model = os.getenv("CODESCAN_AI_MODEL")
    
    # Set AI model default
    if not cfg.ai_config.model:
        cfg.ai_config.model = "gemini-3-pro-high"
    
    return cfg


def save_config(cfg: Config, config_path: str) -> bool:
    """Save configuration to JSON file."""
    try:
        # Convert to dict for JSON serialization
        data = {
            'auth_key': cfg.auth_key,
            'db_config': asdict(cfg.db_config),
            'ai_config': asdict(cfg.ai_config),
            'scanner_config': asdict(cfg.scanner_config),
        }
        
        with open(config_path, 'w') as f:
            json.dump(data, f, indent=2)
        
        return True
    except Exception as e:
        print(f"Error saving config: {e}")
        return False
