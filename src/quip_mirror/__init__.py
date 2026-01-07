"""
Quip Folder Mirror - A CLI tool for mirroring Quip folders to local filesystem.

This package provides functionality to recursively traverse Quip folder structures
and create mirrored local filesystem structures with documents converted to Word format.
"""

__version__ = "0.1.0"
__author__ = "Amazon Developer"
__description__ = "CLI tool for mirroring Quip folders to local filesystem"

from .models import (
    MirrorConfig,
    QuipItem,
    FolderContents,
    FolderHierarchy,
    DocumentInfo,
    ProcessingSummary,
)

__all__ = [
    "MirrorConfig",
    "QuipItem", 
    "FolderContents",
    "FolderHierarchy",
    "DocumentInfo",
    "ProcessingSummary",
]