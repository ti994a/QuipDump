"""
Data models for the Quip Folder Mirror application.

This module contains all the data classes and models used throughout the application
for configuration, Quip items, folder hierarchies, and processing results.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional
from pathlib import Path
import re


@dataclass
class MirrorConfig:
    """Configuration for the mirroring operation."""
    
    quip_folder_url: str
    target_path: str
    access_token: Optional[str] = None  # Will be resolved during execution
    overwrite_existing: bool = True
    
    def __post_init__(self):
        """Validate configuration after initialization."""
        self.validate()
    
    def validate(self) -> None:
        """Validate the configuration parameters."""
        if not self.quip_folder_url:
            raise ValueError("Quip folder URL is required")
        
        if not self.quip_folder_url.startswith("https://quip-amazon.com/"):
            raise ValueError("Quip URL must start with 'https://quip-amazon.com/'")
        
        if not self.target_path:
            raise ValueError("Target path is required")
        
        # Validate target path is writable
        target = Path(self.target_path)
        if target.exists() and not target.is_dir():
            raise ValueError(f"Target path exists but is not a directory: {self.target_path}")


@dataclass
class QuipItem:
    """Represents a Quip folder or document."""
    
    id: str
    name: str
    type: str  # 'folder' or 'document'
    url: str
    
    def __post_init__(self):
        """Validate item after initialization."""
        if self.type not in ('folder', 'document'):
            raise ValueError(f"Invalid type: {self.type}. Must be 'folder' or 'document'")
        
        if not self.id:
            raise ValueError("Item ID is required")
        
        if not self.name:
            raise ValueError("Item name is required")


@dataclass
class FolderContents:
    """Contents of a Quip folder."""
    
    folders: List[QuipItem] = field(default_factory=list)
    documents: List[QuipItem] = field(default_factory=list)
    folder_name: Optional[str] = None  # Name of the folder itself
    
    @property
    def total_items(self) -> int:
        """Total number of items in the folder."""
        return len(self.folders) + len(self.documents)
    
    def is_empty(self) -> bool:
        """Check if the folder is empty."""
        return self.total_items == 0


@dataclass
class FolderHierarchy:
    """Hierarchical representation of a Quip folder structure."""
    
    root_folder: QuipItem
    subfolders: Dict[str, 'FolderHierarchy'] = field(default_factory=dict)
    documents: List[QuipItem] = field(default_factory=list)
    
    def get_all_documents(self) -> List['DocumentInfo']:
        """Get all documents in this hierarchy with path information."""
        all_docs = []
        
        # Add documents in this folder
        for doc in self.documents:
            doc_info = DocumentInfo(
                item=doc,
                relative_path=self.root_folder.name,
                local_file_path=""  # Will be set later
            )
            all_docs.append(doc_info)
        
        # Recursively add documents from subfolders
        for subfolder_name, subfolder_hierarchy in self.subfolders.items():
            subfolder_docs = subfolder_hierarchy.get_all_documents()
            for doc_info in subfolder_docs:
                # Update the relative path to include this folder
                doc_info.relative_path = f"{self.root_folder.name}/{doc_info.relative_path}"
                all_docs.append(doc_info)
        
        return all_docs
    
    @property
    def total_folders(self) -> int:
        """Total number of folders in this hierarchy."""
        count = 1  # This folder
        for subfolder in self.subfolders.values():
            count += subfolder.total_folders
        return count
    
    @property
    def total_documents(self) -> int:
        """Total number of documents in this hierarchy."""
        count = len(self.documents)
        for subfolder in self.subfolders.values():
            count += subfolder.total_documents
        return count


@dataclass
class DocumentInfo:
    """Information about a document with path details."""
    
    item: QuipItem
    relative_path: str
    local_file_path: str
    
    def __post_init__(self):
        """Validate document info after initialization."""
        if self.item.type != 'document':
            raise ValueError("DocumentInfo can only be created for document items")


@dataclass
class DocumentContent:
    """Content of a Quip document."""
    
    title: str
    content: str
    format: str  # 'html', 'markdown', etc.
    
    def sanitize_title_for_filename(self) -> str:
        """Sanitize the title for use as a filename."""
        # Replace invalid filename characters
        sanitized = re.sub(r'[<>:"/\\|?*]', '-', self.title)
        # Replace forward slashes specifically (common in Quip titles)
        sanitized = sanitized.replace('/', '-')
        # Remove multiple consecutive dashes
        sanitized = re.sub(r'-+', '-', sanitized)
        # Strip leading/trailing dashes and whitespace
        sanitized = sanitized.strip('- ')
        # Ensure it's not empty
        if not sanitized:
            sanitized = "untitled"
        return sanitized


@dataclass
class ProcessingSummary:
    """Summary of the mirroring operation results."""
    
    total_folders: int = 0
    total_documents: int = 0
    successful_conversions: int = 0
    failed_conversions: int = 0
    errors: List[str] = field(default_factory=list)
    
    @property
    def success_rate(self) -> float:
        """Calculate the success rate as a percentage."""
        if self.total_documents == 0:
            return 100.0
        return (self.successful_conversions / self.total_documents) * 100.0
    
    def add_error(self, error: str) -> None:
        """Add an error to the summary."""
        self.errors.append(error)
    
    def increment_success(self) -> None:
        """Increment the successful conversions counter."""
        self.successful_conversions += 1
    
    def increment_failure(self) -> None:
        """Increment the failed conversions counter."""
        self.failed_conversions += 1
    
    def __str__(self) -> str:
        """String representation of the processing summary."""
        return (
            f"Processing Summary:\n"
            f"  Total folders: {self.total_folders}\n"
            f"  Total documents: {self.total_documents}\n"
            f"  Successful conversions: {self.successful_conversions}\n"
            f"  Failed conversions: {self.failed_conversions}\n"
            f"  Success rate: {self.success_rate:.1f}%\n"
            f"  Errors: {len(self.errors)}"
        )