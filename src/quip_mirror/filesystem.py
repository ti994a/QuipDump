"""
File system operations for creating local directory structures.

This module provides the FileSystemManager class that handles creating
local directory structures and managing file operations.
"""

import os
import logging
from pathlib import Path
from typing import List, Optional, Tuple
import shutil

from .models import FolderHierarchy, DocumentInfo, QuipItem


logger = logging.getLogger(__name__)


class FileSystemError(Exception):
    """Exception raised for file system operations."""
    pass


class FileSystemManager:
    """Manages local file system operations for mirroring Quip folders."""
    
    def __init__(self, base_path: str, overwrite_existing: bool = True):
        """
        Initialize the file system manager.
        
        Args:
            base_path: Base directory path for mirroring
            overwrite_existing: Whether to overwrite existing files
        """
        self.base_path = Path(base_path)
        self.overwrite_existing = overwrite_existing
        
        # Ensure base path exists
        self.base_path.mkdir(parents=True, exist_ok=True)
        
        logger.debug(f"FileSystemManager initialized with base path: {self.base_path}")
    
    def create_directory_structure(self, hierarchy: FolderHierarchy, current_path: Optional[Path] = None) -> bool:
        """
        Create local directory structure matching the Quip hierarchy.
        
        Args:
            hierarchy: FolderHierarchy to replicate
            current_path: Current path in the directory structure
            
        Returns:
            True if successful, False otherwise
            
        Raises:
            FileSystemError: If directory creation fails
        """
        if current_path is None:
            current_path = self.base_path
        
        try:
            # Create directory for this folder
            folder_name = self.sanitize_folder_name(hierarchy.root_folder.name)
            folder_path = current_path / folder_name
            
            logger.debug(f"Creating directory: {folder_path}")
            folder_path.mkdir(parents=True, exist_ok=True)
            
            # Recursively create subdirectories
            for subfolder_hierarchy in hierarchy.subfolders.values():
                self.create_directory_structure(subfolder_hierarchy, folder_path)
            
            logger.debug(f"Successfully created directory structure for: {folder_name}")
            return True
            
        except OSError as e:
            raise FileSystemError(f"Failed to create directory structure: {str(e)}") from e
        except Exception as e:
            raise FileSystemError(f"Unexpected error creating directories: {str(e)}") from e
    
    def ensure_directory_exists(self, path: str) -> bool:
        """
        Ensure a directory exists, creating it if necessary.
        
        Args:
            path: Directory path to ensure exists
            
        Returns:
            True if directory exists or was created successfully
            
        Raises:
            FileSystemError: If directory cannot be created
        """
        try:
            dir_path = Path(path)
            dir_path.mkdir(parents=True, exist_ok=True)
            logger.debug(f"Ensured directory exists: {dir_path}")
            return True
            
        except OSError as e:
            raise FileSystemError(f"Cannot create directory {path}: {str(e)}") from e
    
    def get_document_path(self, doc_info: DocumentInfo, base_path: Optional[str] = None) -> str:
        """
        Get the local file path for a document.
        
        Args:
            doc_info: DocumentInfo object
            base_path: Optional base path override
            
        Returns:
            Full local file path for the document
        """
        if base_path is None:
            base_path = str(self.base_path)
        
        # Sanitize the relative path components
        path_parts = doc_info.relative_path.split('/')
        sanitized_parts = [self.sanitize_folder_name(part) for part in path_parts if part]
        
        # Create the directory path
        dir_path = Path(base_path)
        for part in sanitized_parts:
            dir_path = dir_path / part
        
        # Create the file path with sanitized filename
        filename = self.sanitize_filename(doc_info.item.name)
        if not filename.endswith('.docx'):
            filename += '.docx'
        
        file_path = dir_path / filename
        return str(file_path)
    
    def file_exists(self, path: str) -> bool:
        """Check if a file exists."""
        return Path(path).exists()
    
    def get_file_size(self, path: str) -> int:
        """Get the size of a file in bytes."""
        try:
            return Path(path).stat().st_size
        except OSError:
            return 0
    
    def backup_existing_file(self, file_path: str) -> Optional[str]:
        """
        Create a backup of an existing file.
        
        Args:
            file_path: Path to the file to backup
            
        Returns:
            Path to the backup file, or None if backup failed
        """
        if not self.file_exists(file_path):
            return None
        
        try:
            backup_path = f"{file_path}.backup"
            counter = 1
            
            # Find a unique backup filename
            while Path(backup_path).exists():
                backup_path = f"{file_path}.backup.{counter}"
                counter += 1
            
            shutil.copy2(file_path, backup_path)
            logger.debug(f"Created backup: {backup_path}")
            return backup_path
            
        except OSError as e:
            logger.warning(f"Failed to create backup for {file_path}: {str(e)}")
            return None
    
    def handle_file_conflict(self, file_path: str) -> Tuple[bool, str]:
        """
        Handle file conflicts based on overwrite settings.
        
        Args:
            file_path: Path to the conflicting file
            
        Returns:
            Tuple of (should_proceed, message)
        """
        if not self.file_exists(file_path):
            return True, "No conflict"
        
        if self.overwrite_existing:
            # Create backup if possible
            backup_path = self.backup_existing_file(file_path)
            if backup_path:
                return True, f"File will be overwritten (backup created: {backup_path})"
            else:
                return True, "File will be overwritten (backup failed)"
        else:
            return False, f"File already exists and overwrite is disabled: {file_path}"
    
    def sanitize_filename(self, filename: str) -> str:
        """
        Sanitize a filename for file system compatibility.
        
        Args:
            filename: Original filename
            
        Returns:
            Sanitized filename safe for file systems
        """
        # Remove or replace invalid characters
        invalid_chars = '<>:"/\\|?*'
        sanitized = filename
        
        for char in invalid_chars:
            sanitized = sanitized.replace(char, '-')
        
        # Replace forward slashes specifically (common in Quip titles)
        sanitized = sanitized.replace('/', '-')
        
        # Remove control characters
        sanitized = ''.join(char for char in sanitized if ord(char) >= 32)
        
        # Remove multiple consecutive dashes
        while '--' in sanitized:
            sanitized = sanitized.replace('--', '-')
        
        # Strip leading/trailing dashes and whitespace
        sanitized = sanitized.strip('- ')
        
        # Ensure it's not empty
        if not sanitized:
            sanitized = "untitled"
        
        # Limit length to avoid file system issues
        if len(sanitized) > 200:
            sanitized = sanitized[:200].rstrip('- ')
        
        return sanitized
    
    def sanitize_folder_name(self, folder_name: str) -> str:
        """
        Sanitize a folder name for file system compatibility.
        
        Args:
            folder_name: Original folder name
            
        Returns:
            Sanitized folder name safe for file systems
        """
        # Use the same sanitization as filenames
        return self.sanitize_filename(folder_name)
    
    def validate_path_length(self, path: str) -> bool:
        """
        Validate that a path is not too long for the file system.
        
        Args:
            path: Path to validate
            
        Returns:
            True if path length is acceptable
        """
        # Most file systems have a limit around 260 characters for full paths
        # We'll use a conservative limit of 250
        return len(path) <= 250
    
    def get_available_space(self, path: str) -> int:
        """
        Get available disk space in bytes.
        
        Args:
            path: Path to check (directory)
            
        Returns:
            Available space in bytes
        """
        try:
            stat = shutil.disk_usage(path)
            return stat.free
        except OSError:
            return 0
    
    def cleanup_empty_directories(self, base_path: Optional[str] = None) -> int:
        """
        Remove empty directories from the mirrored structure.
        
        Args:
            base_path: Base path to clean up (defaults to self.base_path)
            
        Returns:
            Number of directories removed
        """
        if base_path is None:
            base_path = str(self.base_path)
        
        removed_count = 0
        base_path_obj = Path(base_path)
        
        try:
            # Walk the directory tree bottom-up
            for root, dirs, files in os.walk(base_path, topdown=False):
                root_path = Path(root)
                
                # Skip the base directory itself
                if root_path == base_path_obj:
                    continue
                
                # Check if directory is empty
                try:
                    if not any(root_path.iterdir()):
                        root_path.rmdir()
                        removed_count += 1
                        logger.debug(f"Removed empty directory: {root_path}")
                except OSError as e:
                    logger.debug(f"Could not remove directory {root_path}: {str(e)}")
            
            return removed_count
            
        except Exception as e:
            logger.warning(f"Error during cleanup: {str(e)}")
            return removed_count
    
    def get_directory_stats(self, path: Optional[str] = None) -> dict:
        """
        Get statistics about the mirrored directory structure.
        
        Args:
            path: Path to analyze (defaults to self.base_path)
            
        Returns:
            Dictionary with directory statistics
        """
        if path is None:
            path = str(self.base_path)
        
        stats = {
            "total_directories": 0,
            "total_files": 0,
            "total_size": 0,
            "docx_files": 0,
            "empty_directories": 0
        }
        
        try:
            for root, dirs, files in os.walk(path):
                stats["total_directories"] += len(dirs)
                stats["total_files"] += len(files)
                
                # Check if current directory is empty
                if not dirs and not files:
                    stats["empty_directories"] += 1
                
                for file in files:
                    file_path = Path(root) / file
                    try:
                        file_size = file_path.stat().st_size
                        stats["total_size"] += file_size
                        
                        if file.endswith('.docx'):
                            stats["docx_files"] += 1
                    except OSError:
                        continue
            
        except Exception as e:
            logger.warning(f"Error calculating directory stats: {str(e)}")
        
        return stats