"""
Unit tests for the Quip API client.
"""

import pytest
import responses
from unittest.mock import Mock, patch
from quip_mirror.quip_client import QuipAPIClient, QuipAPIError
from quip_mirror.models import FolderContents, DocumentContent


class TestQuipAPIClient:
    """Test cases for QuipAPIClient."""
    
    def test_client_initialization(self):
        """Test client initialization."""
        client = QuipAPIClient("test_token")
        
        assert client.access_token == "test_token"
        assert client.base_url == "https://platform.quip.com/1"
        assert client.timeout == 30
        assert "Bearer test_token" in client.session.headers["Authorization"]
    
    def test_extract_folder_id_from_url(self):
        """Test folder ID extraction from various URL formats."""
        client = QuipAPIClient("test_token")
        
        # Standard folder URL
        folder_id = client.extract_folder_id_from_url("https://quip-amazon.com/folder/ABC123")
        assert folder_id == "ABC123"
        
        # Direct folder ID URL
        folder_id = client.extract_folder_id_from_url("https://quip-amazon.com/ABC123")
        assert folder_id == "ABC123"
        
        # Folder URL with additional path
        folder_id = client.extract_folder_id_from_url("https://quip-amazon.com/folder/ABC123/folder-name")
        assert folder_id == "ABC123"
    
    def test_extract_folder_id_invalid_url(self):
        """Test folder ID extraction with invalid URLs."""
        client = QuipAPIClient("test_token")
        
        # Invalid domain
        with pytest.raises(QuipAPIError, match="Invalid Quip URL"):
            client.extract_folder_id_from_url("https://invalid.com/folder/ABC123")
        
        # Empty path
        with pytest.raises(QuipAPIError, match="Cannot extract folder ID"):
            client.extract_folder_id_from_url("https://quip-amazon.com/")
        
        # Invalid folder ID format
        with pytest.raises(QuipAPIError, match="Invalid folder ID format"):
            client.extract_folder_id_from_url("https://quip-amazon.com/folder/ABC-123!")
    
    @responses.activate
    def test_get_folder_contents_success(self):
        """Test successful folder contents retrieval."""
        client = QuipAPIClient("test_token")
        
        # Mock API response
        mock_response = {
            "folder": {
                "id": "folder123",
                "title": "Test Folder"
            },
            "children": [
                {
                    "folder_id": "subfolder123",
                    "title": "Sub Folder"
                },
                {
                    "thread_id": "doc123",
                    "title": "Test Document"
                }
            ]
        }
        
        responses.add(
            responses.GET,
            "https://platform.quip.com/1/folders/folder123",
            json=mock_response,
            status=200
        )
        
        contents = client.get_folder_contents("folder123")
        
        assert isinstance(contents, FolderContents)
        assert len(contents.folders) == 1
        assert len(contents.documents) == 1
        assert contents.folders[0].id == "subfolder123"
        assert contents.folders[0].name == "Sub Folder"
        assert contents.documents[0].id == "doc123"
        assert contents.documents[0].name == "Test Document"
    
    @responses.activate
    def test_get_folder_contents_auth_error(self):
        """Test folder contents retrieval with authentication error."""
        client = QuipAPIClient("test_token")
        
        responses.add(
            responses.GET,
            "https://platform.quip.com/1/folders/folder123",
            json={"error": "Unauthorized"},
            status=401
        )
        
        with pytest.raises(QuipAPIError, match="Authentication failed"):
            client.get_folder_contents("folder123")
    
    @responses.activate
    def test_get_folder_contents_not_found(self):
        """Test folder contents retrieval with not found error."""
        client = QuipAPIClient("test_token")
        
        responses.add(
            responses.GET,
            "https://platform.quip.com/1/folders/folder123",
            json={"error": "Not found"},
            status=404
        )
        
        with pytest.raises(QuipAPIError, match="Folder folder123 not found"):
            client.get_folder_contents("folder123")
    
    @responses.activate
    def test_get_document_metadata_success(self):
        """Test successful document metadata retrieval."""
        client = QuipAPIClient("test_token")
        
        mock_response = {
            "thread": {
                "id": "doc123",
                "title": "Test Document",
                "type": "document"
            }
        }
        
        responses.add(
            responses.GET,
            "https://platform.quip.com/1/threads/doc123",
            json=mock_response,
            status=200
        )
        
        content = client.get_document_metadata("doc123")
        
        assert isinstance(content, DocumentContent)
        assert content.title == "Test Document"
        assert content.format == "quip"
    
    @responses.activate
    def test_export_document_to_docx_success(self, temp_dir):
        """Test successful document export."""
        client = QuipAPIClient("test_token")
        
        mock_docx_content = b"Mock DOCX content"
        
        responses.add(
            responses.GET,
            "https://platform.quip.com/1/threads/doc123/export/docx",
            body=mock_docx_content,
            status=200
        )
        
        file_path = f"{temp_dir}/test_document.docx"
        success = client.export_document_to_docx("doc123", file_path)
        
        assert success is True
        
        # Verify file was created with correct content
        with open(file_path, "rb") as f:
            content = f.read()
        assert content == mock_docx_content
    
    @responses.activate
    def test_export_document_to_docx_failure(self, temp_dir):
        """Test failed document export."""
        client = QuipAPIClient("test_token", max_retries=0)  # Disable retries for this test
        
        responses.add(
            responses.GET,
            "https://platform.quip.com/1/threads/doc123/export/docx",
            json={"error": "Export failed"},
            status=500
        )
        
        file_path = f"{temp_dir}/test_document.docx"
        
        with pytest.raises(QuipAPIError, match="Network error while exporting document"):
            client.export_document_to_docx("doc123", file_path)
    
    def test_is_folder(self):
        """Test folder detection."""
        client = QuipAPIClient("test_token")
        
        folder_item = {"folder_id": "folder123", "title": "Test Folder"}
        document_item = {"thread_id": "doc123", "title": "Test Document"}
        
        assert client.is_folder(folder_item) is True
        assert client.is_folder(document_item) is False
    
    def test_is_document(self):
        """Test document detection."""
        client = QuipAPIClient("test_token")
        
        folder_item = {"folder_id": "folder123", "title": "Test Folder"}
        document_item = {"thread_id": "doc123", "title": "Test Document"}
        
        assert client.is_document(folder_item) is False
        assert client.is_document(document_item) is True
    
    @responses.activate
    def test_test_connection_success(self):
        """Test successful connection test."""
        client = QuipAPIClient("test_token")
        
        responses.add(
            responses.GET,
            "https://platform.quip.com/1/users/current",
            json={"user": {"id": "user123"}},
            status=200
        )
        
        success, message = client.test_connection()
        
        assert success is True
        assert message == "Connection successful"
    
    @responses.activate
    def test_test_connection_auth_failure(self):
        """Test connection test with authentication failure."""
        client = QuipAPIClient("test_token")
        
        responses.add(
            responses.GET,
            "https://platform.quip.com/1/users/current",
            json={"error": "Unauthorized"},
            status=401
        )
        
        success, message = client.test_connection()
        
        assert success is False
        assert "Authentication failed" in message
    
    def test_parse_folder_contents_empty(self):
        """Test parsing empty folder contents."""
        client = QuipAPIClient("test_token")
        
        data = {
            "folder": {"id": "folder123", "title": "Empty Folder"},
            "children": []
        }
        
        contents = client._parse_folder_contents(data)
        
        assert len(contents.folders) == 0
        assert len(contents.documents) == 0
        assert contents.is_empty() is True
        assert contents.folder_name == "Empty Folder"
    
    def test_parse_folder_contents_mixed(self):
        """Test parsing folder contents with mixed items."""
        client = QuipAPIClient("test_token")
        
        data = {
            "folder": {"id": "folder123", "title": "Mixed Folder"},
            "children": [
                {"folder_id": "sub1", "title": "Subfolder 1"},
                {"thread_id": "doc1", "title": "Document 1"},
                {"folder_id": "sub2", "title": "Subfolder 2"},
                {"thread_id": "doc2", "title": "Document 2"}
            ]
        }
        
        contents = client._parse_folder_contents(data)
        
        assert len(contents.folders) == 2
        assert len(contents.documents) == 2
        assert contents.total_items == 4
        
        # Check folder items
        folder_ids = [f.id for f in contents.folders]
        assert "sub1" in folder_ids
        assert "sub2" in folder_ids
        
        # Check document items
        doc_ids = [d.id for d in contents.documents]
        assert "doc1" in doc_ids
        assert "doc2" in doc_ids