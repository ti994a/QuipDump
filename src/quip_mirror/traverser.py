"""
Folder traversal logic for Quip folder structures.

This module provides the FolderTraverser class that recursively discovers
and maps Quip folder hierarchies using the API client.
"""

import logging
from typing import Dict, List, Set, Optional
from .models import QuipItem, FolderContents, FolderHierarchy, DocumentInfo
from .quip_client import QuipAPIClient, QuipAPIError


logger = logging.getLogger(__name__)


class TraversalError(Exception):
    """Exception raised during folder traversal."""
    pass


class FolderTraverser:
    """Handles recursive traversal of Quip folder structures."""
    
    def __init__(self, client: QuipAPIClient, max_depth: int = 50):
        """
        Initialize the folder traverser.
        
        Args:
            client: QuipAPIClient instance for API calls
            max_depth: Maximum recursion depth to prevent infinite loops
        """
        self.client = client
        self.max_depth = max_depth
        self._visited_folders: Set[str] = set()
    
    def traverse(self, root_folder_id: str) -> FolderHierarchy:
        """
        Traverse a Quip folder structure recursively.
        
        Args:
            root_folder_id: ID of the root folder to start traversal
            
        Returns:
            FolderHierarchy representing the complete folder structure
            
        Raises:
            TraversalError: If traversal fails
        """
        logger.info(f"Starting traversal of folder: {root_folder_id}")
        self._visited_folders.clear()
        
        try:
            hierarchy = self._traverse_recursive(root_folder_id, depth=0)
            logger.info(f"Completed traversal of '{hierarchy.root_folder.name}' - "
                       f"found {hierarchy.total_folders} folders and {hierarchy.total_documents} documents")
            return hierarchy
        except QuipAPIError as e:
            raise TraversalError(f"API error during traversal: {str(e)}") from e
        except Exception as e:
            raise TraversalError(f"Unexpected error during traversal: {str(e)}") from e
    
    def _traverse_recursive(self, folder_id: str, depth: int = 0) -> FolderHierarchy:
        """
        Recursively traverse a folder and its subfolders.
        
        Args:
            folder_id: ID of the folder to traverse
            depth: Current recursion depth
            
        Returns:
            FolderHierarchy for this folder and all subfolders
            
        Raises:
            TraversalError: If traversal fails or max depth exceeded
        """
        # Check for maximum depth to prevent infinite recursion
        if depth > self.max_depth:
            raise TraversalError(f"Maximum traversal depth ({self.max_depth}) exceeded")
        
        # Check for circular references
        if folder_id in self._visited_folders:
            logger.warning(f"Circular reference detected for folder {folder_id}, skipping")
            # Return empty hierarchy to avoid infinite loops
            root_item = QuipItem(
                id=folder_id,
                name=f"Circular Reference: {folder_id}",
                type="folder",
                url=f"https://quip-amazon.com/folder/{folder_id}"
            )
            return FolderHierarchy(root_folder=root_item)
        
        # Mark this folder as visited
        self._visited_folders.add(folder_id)
        
        try:
            # Get folder contents from API
            folder_contents = self.client.get_folder_contents(folder_id)
            folder_name = folder_contents.folder_name or f"Folder {folder_id}"
            logger.debug(f"Traversing folder '{folder_name}' ({folder_id}) at depth {depth}")
            
            # Create root folder item using the actual name from the API
            root_item = QuipItem(
                id=folder_id,
                name=folder_name,  # Use actual name from API
                type="folder",
                url=f"https://quip-amazon.com/folder/{folder_id}"
            )
            
            # Initialize hierarchy
            hierarchy = FolderHierarchy(
                root_folder=root_item,
                documents=folder_contents.documents
            )
            
            # Recursively traverse subfolders
            for subfolder in folder_contents.folders:
                try:
                    logger.debug(f"Recursively traversing subfolder: {subfolder.name} ({subfolder.id})")
                    subfolder_hierarchy = self._traverse_recursive(subfolder.id, depth + 1)
                    hierarchy.subfolders[subfolder.id] = subfolder_hierarchy
                    
                except QuipAPIError as e:
                    logger.error(f"Failed to traverse subfolder '{subfolder.name}' ({subfolder.id}): {str(e)}")
                    # Continue with other subfolders instead of failing completely
                    continue
                except Exception as e:
                    logger.error(f"Unexpected error traversing subfolder '{subfolder.name}' ({subfolder.id}): {str(e)}")
                    continue
            
            logger.debug(f"Completed traversal of folder '{folder_name}' ({folder_id}): "
                        f"{len(hierarchy.subfolders)} subfolders, {len(hierarchy.documents)} documents")
            
            return hierarchy
            
        finally:
            # Remove from visited set when we're done with this branch
            # This allows the same folder to be visited in different branches if needed
            self._visited_folders.discard(folder_id)
    
    def get_folder_metadata(self, folder_id: str) -> Optional[QuipItem]:
        """
        Get metadata for a specific folder.
        
        Args:
            folder_id: ID of the folder
            
        Returns:
            QuipItem with folder metadata, or None if not accessible
        """
        try:
            # Note: The current Quip API doesn't have a direct folder metadata endpoint
            # We get folder names from the parent folder's children list
            # This is a placeholder for potential future API enhancement
            return QuipItem(
                id=folder_id,
                name=f"Folder {folder_id}",
                type="folder",
                url=f"https://quip-amazon.com/folder/{folder_id}"
            )
        except QuipAPIError as e:
            logger.warning(f"Could not get metadata for folder {folder_id}: {str(e)}")
            return None
    
    def build_document_list(self, hierarchy: FolderHierarchy, base_path: str = "") -> List[DocumentInfo]:
        """
        Build a flat list of all documents in the hierarchy with path information.
        
        Args:
            hierarchy: FolderHierarchy to process
            base_path: Base path for relative paths
            
        Returns:
            List of DocumentInfo objects with path information
        """
        documents = []
        
        # Current folder path
        current_path = f"{base_path}/{hierarchy.root_folder.name}".strip("/")
        
        # Add documents from this folder
        for doc in hierarchy.documents:
            doc_info = DocumentInfo(
                item=doc,
                relative_path=current_path,
                local_file_path=""  # Will be set by FileSystemManager
            )
            documents.append(doc_info)
        
        # Recursively add documents from subfolders
        for subfolder_hierarchy in hierarchy.subfolders.values():
            subfolder_docs = self.build_document_list(subfolder_hierarchy, current_path)
            documents.extend(subfolder_docs)
        
        return documents
    
    def get_traversal_stats(self, hierarchy: FolderHierarchy) -> Dict[str, int]:
        """
        Get statistics about the traversed hierarchy.
        
        Args:
            hierarchy: FolderHierarchy to analyze
            
        Returns:
            Dictionary with traversal statistics
        """
        stats = {
            "total_folders": hierarchy.total_folders,
            "total_documents": hierarchy.total_documents,
            "max_depth": self._calculate_max_depth(hierarchy),
            "empty_folders": self._count_empty_folders(hierarchy)
        }
        
        return stats
    
    def _calculate_max_depth(self, hierarchy: FolderHierarchy, current_depth: int = 0) -> int:
        """Calculate the maximum depth of the folder hierarchy."""
        if not hierarchy.subfolders:
            return current_depth
        
        max_subfolder_depth = 0
        for subfolder in hierarchy.subfolders.values():
            subfolder_depth = self._calculate_max_depth(subfolder, current_depth + 1)
            max_subfolder_depth = max(max_subfolder_depth, subfolder_depth)
        
        return max_subfolder_depth
    
    def _count_empty_folders(self, hierarchy: FolderHierarchy) -> int:
        """Count the number of empty folders in the hierarchy."""
        count = 0
        
        # Check if this folder is empty (no documents and no subfolders)
        if not hierarchy.documents and not hierarchy.subfolders:
            count += 1
        
        # Recursively count empty subfolders
        for subfolder in hierarchy.subfolders.values():
            count += self._count_empty_folders(subfolder)
        
        return count
    
    def validate_hierarchy(self, hierarchy: FolderHierarchy) -> List[str]:
        """
        Validate the folder hierarchy for potential issues.
        
        Args:
            hierarchy: FolderHierarchy to validate
            
        Returns:
            List of validation warnings/errors
        """
        issues = []
        
        # Check for empty hierarchy
        if hierarchy.total_documents == 0 and hierarchy.total_folders == 1:
            issues.append("Hierarchy appears to be empty (no documents found)")
        
        # Check for very deep hierarchies
        max_depth = self._calculate_max_depth(hierarchy)
        if max_depth > 20:
            issues.append(f"Very deep folder hierarchy detected (depth: {max_depth})")
        
        # Check for folders with many items (potential performance issues)
        self._check_large_folders(hierarchy, issues)
        
        return issues
    
    def _check_large_folders(self, hierarchy: FolderHierarchy, issues: List[str], path: str = "") -> None:
        """Check for folders with unusually large numbers of items."""
        current_path = f"{path}/{hierarchy.root_folder.name}".strip("/")
        total_items = len(hierarchy.documents) + len(hierarchy.subfolders)
        
        if total_items > 100:
            issues.append(f"Large folder detected: '{current_path}' has {total_items} items")
        
        # Recursively check subfolders
        for subfolder in hierarchy.subfolders.values():
            self._check_large_folders(subfolder, issues, current_path)