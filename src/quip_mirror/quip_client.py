"""
Quip API client for folder traversal and document export.

This module provides the QuipAPIClient class that handles all communication
with Quip's REST API for folder listing, document metadata, and DOCX export.
"""

import re
import time
import logging
from typing import Dict, Any, Optional, Tuple
from urllib.parse import urlparse, parse_qs
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .models import QuipItem, FolderContents, DocumentContent


logger = logging.getLogger(__name__)


class QuipAPIError(Exception):
    """Exception raised for Quip API errors."""
    
    def __init__(self, message: str, status_code: Optional[int] = None, response_text: Optional[str] = None):
        super().__init__(message)
        self.status_code = status_code
        self.response_text = response_text


class QuipAPIClient:
    """Client for interacting with Quip's REST API."""
    
    def __init__(self, access_token: str, timeout: int = 30, max_retries: int = 3):
        """
        Initialize the Quip API client.
        
        Args:
            access_token: Quip personal access token
            timeout: Request timeout in seconds
            max_retries: Maximum number of retry attempts
        """
        self.access_token = access_token
        self.base_url = "https://platform.quip-amazon.com/1"
        self.timeout = timeout
        
        # Set up session with retry strategy
        self.session = requests.Session()
        retry_strategy = Retry(
            total=max_retries,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["GET"]
        )
        adapter = HTTPAdapter(max_retries=retry_strategy)
        self.session.mount("http://", adapter)
        self.session.mount("https://", adapter)
        
        # Set default headers
        self.session.headers.update({
            "Authorization": f"Bearer {access_token}",
            "User-Agent": "QuipFolderMirror/0.1.0"
        })
    
    def extract_folder_id_from_url(self, url: str) -> str:
        """
        Extract folder ID from a Quip folder URL.
        
        Args:
            url: Quip folder URL
            
        Returns:
            Folder ID extracted from the URL
            
        Raises:
            QuipAPIError: If URL is invalid or folder ID cannot be extracted
        """
        if not url.startswith("https://quip-amazon.com/"):
            raise QuipAPIError(f"Invalid Quip URL. Must start with 'https://quip-amazon.com/': {url}")
        
        # Parse the URL to extract folder ID
        parsed = urlparse(url)
        path_parts = parsed.path.strip('/').split('/')
        
        # Handle different URL formats:
        # https://quip-amazon.com/folder/ABC123
        # https://quip-amazon.com/ABC123 (direct folder ID)
        # https://quip-amazon.com/folder/ABC123/some-folder-name
        
        if len(path_parts) >= 2 and path_parts[0] == 'folder':
            folder_id = path_parts[1]
        elif len(path_parts) >= 1 and path_parts[0]:
            # Direct folder ID or other format
            folder_id = path_parts[0]
        else:
            raise QuipAPIError(f"Cannot extract folder ID from URL: {url}")
        
        # Validate folder ID format (alphanumeric)
        if not re.match(r'^[a-zA-Z0-9]+$', folder_id):
            raise QuipAPIError(f"Invalid folder ID format: {folder_id}")
        
        logger.debug(f"Extracted folder ID '{folder_id}' from URL: {url}")
        return folder_id
    
    def get_folder_contents(self, folder_id: str) -> FolderContents:
        """
        Get the contents of a Quip folder.
        
        Args:
            folder_id: Quip folder ID
            
        Returns:
            FolderContents object with folders and documents
            
        Raises:
            QuipAPIError: If API request fails
        """
        url = f"{self.base_url}/folders/{folder_id}"
        
        try:
            logger.debug(f"Fetching folder contents for ID: {folder_id}")
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 401:
                raise QuipAPIError("Authentication failed. Please check your access token.", 401, response.text)
            elif response.status_code == 403:
                raise QuipAPIError(f"Access denied to folder {folder_id}. Check permissions.", 403, response.text)
            elif response.status_code == 404:
                raise QuipAPIError(f"Folder {folder_id} not found.", 404, response.text)
            elif response.status_code != 200:
                raise QuipAPIError(
                    f"Failed to fetch folder {folder_id}. Status: {response.status_code}",
                    response.status_code,
                    response.text
                )
            
            data = response.json()
            return self._parse_folder_contents(data)
            
        except requests.exceptions.Timeout:
            raise QuipAPIError(f"Timeout while fetching folder {folder_id}")
        except requests.exceptions.RequestException as e:
            raise QuipAPIError(f"Network error while fetching folder {folder_id}: {str(e)}")
        except ValueError as e:
            raise QuipAPIError(f"Invalid JSON response for folder {folder_id}: {str(e)}")
    
    def get_document_metadata(self, thread_id: str) -> DocumentContent:
        """
        Get metadata for a Quip document.
        
        Args:
            thread_id: Quip document/thread ID
            
        Returns:
            DocumentContent object with document information
            
        Raises:
            QuipAPIError: If API request fails
        """
        url = f"{self.base_url}/threads/{thread_id}"
        
        try:
            logger.debug(f"Fetching document metadata for ID: {thread_id}")
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 401:
                raise QuipAPIError("Authentication failed. Please check your access token.", 401, response.text)
            elif response.status_code == 403:
                raise QuipAPIError(f"Access denied to document {thread_id}. Check permissions.", 403, response.text)
            elif response.status_code == 404:
                raise QuipAPIError(f"Document {thread_id} not found.", 404, response.text)
            elif response.status_code != 200:
                raise QuipAPIError(
                    f"Failed to fetch document {thread_id}. Status: {response.status_code}",
                    response.status_code,
                    response.text
                )
            
            data = response.json()
            thread_info = data.get("thread", {})
            
            return DocumentContent(
                title=thread_info.get("title", "Untitled"),
                content="",  # Content not needed for metadata
                format="quip"
            )
            
        except requests.exceptions.Timeout:
            raise QuipAPIError(f"Timeout while fetching document {thread_id}")
        except requests.exceptions.RequestException as e:
            raise QuipAPIError(f"Network error while fetching document {thread_id}: {str(e)}")
        except ValueError as e:
            raise QuipAPIError(f"Invalid JSON response for document {thread_id}: {str(e)}")
    
    def export_document_to_docx(self, thread_id: str, file_path: str) -> bool:
        """
        Export a Quip document to Word format.
        
        Args:
            thread_id: Quip document/thread ID
            file_path: Local file path to save the DOCX file
            
        Returns:
            True if export was successful, False otherwise
            
        Raises:
            QuipAPIError: If API request fails
        """
        export_url = f"{self.base_url}/threads/{thread_id}/export/docx"
        
        try:
            logger.debug(f"Exporting document {thread_id} to {file_path}")
            response = self.session.get(export_url, timeout=self.timeout)
            
            if response.status_code == 401:
                raise QuipAPIError("Authentication failed. Please check your access token.", 401, response.text)
            elif response.status_code == 403:
                raise QuipAPIError(f"Access denied to document {thread_id}. Check permissions.", 403, response.text)
            elif response.status_code == 404:
                raise QuipAPIError(f"Document {thread_id} not found.", 404, response.text)
            elif response.status_code != 200:
                raise QuipAPIError(
                    f"Failed to export document {thread_id}. Status: {response.status_code}",
                    response.status_code,
                    response.text
                )
            
            # Write binary content to file
            with open(file_path, "wb") as f:
                f.write(response.content)
            
            logger.debug(f"Successfully exported document {thread_id} to {file_path}")
            return True
            
        except requests.exceptions.Timeout:
            raise QuipAPIError(f"Timeout while exporting document {thread_id}")
        except requests.exceptions.RequestException as e:
            raise QuipAPIError(f"Network error while exporting document {thread_id}: {str(e)}")
        except IOError as e:
            raise QuipAPIError(f"Failed to write file {file_path}: {str(e)}")
    
    def _parse_folder_contents(self, data: Dict[str, Any]) -> FolderContents:
        """
        Parse folder contents from API response.
        
        Args:
            data: Raw API response data
            
        Returns:
            FolderContents object
        """
        folders = []
        documents = []
        
        # Extract the folder name from the response
        folder_info = data.get("folder", {})
        folder_name = folder_info.get("title", "Untitled Folder")
        
        children = data.get("children", [])
        
        for child in children:
            if "folder_id" in child:
                # This is a subfolder
                folder_item = QuipItem(
                    id=child["folder_id"],
                    name=child.get("title", "Untitled Folder"),
                    type="folder",
                    url=f"https://quip-amazon.com/folder/{child['folder_id']}"
                )
                folders.append(folder_item)
                
            elif "thread_id" in child:
                # This is a document
                document_item = QuipItem(
                    id=child["thread_id"],
                    name=child.get("title", "Untitled Document"),
                    type="document",
                    url=f"https://quip-amazon.com/{child['thread_id']}"
                )
                documents.append(document_item)
        
        logger.debug(f"Parsed folder contents: {len(folders)} folders, {len(documents)} documents")
        return FolderContents(folders=folders, documents=documents, folder_name=folder_name)
    
    def is_folder(self, item: Dict[str, Any]) -> bool:
        """Check if an API response item is a folder."""
        return "folder_id" in item
    
    def is_document(self, item: Dict[str, Any]) -> bool:
        """Check if an API response item is a document."""
        return "thread_id" in item
    
    def test_connection(self) -> Tuple[bool, str]:
        """
        Test the API connection and authentication.
        
        Returns:
            Tuple of (success, message)
        """
        try:
            # Try to access the user's info endpoint
            url = f"{self.base_url}/users/current"
            response = self.session.get(url, timeout=self.timeout)
            
            if response.status_code == 200:
                return True, "Connection successful"
            elif response.status_code == 401:
                return False, "Authentication failed. Please check your access token."
            else:
                return False, f"Connection failed. Status: {response.status_code}"
                
        except requests.exceptions.RequestException as e:
            return False, f"Network error: {str(e)}"