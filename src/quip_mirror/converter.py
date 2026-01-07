"""
Document conversion functionality for exporting Quip documents to Word format.

This module provides the DocumentConverter class that handles the conversion
of Quip documents to DOCX format using the Quip API's direct export functionality.
"""

import logging
from pathlib import Path
from typing import Optional, Tuple
import time

from .models import DocumentInfo, DocumentContent
from .quip_client import QuipAPIClient, QuipAPIError
from .filesystem import FileSystemManager, FileSystemError


logger = logging.getLogger(__name__)


class ConversionError(Exception):
    """Exception raised during document conversion."""
    pass


class DocumentConverter:
    """Handles conversion of Quip documents to Word format."""
    
    def __init__(self, client: QuipAPIClient, filesystem_manager: FileSystemManager):
        """
        Initialize the document converter.
        
        Args:
            client: QuipAPIClient for API operations
            filesystem_manager: FileSystemManager for file operations
        """
        self.client = client
        self.filesystem_manager = filesystem_manager
        self.conversion_stats = {
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
    
    def export_to_word(self, doc_info: DocumentInfo, output_path: Optional[str] = None) -> Tuple[bool, str]:
        """
        Export a Quip document to Word format.
        
        Args:
            doc_info: DocumentInfo object containing document details
            output_path: Optional custom output path (overrides doc_info.local_file_path)
            
        Returns:
            Tuple of (success, message)
        """
        # Determine output path
        if output_path is None:
            if not doc_info.local_file_path:
                output_path = self.filesystem_manager.get_document_path(doc_info)
            else:
                output_path = doc_info.local_file_path
        
        try:
            # Ensure output directory exists
            output_dir = Path(output_path).parent
            self.filesystem_manager.ensure_directory_exists(str(output_dir))
            
            # Handle file conflicts
            should_proceed, conflict_message = self.filesystem_manager.handle_file_conflict(output_path)
            if not should_proceed:
                self.conversion_stats["skipped"] += 1
                return False, conflict_message
            
            # Get document metadata first (for better error messages)
            try:
                doc_metadata = self.client.get_document_metadata(doc_info.item.id)
                logger.debug(f"Converting document: {doc_metadata.title} ({doc_info.item.id})")
            except QuipAPIError as e:
                logger.warning(f"Could not get metadata for document {doc_info.item.id}: {str(e)}")
                doc_metadata = None
            
            # Export document to DOCX
            success = self.client.export_document_to_docx(doc_info.item.id, output_path)
            
            if success:
                # Verify the file was created and has content
                if self.filesystem_manager.file_exists(output_path):
                    file_size = self.filesystem_manager.get_file_size(output_path)
                    if file_size > 0:
                        self.conversion_stats["successful"] += 1
                        doc_name = doc_metadata.title if doc_metadata else doc_info.item.name
                        return True, f"Successfully exported '{doc_name}' ({file_size} bytes)"
                    else:
                        self.conversion_stats["failed"] += 1
                        return False, f"Exported file is empty: {output_path}"
                else:
                    self.conversion_stats["failed"] += 1
                    return False, f"Export appeared successful but file was not created: {output_path}"
            else:
                self.conversion_stats["failed"] += 1
                return False, f"Export failed for document {doc_info.item.id}"
                
        except QuipAPIError as e:
            self.conversion_stats["failed"] += 1
            error_msg = f"API error exporting document {doc_info.item.id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except FileSystemError as e:
            self.conversion_stats["failed"] += 1
            error_msg = f"File system error exporting document {doc_info.item.id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
            
        except Exception as e:
            self.conversion_stats["failed"] += 1
            error_msg = f"Unexpected error exporting document {doc_info.item.id}: {str(e)}"
            logger.error(error_msg)
            return False, error_msg
    
    def batch_export(self, documents: list[DocumentInfo], progress_callback=None) -> dict:
        """
        Export multiple documents in batch.
        
        Args:
            documents: List of DocumentInfo objects to export
            progress_callback: Optional callback function for progress updates
            
        Returns:
            Dictionary with batch export results
        """
        results = {
            "successful": [],
            "failed": [],
            "skipped": [],
            "total": len(documents)
        }
        
        logger.info(f"Starting batch export of {len(documents)} documents")
        
        for i, doc_info in enumerate(documents):
            try:
                # Call progress callback if provided
                if progress_callback:
                    progress_callback(i + 1, len(documents), doc_info.item.name)
                
                success, message = self.export_to_word(doc_info)
                
                if success:
                    results["successful"].append({
                        "document": doc_info.item.name,
                        "id": doc_info.item.id,
                        "path": doc_info.local_file_path or "auto-generated",
                        "message": message
                    })
                elif "skipped" in message.lower():
                    results["skipped"].append({
                        "document": doc_info.item.name,
                        "id": doc_info.item.id,
                        "reason": message
                    })
                else:
                    results["failed"].append({
                        "document": doc_info.item.name,
                        "id": doc_info.item.id,
                        "error": message
                    })
                
                # Small delay to avoid overwhelming the API
                time.sleep(0.1)
                
            except Exception as e:
                error_msg = f"Unexpected error processing document {doc_info.item.name}: {str(e)}"
                logger.error(error_msg)
                results["failed"].append({
                    "document": doc_info.item.name,
                    "id": doc_info.item.id,
                    "error": error_msg
                })
        
        logger.info(f"Batch export completed: {len(results['successful'])} successful, "
                   f"{len(results['failed'])} failed, {len(results['skipped'])} skipped")
        
        return results
    
    def sanitize_filename(self, title: str) -> str:
        """
        Sanitize document title for use as filename.
        
        Args:
            title: Original document title
            
        Returns:
            Sanitized filename
        """
        return self.filesystem_manager.sanitize_filename(title)
    
    def handle_file_conflict(self, file_path: str, overwrite: bool = None) -> Tuple[bool, str]:
        """
        Handle file naming conflicts.
        
        Args:
            file_path: Path where conflict occurred
            overwrite: Override the default overwrite setting
            
        Returns:
            Tuple of (should_proceed, message)
        """
        if overwrite is not None:
            # Temporarily override the filesystem manager's setting
            original_setting = self.filesystem_manager.overwrite_existing
            self.filesystem_manager.overwrite_existing = overwrite
            try:
                return self.filesystem_manager.handle_file_conflict(file_path)
            finally:
                self.filesystem_manager.overwrite_existing = original_setting
        else:
            return self.filesystem_manager.handle_file_conflict(file_path)
    
    def get_conversion_stats(self) -> dict:
        """
        Get conversion statistics.
        
        Returns:
            Dictionary with conversion statistics
        """
        total = sum(self.conversion_stats.values())
        stats = self.conversion_stats.copy()
        stats["total"] = total
        
        if total > 0:
            stats["success_rate"] = (stats["successful"] / total) * 100
        else:
            stats["success_rate"] = 0.0
        
        return stats
    
    def reset_stats(self) -> None:
        """Reset conversion statistics."""
        self.conversion_stats = {
            "successful": 0,
            "failed": 0,
            "skipped": 0
        }
    
    def validate_document_export(self, file_path: str) -> Tuple[bool, str]:
        """
        Validate that an exported document is valid.
        
        Args:
            file_path: Path to the exported DOCX file
            
        Returns:
            Tuple of (is_valid, message)
        """
        try:
            if not self.filesystem_manager.file_exists(file_path):
                return False, "File does not exist"
            
            file_size = self.filesystem_manager.get_file_size(file_path)
            if file_size == 0:
                return False, "File is empty"
            
            # Basic validation - check if it's a valid ZIP file (DOCX is ZIP-based)
            try:
                import zipfile
                with zipfile.ZipFile(file_path, 'r') as zip_file:
                    # Check for required DOCX structure
                    required_files = ['[Content_Types].xml', '_rels/.rels']
                    for required_file in required_files:
                        if required_file not in zip_file.namelist():
                            return False, f"Invalid DOCX structure: missing {required_file}"
                
                return True, f"Valid DOCX file ({file_size} bytes)"
                
            except zipfile.BadZipFile:
                return False, "File is not a valid ZIP/DOCX file"
            
        except Exception as e:
            return False, f"Validation error: {str(e)}"
    
    def estimate_conversion_time(self, document_count: int) -> float:
        """
        Estimate total conversion time based on document count.
        
        Args:
            document_count: Number of documents to convert
            
        Returns:
            Estimated time in seconds
        """
        # Base estimate: ~2 seconds per document (API call + file I/O)
        # This is a rough estimate and actual time will vary
        base_time_per_doc = 2.0
        
        # Add some overhead for batch processing
        overhead = min(document_count * 0.1, 30)  # Max 30 seconds overhead
        
        return (document_count * base_time_per_doc) + overhead
    
    def get_failed_documents(self) -> list:
        """
        Get list of documents that failed to convert in the last batch operation.
        
        Returns:
            List of failed document information
        """
        # This would need to be implemented with state tracking
        # For now, return empty list as this is a stateless implementation
        return []