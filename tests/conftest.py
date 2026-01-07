"""
Shared test configuration and fixtures for pytest.

This module contains common fixtures and configuration used across all tests.
"""

import pytest
import tempfile
import shutil
from pathlib import Path
from typing import Dict, Any
from unittest.mock import Mock

from quip_mirror.models import MirrorConfig, QuipItem, FolderContents, ProcessingSummary


@pytest.fixture
def temp_dir():
    """Create a temporary directory for testing."""
    temp_path = tempfile.mkdtemp()
    yield temp_path
    shutil.rmtree(temp_path)


@pytest.fixture
def sample_config(temp_dir):
    """Create a sample MirrorConfig for testing."""
    return MirrorConfig(
        quip_folder_url="https://quip-amazon.com/folder/test123",
        target_path=temp_dir,
        access_token="test_token",
        overwrite_existing=True
    )


@pytest.fixture
def sample_folder_item():
    """Create a sample folder QuipItem."""
    return QuipItem(
        id="folder123",
        name="Test Folder",
        type="folder",
        url="https://quip-amazon.com/folder/folder123"
    )


@pytest.fixture
def sample_document_item():
    """Create a sample document QuipItem."""
    return QuipItem(
        id="doc123",
        name="Test Document",
        type="document",
        url="https://quip-amazon.com/doc/doc123"
    )


@pytest.fixture
def sample_folder_contents(sample_folder_item, sample_document_item):
    """Create sample folder contents."""
    return FolderContents(
        folders=[sample_folder_item],
        documents=[sample_document_item]
    )


@pytest.fixture
def mock_quip_api_response():
    """Mock Quip API response data."""
    return {
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


@pytest.fixture
def mock_document_metadata():
    """Mock document metadata response."""
    return {
        "thread": {
            "id": "doc123",
            "title": "Test Document",
            "type": "document"
        }
    }


@pytest.fixture
def mock_requests_session():
    """Create a mock requests session."""
    session = Mock()
    session.get.return_value.status_code = 200
    session.get.return_value.json.return_value = {}
    session.get.return_value.content = b"mock docx content"
    return session


@pytest.fixture
def processing_summary():
    """Create a sample ProcessingSummary."""
    return ProcessingSummary(
        total_folders=2,
        total_documents=3,
        successful_conversions=2,
        failed_conversions=1,
        errors=["Sample error"]
    )