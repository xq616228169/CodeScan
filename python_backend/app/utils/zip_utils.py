"""
ZIP file utilities for CodeScan.

Handles ZIP file extraction with security checks.
"""

import os
import zipfile
from typing import Optional

MAX_FILE_SIZE = 30 * 1024 * 1024  # 30MB


def unzip_file(src: str, dest: str) -> None:
    """
    Extract a ZIP file to destination directory.
    
    Args:
        src: Path to the ZIP file
        dest: Destination directory path
        
    Raises:
        Exception: If extraction fails or illegal paths detected
    """
    with zipfile.ZipFile(src, 'r') as zip_ref:
        for member in zip_ref.namelist():
            # Security check: prevent path traversal
            dest_path = os.path.normpath(os.path.join(dest, member))
            if not dest_path.startswith(os.path.normpath(dest)):
                raise Exception(f"Illegal file path: {member}")
            
            if member.endswith('/'):
                # Directory
                os.makedirs(dest_path, exist_ok=True)
            else:
                # File - ensure parent directory exists
                os.makedirs(os.path.dirname(dest_path), exist_ok=True)
                
                # Extract file
                with zip_ref.open(member) as source:
                    with open(dest_path, 'wb') as target:
                        target.write(source.read())
