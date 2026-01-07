"""
Unit tests for the models module.
"""

import pytest
from quip_mirror.models import (
    MirrorConfig, QuipItem, FolderContents, FolderHierarchy,
    DocumentInfo, DocumentContent, ProcessingSummary
)


class TestMirrorConfig:
    """Test cases for MirrorConfig."""
    
    def test_valid_config(self, temp_dir):
        """Test creating a valid configuration."""
        config = MirrorConfig(
            quip_folder_url="https://quip-amazon.com/folder/test123",
            target_path=temp_dir,
            access_token="test_token"
        )
        
        assert config.quip_folder_url == "https://quip-amazon.com/folder/test123"
        assert config.target_path == temp_dir
        assert config.access_token == "test_token"
        assert config.overwrite_existing is True
    
    def test_invalid_url(self, temp_dir):
        """Test configuration with invalid URL."""
        with pytest.raises(ValueError, match="Quip URL must start with"):
            MirrorConfig(
                quip_folder_url="https://invalid.com/folder/test123",
                target_path=temp_dir
            )
    
    def test_empty_url(self, temp_dir):
        """Test configuration with empty URL."""
        with pytest.raises(ValueError, match="Quip folder URL is required"):
            MirrorConfig(
                quip_folder_url="",
                target_path=temp_dir
            )
    
    def test_empty_target_path(self):
        """Test configuration with empty target path."""
        with pytest.raises(ValueError, match="Target path is required"):
            MirrorConfig(
                quip_folder_url="https://quip-amazon.com/folder/test123",
                target_path=""
            )


class TestQuipItem:
    """Test cases for QuipItem."""
    
    def test_valid_folder_item(self):
        """Test creating a valid folder item."""
        item = QuipItem(
            id="folder123",
            name="Test Folder",
            type="folder",
            url="https://quip-amazon.com/folder/folder123"
        )
        
        assert item.id == "folder123"
        assert item.name == "Test Folder"
        assert item.type == "folder"
        assert item.url == "https://quip-amazon.com/folder/folder123"
    
    def test_valid_document_item(self):
        """Test creating a valid document item."""
        item = QuipItem(
            id="doc123",
            name="Test Document",
            type="document",
            url="https://quip-amazon.com/doc/doc123"
        )
        
        assert item.id == "doc123"
        assert item.name == "Test Document"
        assert item.type == "document"
        assert item.url == "https://quip-amazon.com/doc/doc123"
    
    def test_invalid_type(self):
        """Test creating item with invalid type."""
        with pytest.raises(ValueError, match="Invalid type"):
            QuipItem(
                id="test123",
                name="Test Item",
                type="invalid",
                url="https://quip-amazon.com/test123"
            )
    
    def test_empty_id(self):
        """Test creating item with empty ID."""
        with pytest.raises(ValueError, match="Item ID is required"):
            QuipItem(
                id="",
                name="Test Item",
                type="folder",
                url="https://quip-amazon.com/test123"
            )
    
    def test_empty_name(self):
        """Test creating item with empty name."""
        with pytest.raises(ValueError, match="Item name is required"):
            QuipItem(
                id="test123",
                name="",
                type="folder",
                url="https://quip-amazon.com/test123"
            )


class TestFolderContents:
    """Test cases for FolderContents."""
    
    def test_empty_folder_contents(self):
        """Test empty folder contents."""
        contents = FolderContents()
        
        assert len(contents.folders) == 0
        assert len(contents.documents) == 0
        assert contents.total_items == 0
        assert contents.is_empty() is True
    
    def test_folder_contents_with_items(self, sample_folder_item, sample_document_item):
        """Test folder contents with items."""
        contents = FolderContents(
            folders=[sample_folder_item],
            documents=[sample_document_item]
        )
        
        assert len(contents.folders) == 1
        assert len(contents.documents) == 1
        assert contents.total_items == 2
        assert contents.is_empty() is False


class TestFolderHierarchy:
    """Test cases for FolderHierarchy."""
    
    def test_simple_hierarchy(self, sample_folder_item, sample_document_item):
        """Test simple folder hierarchy."""
        hierarchy = FolderHierarchy(
            root_folder=sample_folder_item,
            documents=[sample_document_item]
        )
        
        assert hierarchy.root_folder == sample_folder_item
        assert len(hierarchy.documents) == 1
        assert len(hierarchy.subfolders) == 0
        assert hierarchy.total_folders == 1
        assert hierarchy.total_documents == 1
    
    def test_nested_hierarchy(self, sample_folder_item, sample_document_item):
        """Test nested folder hierarchy."""
        # Create subfolder hierarchy
        subfolder_item = QuipItem(
            id="subfolder123",
            name="Sub Folder",
            type="folder",
            url="https://quip-amazon.com/folder/subfolder123"
        )
        
        subfolder_hierarchy = FolderHierarchy(
            root_folder=subfolder_item,
            documents=[sample_document_item]
        )
        
        # Create main hierarchy
        hierarchy = FolderHierarchy(
            root_folder=sample_folder_item,
            subfolders={"subfolder123": subfolder_hierarchy}
        )
        
        assert hierarchy.total_folders == 2  # Root + subfolder
        assert hierarchy.total_documents == 1  # Document in subfolder
        
        # Test get_all_documents
        all_docs = hierarchy.get_all_documents()
        assert len(all_docs) == 1
        assert all_docs[0].item == sample_document_item


class TestDocumentInfo:
    """Test cases for DocumentInfo."""
    
    def test_valid_document_info(self, sample_document_item):
        """Test creating valid document info."""
        doc_info = DocumentInfo(
            item=sample_document_item,
            relative_path="folder/subfolder",
            local_file_path="/local/path/document.docx"
        )
        
        assert doc_info.item == sample_document_item
        assert doc_info.relative_path == "folder/subfolder"
        assert doc_info.local_file_path == "/local/path/document.docx"
    
    def test_invalid_item_type(self, sample_folder_item):
        """Test creating document info with folder item."""
        with pytest.raises(ValueError, match="DocumentInfo can only be created for document items"):
            DocumentInfo(
                item=sample_folder_item,
                relative_path="folder",
                local_file_path="/local/path"
            )


class TestDocumentContent:
    """Test cases for DocumentContent."""
    
    def test_document_content(self):
        """Test creating document content."""
        content = DocumentContent(
            title="Test Document",
            content="<p>Test content</p>",
            format="html"
        )
        
        assert content.title == "Test Document"
        assert content.content == "<p>Test content</p>"
        assert content.format == "html"
    
    def test_sanitize_title_for_filename(self):
        """Test filename sanitization."""
        content = DocumentContent(
            title="Test/Document<>:\"\\|?*",
            content="",
            format="html"
        )
        
        sanitized = content.sanitize_title_for_filename()
        assert "/" not in sanitized
        assert "<" not in sanitized
        assert ">" not in sanitized
        assert ":" not in sanitized
        assert "\"" not in sanitized
        assert "\\" not in sanitized
        assert "|" not in sanitized
        assert "?" not in sanitized
        assert "*" not in sanitized
    
    def test_sanitize_empty_title(self):
        """Test sanitizing empty title."""
        content = DocumentContent(
            title="",
            content="",
            format="html"
        )
        
        sanitized = content.sanitize_title_for_filename()
        assert sanitized == "untitled"


class TestProcessingSummary:
    """Test cases for ProcessingSummary."""
    
    def test_empty_summary(self):
        """Test empty processing summary."""
        summary = ProcessingSummary()
        
        assert summary.total_folders == 0
        assert summary.total_documents == 0
        assert summary.successful_conversions == 0
        assert summary.failed_conversions == 0
        assert len(summary.errors) == 0
        assert summary.success_rate == 100.0
    
    def test_summary_with_data(self):
        """Test processing summary with data."""
        summary = ProcessingSummary(
            total_folders=5,
            total_documents=10,
            successful_conversions=8,
            failed_conversions=2
        )
        
        assert summary.total_folders == 5
        assert summary.total_documents == 10
        assert summary.successful_conversions == 8
        assert summary.failed_conversions == 2
        assert summary.success_rate == 80.0
    
    def test_summary_methods(self):
        """Test processing summary methods."""
        summary = ProcessingSummary()
        
        summary.add_error("Test error")
        assert len(summary.errors) == 1
        assert summary.errors[0] == "Test error"
        
        summary.increment_success()
        assert summary.successful_conversions == 1
        
        summary.increment_failure()
        assert summary.failed_conversions == 1
    
    def test_summary_string_representation(self):
        """Test string representation of summary."""
        summary = ProcessingSummary(
            total_folders=2,
            total_documents=5,
            successful_conversions=4,
            failed_conversions=1,
            errors=["Test error"]
        )
        
        str_repr = str(summary)
        assert "Total folders: 2" in str_repr
        assert "Total documents: 5" in str_repr
        assert "Successful conversions: 4" in str_repr
        assert "Failed conversions: 1" in str_repr
        assert "Success rate: 80.0%" in str_repr
        assert "Errors: 1" in str_repr